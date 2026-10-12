"""Guard the GitHub Actions CI admission and concurrency contract."""

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


class GitHubActionsCIContractTests(unittest.TestCase):
    def test_primary_ci_runs_on_pull_requests_and_main_pushes(self):
        source = CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("name: CI\n", source)
        self.assertIn("  push:\n    branches: [main]\n", source)
        self.assertIn("  pull_request:\n", source)

    def test_superseded_runs_cancel_per_ref_not_globally(self):
        source = CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "concurrency:\n"
            "  group: ci-${{ github.workflow }}-${{ github.ref }}\n"
            "  cancel-in-progress: true\n",
            source,
            "CI should cancel superseded runs for the same PR/branch only",
        )
        self.assertNotIn(
            "group: ci-${{ github.workflow }}\n",
            source,
            "A repository-wide concurrency key serializes unrelated pull requests",
        )

    def test_rust_build_matrix_remains_in_primary_ci(self):
        source = CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("cargo nextest run --locked", source)
        self.assertIn("cargo test --locked --no-default-features", source)
        self.assertIn("cargo clippy --locked --all-targets", source)


if __name__ == "__main__":
    unittest.main()
