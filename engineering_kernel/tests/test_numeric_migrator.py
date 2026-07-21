from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from engineering_kernel.tools.migrate_numeric_assertions import migrate_file


class NumericMigratorTests(unittest.TestCase):
    def migrate(self, body: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_sample.py"
            path.write_text(
                "from __future__ import annotations\n"
                "import unittest\n\n"
                "class Sample(unittest.TestCase):\n"
                f"{body}",
                encoding="utf-8",
            )
            migrate_file(path)
            return path.read_text(encoding="utf-8")

    def test_scalar_float_migrates(self):
        result = self.migrate(
            "    def test_value(self):\n"
            "        self.assertEqual(calculate(), 0.2)\n"
        )
        self.assertIn("assert_float_close(self, calculate(), 0.2)", result)

    def test_numeric_tuple_migrates_to_sequence(self):
        result = self.migrate(
            "    def test_value(self):\n"
            "        self.assertEqual(calculate(), (0.2, 0.3))\n"
        )
        self.assertIn(
            "assert_numeric_sequence_close(self, calculate(), (0.2, 0.3))",
            result,
        )

    def test_string_remains_exact(self):
        result = self.migrate(
            "    def test_value(self):\n"
            '        self.assertEqual(classify(0.5), "material")\n'
        )
        self.assertIn('self.assertEqual(classify(0.5), "material")', result)
        self.assertNotIn("assert_float_close(self, classify", result)

    def test_integer_remains_exact(self):
        result = self.migrate(
            "    def test_value(self):\n"
            "        self.assertEqual(count(0.5), 3)\n"
        )
        self.assertIn("self.assertEqual(count(0.5), 3)", result)

    def test_unknown_composite_remains_exact(self):
        result = self.migrate(
            "    def test_value(self):\n"
            "        self.assertEqual(calculate(), expected_value)\n"
        )
        self.assertIn("self.assertEqual(calculate(), expected_value)", result)


if __name__ == "__main__":
    unittest.main()
