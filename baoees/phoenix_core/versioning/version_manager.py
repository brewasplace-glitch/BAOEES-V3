from pathlib import Path
from datetime import datetime
import json


class PhoenixVersionManager:
    def __init__(self, version_file="baoees/phoenix_core/versioning/phoenix_version.json"):
        self.version_file = Path(version_file)
        self.version_file.parent.mkdir(parents=True, exist_ok=True)

    def set_version(self, version="1.1.0"):
        data = {
            "product": "Project Phoenix Core",
            "version": version,
            "updated_at": datetime.now().isoformat(timespec="seconds")
        }
        self.version_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data
