"""Keep the standalone ELF smoke wired to the opt-in feature and Cargo output."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def job_section(workflow: str, name: str) -> str:
    match = re.search(rf"(?m)^  {re.escape(name)}:\n", workflow)
    if not match:
        raise AssertionError(f"CI job {name!r} is missing")
    following = workflow[match.end():]
    boundary = re.search(r"(?m)^  [a-z][a-z0-9_-]*:\n", following)
    return following if boundary is None else following[:boundary.start()]


class NativeCiWiringTests(unittest.TestCase):
    def test_native_smoke_runs_in_opt_in_lane_with_actual_cargo_target_dir(self):
        workflow = WORKFLOW.read_text()
        primary = job_section(workflow, "test")
        minimal = job_section(workflow, "minimal-build")

        # The default-feature compiler intentionally does not contain --emit-exe.
        self.assertNotIn("Native executable smoke and size report", primary)
        self.assertIn("--no-default-features --features native-executable --bin nulang", minimal)
        self.assertIn("--no-default-features --features native-executable --test native_tiny_executable", minimal)
        self.assertIn("cargo metadata --locked --format-version 1 --no-deps", minimal)
        self.assertIn('scripts/measure_native_binaries.sh "$cargo_target/debug/nulang"', minimal)
        self.assertIn('--nulang "$cargo_target/debug/nulang"', minimal)
        self.assertIn("native-binary-size.json", minimal)
        self.assertIn("Upload native executable size report", minimal)


if __name__ == "__main__":
    unittest.main()
