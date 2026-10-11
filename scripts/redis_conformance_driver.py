#!/usr/bin/env python3
"""Differential RESP conformance driver: replays fixture commands against both
Nulang's RESP cache tier and a real redis-server oracle, comparing replies per
a per-family policy.

Fixtures are files of one RESP command per physical line (self-delimiting wire
frames — a command may itself contain CRLF) with `#` comment lines. The driver
parses frames directly off the byte stream, so inter-frame newlines are simply
whitespace.

Comparison policies (derived from the fixture filename unless --policy is
given, documented here):
  * byte-exact (default)      : full reply bytes must match.
  * ttl-range                 : `:N` integer replies, |a - b| <= 2, for
                                wall-clock TTL drift across two processes.
  * error-prefix              : reply shape (error vs ok) must match; when both
                                are errors, only the first token after '-' must
                                match — message prose is not byte-pinned.

Exit 0 iff every case in the fixture passes; 1 on any mismatch; 2 on usage
error (matches scripts/difffuzz.sh convention).
"""

import argparse
import os
import socket
import sys
import time

REDIS_PORT = 16379
NULANG_PORT = 17390
TTL_DRIFT = 2


class RespReadError(Exception):
    pass


def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise RespReadError("connection closed mid-reply")
        buf += chunk
    return buf


def read_line(sock):
    buf = b""
    while not buf.endswith(b"\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            raise RespReadError("connection closed mid-line")
        buf += chunk
    return buf


def read_reply(sock):
    """Read one complete RESP reply frame (bulk/array nesting included)."""
    line = read_line(sock)
    marker = line[:1]
    if marker in (b"+", b"-", b":"):
        return line
    if marker == b"$":
        try:
            n = int(line[1:-2])
        except ValueError:
            raise RespReadError("bad bulk length: %r" % line)
        if n < 0:
            return line
        return line + recv_exact(sock, n + 2)
    if marker == b"*":
        try:
            n = int(line[1:-2])
        except ValueError:
            raise RespReadError("bad array length: %r" % line)
        if n < 0:
            return line
        parts = [line]
        for _ in range(n):
            parts.append(read_reply(sock))
        return b"".join(parts)
    raise RespReadError("unexpected reply marker %r" % marker)


def connect(host, port):
    sock = socket.create_connection((host, port), timeout=5)
    sock.settimeout(10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


def _read_resp_frame(data, pos, path):
    """Parse one complete RESP array-of-bulk command frame at data[pos].
    Returns (frame_bytes, new_pos)."""
    if data[pos : pos + 1] != b"*":
        raise RuntimeError("%s: expected '*' at byte %d" % (path, pos))
    end = data.index(b"\r\n", pos)
    count = int(data[pos + 1 : end])
    i = end + 2
    if count <= 0:
        raise RuntimeError("%s: non-positive command argc %d" % (path, count))
    for _ in range(count):
        if data[i : i + 1] != b"$":
            raise RuntimeError("%s: expected bulk arg at byte %d" % (path, i))
        lend = data.index(b"\r\n", i)
        length = int(data[i + 1 : lend])
        j = lend + 2
        if length < 0:
            raise RuntimeError("%s: null bulk inside command" % path)
        i = j + length + 2  # payload + trailing CRLF
    if i > len(data):
        raise RuntimeError("%s: truncated command frame" % path)
    return data[pos:i], i


def load_fixture(path):
    with open(path, "rb") as fh:
        data = fh.read()
    commands = []
    pos = 0
    n = len(data)
    while pos < n:
        byte = data[pos : pos + 1]
        if byte == b"#":
            linefeed = data.find(b"\n", pos)
            if linefeed < 0:
                break
            pos = linefeed + 1
            continue
        if byte in (b"\r", b"\n", b" ", b"\t"):
            pos += 1
            continue
        frame, pos = _read_resp_frame(data, pos, path)
        commands.append(frame)
    if not commands:
        raise RuntimeError("fixture %s contains no commands" % path)
    return commands


def policy_for(path, explicit):
    if explicit:
        return explicit
    base = os.path.basename(path)
    if "errors" in base:
        return "error-prefix"
    if "expiry" in base:
        return "ttl-range"
    return "byte-exact"


def first_error_token(reply):
    body = reply[1:]
    # token = up to first space or CRLF
    end = len(body)
    for i, b in enumerate(body):
        if b in (0x20, 0x0D, 0x0A):
            end = i
            break
    return body[:end]


def compare(server_reply, oracle_reply, policy):
    if policy == "error-prefix":
        s_err = server_reply.startswith(b"-")
        r_err = oracle_reply.startswith(b"-")
        if s_err != r_err:
            return "shape mismatch: server=%s oracle=%s" % (
                "error" if s_err else "ok",
                "error" if r_err else "ok",
            )
        if s_err:
            st = first_error_token(server_reply)
            rt = first_error_token(oracle_reply)
            if st != rt:
                return "error-token mismatch: server=%r oracle=%r" % (st, rt)
        return None
    if policy == "ttl-range":
        # Integer replies (e.g. TTL `:N`) allow drift; any other reply
        # (e.g. the SET `+OK`) must be byte-exact.
        if server_reply.startswith(b":") or oracle_reply.startswith(b":"):
            if not (server_reply.startswith(b":") and oracle_reply.startswith(b":")):
                return "ttl shape mismatch: server=%r oracle=%r" % (
                    server_reply,
                    oracle_reply,
                )
            sv = int(server_reply[1:-2])
            rv = int(oracle_reply[1:-2])
            if abs(sv - rv) > TTL_DRIFT:
                return "ttl drift %d vs %d (allowed +/-%d)" % (sv, rv, TTL_DRIFT)
            return None
        if server_reply != oracle_reply:
            return "byte mismatch: server=%r oracle=%r" % (server_reply, oracle_reply)
        return None
    if server_reply != oracle_reply:
        return "byte mismatch: server=%r oracle=%r" % (server_reply, oracle_reply)
    return None


def wait_ready(host, port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = connect(host, port)
            try:
                sock.sendall(b"*1\r\n$4\r\nPING\r\n")
                if read_reply(sock) == b"+PONG\r\n":
                    return
            finally:
                sock.close()
        except (OSError, RespReadError):
            time.sleep(0.2)
    raise RuntimeError("server %s:%s not ready after %ss" % (host, port, timeout))


def run_fixture(server_host, server_port, oracle_host, oracle_port, path,
                policy, pipelined):
    commands = load_fixture(path)
    policy = policy_for(path, policy)

    with connect(server_host, server_port) as server, connect(
        oracle_host, oracle_port
    ) as oracle:
        if not pipelined:
            for raw in commands:
                server.sendall(raw)
                oracle.sendall(raw)
                mismatch = compare(read_reply(server), read_reply(oracle), policy)
                if mismatch:
                    print("MISMATCH (%s) %r: %s" % (policy, raw, mismatch))
                    return 1
            return 0

        blob = b"".join(commands)
        server.sendall(blob)
        oracle.sendall(blob)
        for raw in commands:
            mismatch = compare(read_reply(server), read_reply(oracle), policy)
            if mismatch:
                print("MISMATCH (pipelined %s) %r: %s" % (policy, raw, mismatch))
                return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--server-host", default="127.0.0.1")
    ap.add_argument("--server-port", type=int, default=NULANG_PORT)
    ap.add_argument("--oracle-host", default="127.0.0.1")
    ap.add_argument("--oracle-port", type=int, default=REDIS_PORT)
    ap.add_argument("--fixture")
    ap.add_argument("--pipelined", action="store_true",
                    help="send the whole file in one write; read replies in order")
    ap.add_argument("--policy", choices=["byte-exact", "ttl-range", "error-prefix"],
                    help="override policy; default derived from fixture filename")
    ap.add_argument("--wait", action="store_true",
                    help="poll PING until both servers answer, then exit 0")
    args = ap.parse_args()

    if args.wait:
        wait_ready(args.server_host, args.server_port)
        wait_ready(args.oracle_host, args.oracle_port)
        return 0

    if not args.fixture:
        print("driver: --fixture is required (unless --wait)", file=sys.stderr)
        return 2

    return run_fixture(
        args.server_host, args.server_port, args.oracle_host, args.oracle_port,
        args.fixture, args.policy, args.pipelined,
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RespReadError, RuntimeError) as exc:
        print("driver: %s" % exc, file=sys.stderr)
        sys.exit(1)