from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.updater.engine import PhoenixUpdater
from phoenix.updater.package_builder import PackageBuilder


class PhoenixUpdaterV11Tests(unittest.TestCase):
    def test_package_builder_creates_valid_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            source = root / "phoenix/example.py"
            source.parent.mkdir(parents=True)
            source.write_text("VALUE = 1\n", encoding="utf-8")

            package = PackageBuilder(root).build(
                update_id="example-update",
                version="1.0",
                description="Example",
                source_files=["phoenix/example.py"],
                test_commands=[["python", "-m", "compileall", "-q", "phoenix"]],
                commit_message="test: example",
                auto_push=False,
            )

            manifest = json.loads(
                (package / "manifest.json").read_text(encoding="utf-8-sig")
            )
            payload = package / manifest["files"][0]["source"]
            expected = hashlib.sha256(payload.read_bytes()).hexdigest()

            self.assertEqual(manifest["update_id"], "example-update")
            self.assertEqual(manifest["files"][0]["sha256"], expected)

    def test_apply_next_without_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            result = PhoenixUpdater(root).apply_next()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["packages"], [])


if __name__ == "__main__":
    unittest.main()
