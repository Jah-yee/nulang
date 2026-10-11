#!/usr/bin/env bash
# Focused smoke for the public C ABI and the idiomatic Rust embedding wrapper.
# Requires Rust, Cargo, cc and nm on a Linux host.
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Embedding shared-library smoke currently targets Linux only" >&2
  exit 2
fi

features=(--locked --no-default-features --features ffi)
for suite in ffi::c_api::tests ffi::native::tests ffi::embed::tests; do
  cargo test "${features[@]}" --lib "$suite"
done

cargo build "${features[@]}" --lib
library="target/debug/libnulang.so"
test -s "$library"

for symbol in \
  nulang_runtime_new \
  nulang_runtime_register_native_function \
  nulang_value_to_string_in_module \
  nulang_run_owned \
  nulang_call_function_owned \
  nulang_owned_value_from_module \
  nulang_owned_value_int_new \
  nulang_owned_value_int \
  nulang_owned_value_string_new \
  nulang_owned_value_to_string \
  nulang_owned_value_release; do
  if ! nm -D --defined-only "$library" | awk -v symbol="$symbol" '$NF == symbol { found=1 } END { exit !found }'; then
    echo "Required C ABI export missing: $symbol" >&2
    exit 1
  fi
done

mkdir -p target/embed-smoke
cc -std=c11 -Wall -Wextra -Werror \
  -Iinclude \
  examples/ffi_example.c \
  -Ltarget/debug -lnulang \
  -Wl,-rpath,"$(pwd)/target/debug" \
  -o target/embed-smoke/ffi_example

target/embed-smoke/ffi_example
