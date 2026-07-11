from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


class UpdatePackageFormatTests(unittest.TestCase):
    def test_minimal_package_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "files" / "apps" / "example.py"
            payload.parent.mkdir(parents=True)
            payload.write_text("print('ok')\n", encoding="utf-8")

            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            manifest = {
                "format_version": "1.0",
                "package_name": "test",
                "package_version": "v0",
                "files": [{"path": "apps/example.py", "sha256": digest}],
            }
            (root / "manifest.json").write_text(
                json.dumps(manifest),
                encoding="utf-8",
            )

            package = root / "package.zip"
            with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(root / "manifest.json", "manifest.json")
                archive.write(payload, "files/apps/example.py")

            self.assertTrue(package.is_file())
            self.assertGreater(package.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
