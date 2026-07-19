import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from phoenix.updater.package_discovery import PackageDiscovery
from phoenix.updater.report_writer import RuntimeReportWriter
from phoenix.updater.rollback_manager import RollbackManager


class PackageDiscoveryTests(unittest.TestCase):
    def test_discovers_supported_packages_only(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            incoming = root / "updates" / "incoming"
            incoming.mkdir(parents=True)

            (incoming / "b.zip").write_bytes(b"zip")
            (incoming / "a.phx").write_bytes(b"phx")
            (incoming / "ignore.txt").write_text("ignore", encoding="utf-8")

            packages = PackageDiscovery(root).discover()

            self.assertEqual([package.name for package in packages], ["a.phx", "b.zip"])
            self.assertEqual(PackageDiscovery(root).next_package().name, "a.phx")

    def test_empty_discovery(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.assertEqual(PackageDiscovery(root).discover(), ())
            self.assertIsNone(PackageDiscovery(root).next_package())


class RuntimeReportWriterTests(unittest.TestCase):
    def test_writes_runtime_report(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            destination = RuntimeReportWriter(root).write(
                "discovery",
                {"status": "PASS", "packages": 0},
            )

            self.assertTrue(destination.is_file())
            self.assertIn("runtime_reports/updater", destination.as_posix())
            data = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual(data["report"]["status"], "PASS")

    def test_rejects_unsafe_report_name(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ValueError):
                RuntimeReportWriter(temporary_directory).write("../bad", {})


class RollbackManagerTests(unittest.TestCase):
    def test_creates_snapshot_for_existing_and_missing_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "phoenix" / "module.py"
            source.parent.mkdir(parents=True)
            source.write_text("print('ok')\n", encoding="utf-8")

            snapshot = RollbackManager(root).create_snapshot(
                ["phoenix/module.py", "phoenix/missing.py"],
                snapshot_id="test-snapshot",
            )

            self.assertTrue(snapshot.manifest.is_file())
            self.assertEqual(len(snapshot.entries), 2)
            self.assertTrue(snapshot.entries[0].existed)
            self.assertFalse(snapshot.entries[1].existed)
            self.assertTrue(
                (snapshot.directory / snapshot.entries[0].backup).is_file()
            )

    def test_rejects_parent_traversal(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(ValueError):
                RollbackManager(temporary_directory).create_snapshot(
                    ["../outside.txt"],
                    snapshot_id="unsafe",
                )


if __name__ == "__main__":
    unittest.main()