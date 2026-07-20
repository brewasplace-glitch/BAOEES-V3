from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pdk.doctor import Doctor
from pdk.sync import Synchronizer


class DoctorTests(unittest.TestCase):
    def test_reports_failure_for_empty_directory(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            report = Doctor(temporary_directory).run()
            self.assertEqual(report.status, "FAIL")
            names = {item.name for item in report.diagnostics}
            self.assertIn("required_files", names)

    def test_current_repository_is_healthy(self) -> None:
        root = Path(__file__).resolve().parents[2]
        report = Doctor(root).run()
        self.assertEqual(
            report.status,
            "PASS",
            msg=report.to_json(),
        )


class SynchronizerTests(unittest.TestCase):
    def test_creates_required_directories(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            result = Synchronizer(temporary_directory).run()
            self.assertTrue(
                (Path(temporary_directory) / "runtime_reports").is_dir()
            )
            self.assertIn("runtime_reports", result.created_directories)


if __name__ == "__main__":
    unittest.main()