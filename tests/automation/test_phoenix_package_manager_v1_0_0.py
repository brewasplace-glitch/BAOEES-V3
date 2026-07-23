import tempfile
import unittest
from pathlib import Path

from phoenix.package_manager import (
    PackageManifest,
    PackageManagerError,
    load_manifest,
)


class PackageManagerTests(unittest.TestCase):
    def test_manifest(self):
        manifest = PackageManifest.from_mapping(
            {
                "package_id": "demo",
                "version": "1.0.0",
                "commit_message": "feat: demo",
                "install_files": ["a.txt"],
                "remove_files": ["old.txt"],
                "tests": ["tests.demo"],
            }
        )
        self.assertEqual(manifest.package_id, "demo")

    def test_reject_unsafe_path(self):
        with self.assertRaises(PackageManagerError):
            PackageManifest.from_mapping(
                {
                    "package_id": "demo",
                    "version": "1.0.0",
                    "commit_message": "feat: demo",
                    "install_files": ["../unsafe.txt"],
                }
            )

    def test_load_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            path.write_text(
                '{"package_id":"x","version":"1","commit_message":"feat: x",'
                '"install_files":["a.txt"],"remove_files":[],"tests":[]}',
                encoding="utf-8",
            )
            manifest = load_manifest(path)
        self.assertEqual(manifest.version, "1")


if __name__ == "__main__":
    unittest.main()
