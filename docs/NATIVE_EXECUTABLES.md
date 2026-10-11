# Experimental native executable slice

This document describes the first independently linked native executable path.
It is **not** the interpreter/JIT-backed `--backend native` path and it is
**not** full-language AOT parity.

## Linux smoke

With Rust, a native C linker (`cc`) and the `native-codegen` Cargo feature:

```sh
cat > hello.nula <<'EOF'
perform IO.print("Hello from Nulang")
EOF
cargo run --locked --release -- --emit-exe --out hello hello.nula
./hello
file hello
ldd hello
stat -c '%s bytes' hello
```

The output is an ordinary host-native executable linked to system libc
(`puts`). It does **not** embed the Nulang compiler, VM, JIT, actor scheduler,
durability stack, or package manager. The emitted artifact is a single
executable file, but is **dynamically linked**: libc and the Linux dynamic
loader must be available on its target machine.

Supported in this prototype:

- A synthetic `__main` (or `main`) entry with no parameters, a single basic
  block, no handlers, and a Unit result.
- UTF-8 string constants, integer constants, local copies, negation, and
  integer addition/subtraction/multiplication. Straight-line integer expressions
  are folded at compile time with the VM's signed **48-bit wraparound** semantics.
- `perform IO.print(string)` and `IO.println(string)`, implemented through
  host `puts`, including their terminating newline.

Not supported: function calls, branching/loops, integer result printing,
dynamic strings, arbitrary effects, actors, FFI, suspension, GC-managed
objects, durability, distribution, or native-library independence.
Unsupported MIR returns an error **before writing or installing an executable**.
NUL-containing string literals are rejected rather than truncated.

## Focused validation

```sh
cargo test --locked --test native_tiny_executable
cargo check --locked --no-default-features
bash scripts/check_mobile_runtime_profile.sh
```

Compare **identical programs and linking requirements**, not a
dynamically linked Nulang hello-world against a fully static Go binary.
Measure bytes on disk (uncompressed and stripped), executable dependencies
(`readelf -d` and `ldd`), startup, peak RSS and output parity with the
bytecode backend.

## Promotion gates

1. Exact-head `cargo test --locked` and native executable smoke pass on Linux.
2. Output parity with bytecode on supported fixtures; unsupported constructs
   fail closed and leave no executable artifact.
3. The `mobile-runtime` feature gate continues excluding Cranelift and
   dynamic FFI.
4. Security review of the linker input, temporary files and artifact replacement.
5. Dedicated binary-size benchmark against Go, TinyGo and a native C baseline
   with comparable libc/static-linking settings.

Do not ship this backend as a production deployment or advertise a binary-size
advantage until these gates and reproducible measurements are satisfied.
