from pathlib import Path
from datetime import datetime
import json


class PhoenixPackageManager:
    def __init__(self, package_dir="outputs/phoenix_core/packages"):
        self.package_dir = Path(package_dir)
        self.package_dir.mkdir(parents=True, exist_ok=True)

    def create_package_manifest(self, package_name, version, files=None):
        manifest = {
            "package_name": package_name,
            "version": version,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "files": files or [],
            "status": "manifest_created"
        }

        out = self.package_dir / f"{package_name}_{version}_manifest.json"
        out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest
