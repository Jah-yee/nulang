"""Regression tests for the cross-shard exact-base Criterion A/B harness."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "cross_shard_criterion_ab.py"
SPEC = importlib.util.spec_from_file_location("cross_shard_criterion_ab", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ab)


class CrossShardCriterionABTests(unittest.TestCase):
    def test_benchmark_paths_include_inline_and_shared_boundaries(self) -> None:
        self.assertEqual(
            ab.BENCHMARKS,
            tuple(f"actor/cross_shard_enqueue_by_id/{n}" for n in (0, 1, 4, 5, 16)),
        )

    def test_criterion_results_fail_closed_on_missing_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ab.BENCHMARKS[:-1]:
                path = root / name / "new" / "estimates.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"mean": {"point_estimate": 123.0}}))
            with self.assertRaisesRegex(RuntimeError, "16"):
                ab.read_means(root)

    def test_paired_summary_reports_degradation_and_bootstrap_interval(self) -> None:
        outcome = ab.summarize_pairs([100.0] * 4, [110.0] * 4)
        self.assertEqual(outcome["pairs"], 4)
        self.assertAlmostEqual(outcome["median_latency_change_pct"], 10.0)
        self.assertAlmostEqual(outcome["median_speedup_x"], 100 / 110)
        self.assertLess(outcome["speedup_ci95_upper"], 1.0)

    def test_paired_summary_rejects_mismatched_samples(self) -> None:
        with self.assertRaisesRegex(ValueError, "paired"):
            ab.summarize_pairs([10.0, 20.0], [10.0])

    def test_criterion_command_runs_only_new_shard_group(self) -> None:
        cmd = ab.bench_command()
        self.assertEqual(cmd[:5], ["cargo", "bench", "--locked", "--bench", "actor_bench"])
        self.assertIn("actor/cross_shard_enqueue_by_id", cmd)


if __name__ == "__main__":
    unittest.main()
