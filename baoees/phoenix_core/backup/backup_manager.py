from pathlib import Path
from datetime import datetime
import json
import shutil


class PhoenixBackupManager:
    def __init__(self, backup_root="outputs/phoenix_core/backups"):
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_manifest_backup(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / f"backup_manifest_{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        files_to_capture = [
            "baoees/phoenix_core/registry/modules.json",
            "PHOENIX_CORE_v1_pre_install_status.txt"
        ]

        copied = []
        for item in files_to_capture:
            src = Path(item)
            if src.exists():
                dst = backup_dir / src.name
                shutil.copy2(src, dst)
                copied.append(str(dst))

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "backup_type": "manifest",
            "files": copied
        }

        (backup_dir / "backup_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return manifest
