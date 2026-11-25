"""Tests for the reusable cuckoo false-positive benchmark."""

import subprocess
import sys
import unittest
from pathlib import Path


class CuckooBenchmarkTest(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "scripts.cuckoo_false_positive", *args],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_both_filters_and_multiple_iterations(self):
        result = self.run_script(
            "--keys", "100", "--queries", "1000", "--iterations", "2", "--capacity", "100", "--seed", "42"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        for name in ("CuckooFilter", "CountingCuckooFilter"):
            self.assertIn(f"{name} run=1 seed=42", result.stdout)
            self.assertIn(f"{name} run=2 seed=43", result.stdout)
            self.assertIn(f"{name} summary: mean_rate=", result.stdout)
        self.assertEqual(4, result.stdout.count("false_negatives=0"))
        self.assertEqual(4, result.stdout.count("inserted=100/100"))

    def test_invalid_arguments_fail(self):
        for args in (("--queries", "0"), ("--error-rate", "1"), ("--iterations", "-1")):
            with self.subTest(args=args):
                result = self.run_script(*args)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
