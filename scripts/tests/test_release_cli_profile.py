#!/usr/bin/env python3
"""Guard release feature parity: public CLI differs from full only by Python."""

import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


class ReleaseCliProfileTests(unittest.TestCase):
    def test_public_release_keeps_all_non_python_full_features(self):
        with (ROOT / "Cargo.toml").open("rb") as source:
            features = tomllib.load(source)["features"]

        full = set(features["full"])
        self.assertIn("python", full, "the full profile must retain Python interop")
        self.assertIn("release-cli", features, "public release feature profile is missing")
        public = set(features["release-cli"])
        self.assertNotIn("python", public, "release-cli must exclude PyO3")
        self.assertEqual(
            public,
            full - {"python"},
            "release-cli must match every non-Python full feature exactly",
        )


    def test_pull_request_release_rehearsal_never_publishes(self):
        """PR builds may exercise every target, but publishing remains tag-only."""
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn(
            "  pull_request:\n",
            workflow,
            "the four-platform release matrix must be testable before creating a tag",
        )
        self.assertIn(
            "      - name: Verify tag matches crate and CLI versions\n"
            "        if: github.event_name == 'push'\n",
            workflow,
            "a PR has no release tag to verify",
        )
        self.assertIn(
            "  publish:\n"
            "    name: Publish Release\n"
            "    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')\n",
            workflow,
            "pull requests must never have a path to publishing a GitHub Release",
        )


if __name__ == "__main__":
    unittest.main()
