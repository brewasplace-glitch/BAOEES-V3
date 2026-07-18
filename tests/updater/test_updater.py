from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.updater.engine import PhoenixUpdater
from phoenix.updater.manifest import UpdateManifest, validate_manifest_files


class PhoenixUpdaterTests(unittest.TestCase):
    def test_manifest_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            payload = package / "payload.txt"
            payload.write_text("phoenix", encoding="utf-8")
            checksum = hashlib.sha256(payload.read_bytes()).hexdigest()

            manifest_data = {
                "update_id": "test-update",
                "version": "1.0",
                "description": "test",
                "files": [
                    {
                        "source": "payload.txt",
                        "target": "target.txt",
                        "sha256": checksum,
                    }
                ],
                "test_commands": [],
                "commit_message": "test: updater",
                "auto_push": False,
            }
            manifest_path = package / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest_data),
                encoding="utf-8",
            )

            manifest = UpdateManifest.load(manifest_path)
            self.assertEqual(manifest.update_id, "test-update")
            self.assertEqual(validate_manifest_files(package, manifest), [])

    def test_discover_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            updater = PhoenixUpdater(root)
            self.assertEqual(updater.discover(), [])


if __name__ == "__main__":
    unittest.main()
