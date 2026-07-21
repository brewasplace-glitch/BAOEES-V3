import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from phoenix.release_builder import BuildError, BuildRequest, PhoenixReleaseBuilder


class PhoenixReleaseBuilderTests(unittest.TestCase):
    def test_build_creates_deterministic_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "repo"
            out = root / "out"
            (repo / "a").mkdir(parents=True)
            (repo / "a/file.txt").write_text("phoenix\n", encoding="utf-8")
            request = BuildRequest(
                repo_root=repo,
                release_id="PHX_TEST",
                version="1.0.0",
                output_dir=out,
                include_files=("a/file.txt",),
                metadata={"wave": "test"},
            )
            builder = PhoenixReleaseBuilder()
            first = builder.build(request)
            first_bytes = Path(first.archive_path).read_bytes()
            second = builder.build(request)
            second_bytes = Path(second.archive_path).read_bytes()
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(len(first.archive_sha256), 64)
            with zipfile.ZipFile(first.archive_path) as archive:
                self.assertIn("PHX_TEST/a/file.txt", archive.namelist())
                self.assertIn("PHX_TEST/RELEASE_MANIFEST.json", archive.namelist())
                self.assertIn("PHX_TEST/SHA256SUMS.txt", archive.namelist())

    def test_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            request = BuildRequest(
                repo_root=root,
                release_id="PHX",
                version="1",
                output_dir=root / "out",
                include_files=("missing.txt",),
            )
            with self.assertRaises(BuildError):
                PhoenixReleaseBuilder().build(request)

    def test_rejects_unsafe_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            request = BuildRequest(
                repo_root=root,
                release_id="PHX",
                version="1",
                output_dir=root / "out",
                include_files=("../outside.txt",),
            )
            with self.assertRaises(BuildError):
                PhoenixReleaseBuilder().build(request)

    def test_manifest_contains_checksums(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "repo"
            repo.mkdir()
            (repo / "x.txt").write_text("x", encoding="utf-8")
            result = PhoenixReleaseBuilder().build(
                BuildRequest(
                    repo_root=repo,
                    release_id="PHX",
                    version="1.2.3",
                    output_dir=root / "out",
                    include_files=("x.txt",),
                )
            )
            manifest = json.loads(
                Path(result.manifest_path).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["file_count"], 1)
            self.assertEqual(len(manifest["files"][0]["sha256"]), 64)
            self.assertEqual(len(manifest["manifest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
