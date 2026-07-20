import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from phoenix.updater.api import (
    PackageBuildError,
    ReleasePackageBuilder,
    ReleaseManager,
)


class ReleasePackageBuilderTests(unittest.TestCase):
    def test_builds_archive_manifest_and_checksum(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "phoenix" / "example.py"
            source.parent.mkdir(parents=True)
            source.write_text("print('phoenix')\n", encoding="utf-8")

            built = ReleasePackageBuilder(root).build(
                name="project-phoenix",
                version="2.3.0",
                relative_paths=["phoenix/example.py"],
                changelog="Sprint 3",
            )

            self.assertTrue(built.archive.is_file())
            self.assertTrue(built.manifest.is_file())
            self.assertTrue(built.checksum.is_file())
            self.assertEqual(len(built.archive_sha256), 64)

            with ZipFile(built.archive) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["manifest.json", "payload/phoenix/example.py"],
                )
                self.assertEqual(
                    archive.read("payload/phoenix/example.py"),
                    b"print('phoenix')\n",
                )

            document = json.loads(built.manifest.read_text(encoding="utf-8"))
            self.assertEqual(document["version"], "2.3.0")
            self.assertEqual(document["files"][0]["path"], "phoenix/example.py")

    def test_rejects_runtime_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            runtime_file = root / "runtime" / "state.json"
            runtime_file.parent.mkdir(parents=True)
            runtime_file.write_text("{}", encoding="utf-8")

            with self.assertRaises(PackageBuildError):
                ReleasePackageBuilder(root).build(
                    name="project-phoenix",
                    version="2.3.0",
                    relative_paths=["runtime/state.json"],
                )

    def test_rejects_missing_files(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaises(PackageBuildError):
                ReleasePackageBuilder(temporary_directory).build(
                    name="project-phoenix",
                    version="2.3.0",
                    relative_paths=["missing.py"],
                )


class ReleaseManagerTests(unittest.TestCase):
    def test_creates_release_and_runtime_report(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "docs" / "README.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Phoenix\n", encoding="utf-8")

            result = ReleaseManager(root).create_release(
                name="project-phoenix",
                version="2.3.0",
                relative_paths=["docs/README.md"],
            )

            self.assertEqual(result.status, "PASS")
            self.assertTrue(Path(result.archive).is_file())
            self.assertTrue(Path(result.report_path).is_file())
            self.assertIn('"status": "PASS"', ReleaseManager.to_json(result))


if __name__ == "__main__":
    unittest.main()