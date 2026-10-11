//! Compatibility-safe Web.redirect representation for the HTTP adapter.
//!
//! The Nulang language-level Web.redirect operation still returns Html, so
//! standalone VM/conformance rendering can retain an HTML fallback.

#[cfg(test)]
mod tests {
    use super::{is_safe_redirect_target, render_redirect_fallback};

    #[test]
    fn only_same_origin_absolute_paths_can_be_redirected() {
        for allowed in ["/", "/tasks", "/tasks?tab=mine&sort=recent", "/users/42#activity"] {
            assert!(is_safe_redirect_target(allowed), "{allowed}");
        }
        for denied in [
            "", "tasks", "//evil.example", "https://evil.example", "javascript:alert(1)",
            "/\\evil.example", "/\r\nLocation: https://evil.example",
            "/ok\nX-Header: injected", "/ok\u{007f}",
        ] {
            assert!(!is_safe_redirect_target(denied), "{denied:?}");
        }
    }

    #[test]
    fn legacy_fallback_remains_compatible_for_safe_paths() {
        assert_eq!(
            render_redirect_fallback("/other"),
            "<html><head><meta http-equiv=\"refresh\" content=\"0;url=/other\"></head></html>"
        );
    }

    #[test]
    fn fallback_html_escapes_attribute_delimiters() {
        let output = render_redirect_fallback("/?next=\"<img>&done=yes");
        assert!(output.contains("&quot;&lt;img&gt;&amp;done=yes"));
        assert!(!output.contains("next=\"<img>"));
    }

    #[test]
    fn unsafe_redirects_never_emit_executable_meta_refresh() {
        for url in ["//evil.example", "https://evil.example", "/\r\nX-Test: bad"] {
            let output = render_redirect_fallback(url);
            assert!(!output.contains("http-equiv"));
            assert!(!output.contains(url));
        }
    }
}
