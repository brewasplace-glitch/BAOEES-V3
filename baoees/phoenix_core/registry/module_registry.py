from pathlib import Path
from datetime import datetime
import json
import subprocess


class PhoenixModuleRegistry:
    def __init__(self, registry_path="baoees/phoenix_core/registry/modules.json"):
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def default_registry(self):
        return {
            "registry_version": "1.0",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "modules": {
                "phoenix_core": {
                    "name": "Phoenix Core",
                    "version": "1.0.0",
                    "status": "installed",
                    "category": "core"
                },
                "architectural_suite": {
                    "name": "Architectural Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                },
                "structural_suite": {
                    "name": "Structural Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                },
                "geotechnical_suite": {
                    "name": "Geotechnical Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                },
                "permit_suite": {
                    "name": "Permit Suite",
                    "version": "0.1.0",
                    "status": "planned",
                    "category": "suite"
                }
            }
        }

    def ensure(self):
        if not self.registry_path.exists():
            self.registry_path.write_text(
                json.dumps(self.default_registry(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        return self.load()

    def load(self):
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def save(self, data):
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.registry_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
