from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class NumericPolicyCheckerTests(unittest.TestCase):
    def run_checker(self, assertion: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            tests_root = Path(directory)
            (tests_root / "test_sample.py").write_text(
                "import unittest\n\n"
                "class Sample(unittest.TestCase):\n"
                "    def test_value(self):\n"
                f"        {assertion}\n",
                encoding="utf-8",
            )
            checker = (
                Path(__file__).resolve().parents[1]
                / "tools"
                / "check_numeric_test_policy.py"
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(checker),
                    "--tests-root",
                    str(tests_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_float_expectation_is_rejected(self):
        result = self.run_checker("self.assertEqual(calculate(), 0.5)")
        self.assertNotEqual(result.returncode, 0)

    def test_numeric_tuple_expectation_is_rejected(self):
        result = self.run_checker("self.assertEqual(calculate(), (0.5, 1.0))")
        self.assertNotEqual(result.returncode, 0)

    def test_string_expectation_is_allowed_even_with_float_input(self):
        result = self.run_checker(
            'self.assertEqual(classify_material(0.5), "masonry")'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_integer_expectation_is_allowed(self):
        result = self.run_checker("self.assertEqual(count_items(0.5), 3)")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_boolean_expectation_is_allowed(self):
        result = self.run_checker("self.assertEqual(check_value(0.5), True)")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
