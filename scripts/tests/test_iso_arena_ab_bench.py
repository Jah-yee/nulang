"""Contract tests for the paired active-iso-arena benchmark parser."""
import json
import math
import pathlib
import statistics
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import iso_arena_ab_bench as bench


class IsoArenaAbBenchTests(unittest.TestCase):
    def test_reads_criterion_median_ns_per_batch(self):
        with tempfile.TemporaryDirectory() as td:
            file = pathlib.Path(td) / "estimates.json"
            file.write_text(json.dumps({"median": {"point_estimate": 875.25}}))
            self.assertEqual(bench.read_median_ns(file), 875.25)

    def test_rejects_missing_or_invalid_criterion_estimate(self):
        with tempfile.TemporaryDirectory() as td:
            file = pathlib.Path(td) / "estimates.json"
            for payload in ({}, {"median": {"point_estimate": -5}},
                            {"median": {"point_estimate": "NaN"}}):
                file.write_text(json.dumps(payload))
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    bench.read_median_ns(file)

    def test_paired_reduction_uses_matched_round_ratios(self):
        base = [100.0, 200.0, 300.0]
        candidate = [80.0, 160.0, 240.0]
        result = bench.paired_reduction(base, candidate)
        self.assertAlmostEqual(result["median_reduction_pct"], 20.0)
        self.assertEqual(result["pairs"], 3)
        self.assertEqual(len(result["paired_reductions_pct"]), 3)

    def test_paired_reduction_detects_invalid_samples(self):
        for base, candidate in [([1.0, 2.0], [1.0]), ([0.0], [2.0]),
                                ([1.0], [math.inf]), ([], [])]:
            with self.assertRaises(ValueError):
                bench.paired_reduction(base, candidate)

    def test_counterbalanced_run_order(self):
        self.assertEqual(bench.variant_order(0), ("base", "candidate"))
        self.assertEqual(bench.variant_order(1), ("candidate", "base"))
        self.assertEqual(bench.variant_order(2), ("base", "candidate"))


if __name__ == "__main__":
    unittest.main()
