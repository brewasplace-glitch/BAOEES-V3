from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engineering_kernel.tools.repair_numeric_call_sites import repair_file


class NumericCallsiteRepairTests(unittest.TestCase):
    def repair(self, assertion: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_sample.py"
            path.write_text(
                "from engineering_kernel.tests.numeric_assertions "
                "import assert_float_close\n\n"
                "def test_value(self):\n"
                f"    {assertion}\n",
                encoding="utf-8",
            )
            repair_file(path)
            return path.read_text(encoding="utf-8")

    def test_tuple_becomes_sequence_assertion(self):
        result = self.repair(
            "assert_float_close(self, calculate(), (0.0, 1.0))"
        )
        self.assertIn(
            "assert_numeric_sequence_close(self, calculate(), (0.0, 1.0))",
            result,
        )

    def test_string_becomes_exact_assertion(self):
        result = self.repair(
            'assert_float_close(self, classify(), "plastic")'
        )
        self.assertIn(
            'self.assertEqual(classify(), "plastic")',
            result,
        )

    def test_scalar_float_remains_float_assertion(self):
        result = self.repair(
            "assert_float_close(self, calculate(), 0.5)"
        )
        self.assertIn(
            "assert_float_close(self, calculate(), 0.5)",
            result,
        )


if __name__ == "__main__":
    unittest.main()
