//! Safe same-origin redirects shared by standalone Web rendering and HTTP.
//!
//! The language effect remains `Web.redirect(url) -> Html` for compatibility.
//! Routed HTTP handlers returning that exact value may be upgraded to HTTP
//! 303 by the dev server; standalone rendering keeps the inert HTML fallback.

/// Accept only absolute *local paths*, never scheme-relative or absolute
/// external URLs, whitespace, controls, or backslashes.
pub fn is_safe_redirect_target(url: &str) -> bool {
    url.starts_with('/')
        && !url.starts_with("//")
        && !url.contains('\\')
        && !url.chars().any(char::is_control)
        && !url.bytes().any(|b| b.is_ascii_whitespace())
}

fn escape_html_attribute(value: &str) -> String {
    let mut escaped = String::with_capacity(value.len());
    for ch in value.chars() {
        match ch {
            '&' => escaped.push_str("&amp;"),
            '"' => escaped.push_str("&quot;"),
            '<' => escaped.push_str("&lt;"),
            '>' => escaped.push_str("&gt;"),
            '\'' => escaped.push_str("&#39;"),
            _ => escaped.push(ch),
        }
    }
    escaped
}

/// The previous Nulang conformance fixture for `/other` stays byte-for-byte
/// identical. Bad targets are inert rather than emitted into executable HTML.
pub fn render_redirect_fallback(url: &str) -> String {
    if !is_safe_redirect_target(url) {
        return "<html><body>Invalid redirect target</body></html>".to_string();
    }
    format!(
        "<html><head><meta http-equiv=\"refresh\" content=\"0;url={}\"></head></html>",
        escape_html_attribute(url)
    )
}

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
