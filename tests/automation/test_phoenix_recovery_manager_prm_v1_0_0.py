import unittest

from phoenix.recovery_manager import RecoveryError, inspect_porcelain
from phoenix.recovery_manager.manager import normalize_porcelain_path


class PhoenixRecoveryManagerTests(unittest.TestCase):
    def test_accepts_known_interrupted_paths(self):
        result = inspect_porcelain(
            [
                "?? phoenix/optimization/__init__.py",
                "?? phoenix/optimization/optimization_core.py",
                " M phoenix/adapters/__init__.py",
            ],
            [
                "phoenix/optimization/__init__.py",
                "phoenix/optimization/optimization_core.py",
                "phoenix/adapters/__init__.py",
            ],
        )
        self.assertTrue(result.is_safe)
        self.assertEqual(result.unexpected_paths, ())

    def test_rejects_unrelated_path(self):
        result = inspect_porcelain(
            ["?? unrelated.txt"],
            ["phoenix/optimization/__init__.py"],
        )
        self.assertFalse(result.is_safe)
        self.assertEqual(result.unexpected_paths, ("unrelated.txt",))

    def test_normalizes_windows_separator(self):
        self.assertEqual(
            normalize_porcelain_path(r"?? phoenix\optimization\core.py"),
            "phoenix/optimization/core.py",
        )

    def test_rejects_invalid_status_line(self):
        with self.assertRaises(RecoveryError):
            normalize_porcelain_path("??")


if __name__ == "__main__":
    unittest.main()
