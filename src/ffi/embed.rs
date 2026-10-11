//! Native Rust embedding of Nulang's typed core runtime.

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rust_embedder_compiles_and_runs_typed_results() {
        let mut engine = RustEmbedder::new().unwrap();
        let module = engine.compile("fn add(a: Int, b: Int) -> Int { a + b } add(1, 2)").unwrap();
        assert_eq!(engine.run(&module).unwrap(), RustValue::Int(3));
        assert_eq!(
            engine.call(&module, "add", &[RustValue::Int(11), RustValue::Int(31)]).unwrap(),
            RustValue::Int(42),
        );
    }

    #[test]
    fn rust_embedder_calls_string_functions_without_exposing_nan_boxed_values() {
        let mut engine = RustEmbedder::new().unwrap();
        let module = engine.compile(
            r#"fn greet(name: String) -> String { perform String.concat("hello ", name) } greet("world")"#,
        ).unwrap();
        assert_eq!(engine.run(&module).unwrap(), RustValue::String("hello world".into()));
        assert_eq!(
            engine.call(&module, "greet", &[RustValue::String("Nulang".into())]).unwrap(),
            RustValue::String("hello Nulang".into()),
        );
    }

    #[test]
    fn rust_embedder_rejects_modules_from_other_runtime_instances() {
        let mut a = RustEmbedder::new().unwrap();
        let module = a.compile("41 + 1").unwrap();
        let mut b = RustEmbedder::new().unwrap();
        assert!(b.run(&module).unwrap_err().to_string().contains("another runtime"));
        assert_eq!(a.run(&module).unwrap(), RustValue::Int(42));
    }

    #[test]
    fn rust_embedder_rejects_ints_that_cannot_round_trip_through_the_vm() {
        let mut engine = RustEmbedder::new().unwrap();
        let module = engine.compile("fn id(x: Int) -> Int { x } id(1)").unwrap();
        assert!(engine.call(&module, "id", &[RustValue::Int(i64::MAX)]).is_err());
    }
}
