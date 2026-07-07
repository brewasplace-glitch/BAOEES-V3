from pathlib import Path
from datetime import datetime
import json


class PhoenixPluginLoader:
    def __init__(self, registry_path="baoees/phoenix_core/registry/modules.json"):
        self.registry_path = Path(registry_path)

    def list_plugins(self):
        if not self.registry_path.exists():
            return {"plugins": [], "warning": "registry not found"}

        registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
        plugins = []
        for key, value in registry.get("modules", {}).items():
            plugins.append({
                "id": key,
                "name": value.get("name", key),
                "version": value.get("version", "0.0.0"),
                "status": value.get("status", "unknown"),
                "category": value.get("category", "unknown")
            })

        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "plugins": plugins
        }
