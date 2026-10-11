#!/usr/bin/env bash
# Differential RESP conformance: replay fixtures/tests/resp_conformance/*.resp
# against both Nulang's RESP cache tier and a real redis-server oracle, and
# diff each reply per family policy (see scripts/redis_conformance_driver.py).
#
# Usage: scripts/redis_conformance.sh
#   REDIS_SERVER=<path>   explicit redis-server binary (default: $PATH lookup)
#   NULANG_BIN=<path>     nulang binary; default builds it under Cargo (honors
#                         CARGO_TARGET_DIR)
#
# Exit codes: 0 full pass; 1 any mismatch; 2 redis-server unavailable (skip).
set -euo pipefail

cd "$(dirname "$0")/.."

REDIS_PORT=16379
NULANG_PORT=17390

usage_error() { echo "redis_conformance.sh: $*" >&2; exit 2; }

REDIS_SERVER="${REDIS_SERVER:-}"
if [[ -z "$REDIS_SERVER" ]]; then
    REDIS_SERVER="$(command -v redis-server || true)"
fi
if [[ -z "$REDIS_SERVER" ]]; then
    echo "redis_conformance.sh: redis-server not found; skipping (set REDIS_SERVER=<path> to run)" >&2
    exit 2
fi

NULANG_BIN="${NULANG_BIN:-${CARGO_TARGET_DIR:-target}/debug/nulang}"

if [[ ! -x "$NULANG_BIN" ]]; then
    echo "redis_conformance.sh: building nulang with cache-server feature" >&2
    cargo build --features cache-server
else
    echo "redis_conformance.sh: using $NULANG_BIN" >&2
fi

REDIS_LOG="$(mktemp /tmp/redis_conformance.redis.XXXXXX)"
NULANG_LOG="$(mktemp /tmp/redis_conformance.nulang.XXXXXX)"
REDIS_PID=""
NULANG_PID=""

cleanup() {
    if [[ -n "$NULANG_PID" ]]; then kill "$NULANG_PID" 2>/dev/null || true; fi
    if [[ -n "$REDIS_PID" ]]; then kill "$REDIS_PID" 2>/dev/null || true; fi
    wait "$NULANG_PID" 2>/dev/null || true
    wait "$REDIS_PID" 2>/dev/null || true
    rm -f "$REDIS_LOG" "$NULANG_LOG"
}
trap cleanup EXIT

ensure_ports_free() {
    local port
    for port in "$REDIS_PORT" "$NULANG_PORT"; do
        if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ":$port\$"; then
            echo "redis_conformance.sh: port $port already in use — refusing to compare against a stale server" >&2
            echo "redis_conformance.sh: free it (or set distinct ports) before running the harness" >&2
            exit 1
        fi
    done
}

start_servers() {
    ensure_ports_free
    "$REDIS_SERVER" --port "$REDIS_PORT" --save "" --appendonly no >"$REDIS_LOG" 2>&1 &
    REDIS_PID=$!
    "$NULANG_BIN" --cache-server --cache-port "$NULANG_PORT" >"$NULANG_LOG" 2>&1 &
    NULANG_PID=$!

    python3 scripts/redis_conformance_driver.py --wait --server-host 127.0.0.1 --server-port "$REDIS_PORT"
    python3 scripts/redis_conformance_driver.py --wait --server-host 127.0.0.1 --server-port "$NULANG_PORT"
}

stop_servers() {
    kill "$NULANG_PID" "$REDIS_PID" 2>/dev/null || true
    wait "$NULANG_PID" "$REDIS_PID" 2>/dev/null || true
    NULANG_PID=""
    REDIS_PID=""
}

run_corpus() {
    local pipelined="$1"
    local flags=()
    [[ "$pipelined" == "1" ]] && flags=(--pipelined)
    local fail=0
    for fixture in tests/resp_conformance/*.resp; do
        echo "redis_conformance.sh: $([ "$pipelined" == "1" ] && echo '[pipelined] ')${fixture}" >&2
        if ! python3 scripts/redis_conformance_driver.py \
            --server-host 127.0.0.1 --server-port "$NULANG_PORT" \
            --oracle-host 127.0.0.1 --oracle-port "$REDIS_PORT" \
            --fixture "$fixture" "${flags[@]}"; then
            echo "redis_conformance.sh: FAIL $fixture" >&2
            fail=1
        fi
    done
    return "$fail"
}

start_servers
fail=0
if ! run_corpus 0; then fail=1; fi
# Pipelined pass needs fresh server state (fixtures mutate keys), so restart.
stop_servers
start_servers
if ! run_corpus 1; then fail=1; fi

if [[ "$fail" == "0" ]]; then
    echo "redis_conformance.sh: full pass" >&2
else
    echo "redis_conformance.sh: one or more families FAILED" >&2
fi
exit "$fail"