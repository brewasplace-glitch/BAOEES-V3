from pathlib import Path
from datetime import datetime
import json


class PhoenixReleaseBuilder:
    def create_release_manifest(self, release_name: str, version: str):
        out = Path("outputs/pdk")
        out.mkdir(parents=True, exist_ok=True)
        manifest = {
            "release_name": release_name,
            "version": version,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "release_manifest_created",
            "generated_by": "Phoenix Development Kit v1.0"
        }
        (out / f"{release_name}_{version}_release_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return manifest
