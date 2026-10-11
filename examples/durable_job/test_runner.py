#!/usr/bin/env python3
"""Harness self-tests; fake interpreter must never count as a Nulang proof."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class CrashHarnessTests(unittest.TestCase):
    def test_sqlite_comparator_recovers_and_deduplicates(self):
        result = subprocess.run([sys.executable, str(HERE / "run_demo.py"), "--baseline-only", "--timeout", "5"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS sqlite:", result.stdout)
        self.assertIn("RECOVERED=2:1, COMPLETED=2:1", result.stdout)

    def test_runner_rejects_fake_nulang_that_loses_committed_state(self):
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "broken-nulang"
            fake.write_text("#!/usr/bin/env python3\n"
                            "import os\n"
                            "if os.environ['DEMO_PHASE']=='prepare':\n"
                            "    print('PREPARED=1:0',flush=True)\n"
                            "    open('gate.fifo').read()\n"
                            "else:\n"
                            "    print('RECOVERED=0:0',flush=True)\n"
                            "    print('COMPLETED=2:1',flush=True)\n")
            fake.chmod(0o755)
            result = subprocess.run([sys.executable, str(HERE / "run_demo.py"),
                                     "--nulang-bin", str(fake), "--timeout", "5"],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected ['RECOVERED=1:0']", result.stderr)
            self.assertNotIn("PASS nulang:", result.stdout)


if __name__ == "__main__":
    unittest.main()
