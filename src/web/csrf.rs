//! Browser mutation provenance gate for the experimental HTTP dev server.
//!
//! Tests specify the contract before integrating it into request dispatch.

#[cfg(test)]
mod tests {
    use super::{validate_mutation_origin, OriginCheckError};
    use std::net::SocketAddr;

    fn loopback() -> SocketAddr {
        "127.0.0.1:8080".parse().unwrap()
    }

    fn headers(values: &[(&str, &str)]) -> Vec<(String, String)> {
        values
            .iter()
            .map(|(name, value)| (name.to_string(), value.to_string()))
            .collect()
    }

    #[test]
    fn safe_requests_need_no_origin_or_host() {
        for method in ["GET", "HEAD", "OPTIONS"] {
            assert_eq!(validate_mutation_origin(method, &[], None, None), Ok(()));
        }
    }

    #[test]
    fn same_origin_mutation_is_allowed_for_loopback_and_localhost() {
        for host in ["localhost:8080", "127.0.0.1:8080"] {
            let request = headers(&[
                ("Host", host),
                ("Origin", &format!("http://{host}")),
                ("Sec-Fetch-Site", "same-origin"),
            ]);
            assert_eq!(
                validate_mutation_origin("POST", &request, Some(loopback()), None),
                Ok(())
            );
        }
    }

    #[test]
    fn missing_and_foreign_origin_fail_closed() {
        let missing = headers(&[("Host", "localhost:8080")]);
        assert_eq!(
            validate_mutation_origin("POST", &missing, Some(loopback()), None),
            Err(OriginCheckError::MissingProvenance)
        );
        let foreign = headers(&[
            ("Host", "localhost:8080"),
            ("Origin", "https://attacker.example"),
        ]);
        assert_eq!(
            validate_mutation_origin("POST", &foreign, Some(loopback()), None),
            Err(OriginCheckError::OriginMismatch)
        );
        let null = headers(&[("Host", "localhost:8080"), ("Origin", "null")]);
        assert!(validate_mutation_origin("POST", &null, Some(loopback()), None).is_err());
    }

    #[test]
    fn referer_fallback_requires_an_exact_origin_boundary() {
        let valid = headers(&[
            ("Host", "localhost:8080"),
            ("Referer", "http://localhost:8080/path?query=yes"),
        ]);
        assert_eq!(
            validate_mutation_origin("PATCH", &valid, Some(loopback()), None),
            Ok(())
        );
        let spoofed = headers(&[
            ("Host", "localhost:8080"),
            ("Referer", "http://localhost:8080.attacker.example/path"),
        ]);
        assert!(validate_mutation_origin("PATCH", &spoofed, Some(loopback()), None).is_err());
    }

    #[test]
    fn cross_site_fetch_metadata_overrides_a_claimed_same_origin() {
        let request = headers(&[
            ("Host", "localhost:8080"),
            ("Origin", "http://localhost:8080"),
            ("Sec-Fetch-Site", "same-site"),
        ]);
        assert_eq!(
            validate_mutation_origin("DELETE", &request, Some(loopback()), None),
            Err(OriginCheckError::CrossOriginFetch)
        );
    }

    #[test]
    fn dns_rebinding_and_duplicate_provenance_headers_fail_closed() {
        let rebound = headers(&[
            ("Host", "attacker.example:8080"),
            ("Origin", "http://attacker.example:8080"),
        ]);
        assert_eq!(
            validate_mutation_origin("POST", &rebound, Some(loopback()), None),
            Err(OriginCheckError::UntrustedHost)
        );
        let duplicate = headers(&[
            ("Host", "localhost:8080"),
            ("Origin", "http://localhost:8080"),
            ("Origin", "http://attacker.example"),
        ]);
        assert_eq!(
            validate_mutation_origin("POST", &duplicate, Some(loopback()), None),
            Err(OriginCheckError::DuplicateHeader)
        );
    }

    #[test]
    fn configured_https_public_origin_supports_trusted_reverse_proxies() {
        let valid = headers(&[
            ("Host", "app.example.com"),
            ("Origin", "https://app.example.com"),
            ("Sec-Fetch-Site", "same-origin"),
        ]);
        assert_eq!(
            validate_mutation_origin(
                "POST",
                &valid,
                Some(loopback()),
                Some("https://app.example.com")
            ),
            Ok(())
        );
        assert_eq!(
            validate_mutation_origin(
                "POST",
                &valid,
                Some(loopback()),
                Some("https://app.example.com/unsafe/path")
            ),
            Err(OriginCheckError::InvalidConfiguration)
        );
        let injected_host = headers(&[
            ("Host", "attacker.example"),
            ("Origin", "https://app.example.com"),
        ]);
        assert_eq!(
            validate_mutation_origin(
                "POST",
                &injected_host,
                Some(loopback()),
                Some("https://app.example.com")
            ),
            Err(OriginCheckError::UntrustedHost)
        );
    }
}
