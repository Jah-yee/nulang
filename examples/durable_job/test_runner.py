#!/usr/bin/env python3
"""Harness self-tests; fake interpreter must never count as a Nulang proof."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import run_demo

HERE = Path(__file__).resolve().parent


class CrashHarnessTests(unittest.TestCase):
    def test_sqlite_comparator_recovers_and_deduplicates(self):
        result = subprocess.run([sys.executable, str(HERE / "run_demo.py"), "--baseline-only", "--timeout", "5"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS sqlite:", result.stdout)
        self.assertIn("RECOVERED=2:1, COMPLETED=2:1", result.stdout)

    def test_nulang_cli_arguments_grant_only_fs_as_separate_tokens(self):
        # Regression: --with=fs is rejected; the CLI accepts --with fs.
        with mock.patch.object(run_demo, "run_phase") as phase:
            run_demo.exercise("nulang", ["/some/nulang"], 5)
        self.assertEqual(phase.call_count, 3)
        for call in phase.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[:5], ["/some/nulang", "--backend", "bytecode", "--with", "fs"])
            self.assertNotIn("--with=fs", argv)
            self.assertIn("--store", argv)

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
