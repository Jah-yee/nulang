//! End-to-end native object/linker smoke tests. Host-libc executable; Linux only.
//! These tests intentionally exercise the compiler CLI rather than the VM.

#![cfg(all(target_os = "linux", feature = "native-codegen"))]

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn test_dir() -> PathBuf {
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let path = std::env::temp_dir().join(format!("nulang-native-tiny-{}-{nonce}", std::process::id()));
    fs::create_dir(&path).unwrap();
    path
}

fn build(dir: &Path, source: &str) -> std::process::Output {
    let input = dir.join("main.nula");
    fs::write(&input, source).unwrap();
    Command::new(env!("CARGO_BIN_EXE_nulang"))
        .args(["--emit-exe", "--out"])
        .arg(dir.join("hello"))
        .arg(input)
        .output()
        .unwrap()
}

#[test]
fn hello_world_is_a_real_executable_without_the_nulang_runtime() {
    assert!(
        Command::new("cc").arg("--version").output().is_ok(),
        "native executable tests require a host C linker (cc)"
    );
    let dir = test_dir();
    let built = build(&dir, "perform IO.print(\"Hello from native Nulang\")");
    assert!(
        built.status.success(),
        "compiler stderr: {}",
        String::from_utf8_lossy(&built.stderr)
    );
    let program = dir.join("hello");
    assert!(program.exists());
    let run = Command::new(&program).output().unwrap();
    assert_eq!(run.status.code(), Some(0));
    assert_eq!(run.stdout, b"Hello from native Nulang\n");
    assert!(run.stderr.is_empty());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn unsupported_string_expression_fails_closed_without_an_executable() {
    let dir = test_dir();
    let built = build(&dir, "let name = \"Nulang\" + \"!\";
perform IO.print(name)");
    assert!(!built.status.success());
    assert!(String::from_utf8_lossy(&built.stderr).contains("unsupported"));
    assert!(!dir.join("hello").exists());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn embedded_nul_is_rejected_without_truncating_output() {
    let dir = test_dir();
    let built = build(&dir, "perform IO.print(\"A\\0B\")");
    assert!(!built.status.success());
    assert!(!dir.join("hello").exists());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn multiple_prints_preserve_order_and_utf8() {
    let dir = test_dir();
    let built = build(
        &dir,
        "perform IO.print(\"First\");\nperform IO.print(\"Olá, Nulang\")",
    );
    assert!(
        built.status.success(),
        "compiler stderr: {}",
        String::from_utf8_lossy(&built.stderr)
    );
    let run = Command::new(dir.join("hello")).output().unwrap();
    assert_eq!(run.status.code(), Some(0));
    assert_eq!(run.stdout, "First\nOlá, Nulang\n".as_bytes());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn unsupported_source_preserves_existing_executable_bytes() {
    let dir = test_dir();
    let artifact = dir.join("hello");
    fs::write(&artifact, b"existing-good-artifact").unwrap();
    let built = build(
        &dir,
        "let greeting = \"Hello\" + \" World\";\nperform IO.print(greeting)",
    );
    assert!(!built.status.success());
    assert!(String::from_utf8_lossy(&built.stderr).contains("unsupported"));
    assert_eq!(fs::read(&artifact).unwrap(), b"existing-good-artifact");
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn integer_overflow_fails_closed_before_linking() {
    // Signed Nulang Ints have a 48-bit payload. An unboxed i64 add must
    // never wrap beyond that bound and then continue with observable IO.
    let dir = test_dir();
    let built = build(
        &dir,
        "let max = 140737488355327;\nlet overflow = max + 1;\nperform IO.print(\"must not run\")",
    );
    assert!(
        !built.status.success(),
        "overflow should be rejected, stdout: {}",
        String::from_utf8_lossy(&built.stdout)
    );
    assert!(
        String::from_utf8_lossy(&built.stderr).contains("48-bit"),
        "stderr: {}",
        String::from_utf8_lossy(&built.stderr)
    );
    assert!(!dir.join("hello").exists());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn negating_minimum_integer_fails_closed_before_linking() {
    let dir = test_dir();
    let built = build(
        &dir,
        "let min = -140737488355328;\nlet overflow = -min;\nperform IO.print(\"must not run\")",
    );
    assert!(
        !built.status.success(),
        "negation overflow should be rejected, stdout: {}",
        String::from_utf8_lossy(&built.stdout)
    );
    assert!(
        String::from_utf8_lossy(&built.stderr).contains("48-bit"),
        "stderr: {}",
        String::from_utf8_lossy(&built.stderr)
    );
    assert!(!dir.join("hello").exists());
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn explicit_output_equal_to_input_cannot_overwrite_source() {
    let dir = test_dir();
    let input = dir.join("main.nula");
    let original = b"perform IO.print(\\\"Never overwrite source\\\")";
    fs::write(&input, original).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_nulang"))
        .args(["--emit-exe", "--out"])
        .arg(&input)
        .arg(&input)
        .output()
        .unwrap();
    assert!(!result.status.success());
    assert_eq!(fs::read(&input).unwrap(), original);
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn extensionless_source_is_not_the_default_output_path() {
    let dir = test_dir();
    let input = dir.join("source");
    let original = b"perform IO.print(\\\"preserve me\\\")";
    fs::write(&input, original).unwrap();
    let result = Command::new(env!("CARGO_BIN_EXE_nulang"))
        .arg("--emit-exe")
        .arg(&input)
        .output()
        .unwrap();
    assert!(
        result.status.success(),
        "compiler stderr: {}",
        String::from_utf8_lossy(&result.stderr)
    );
    assert_eq!(fs::read(&input).unwrap(), original);
    assert_eq!(Command::new(dir.join("source.bin")).output().unwrap().stdout, b"preserve me\n");
    fs::remove_dir_all(dir).unwrap();
}
