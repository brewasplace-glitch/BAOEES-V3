from pathlib import Path
from datetime import datetime
import json
import subprocess

from baoees.phoenix_core.registry.module_registry import PhoenixModuleRegistry
from baoees.phoenix_core.health.health_monitor import PhoenixHealthMonitor
from baoees.phoenix_core.backup.backup_manager import PhoenixBackupManager


class PhoenixUpdateEngine:
    def __init__(self, output_dir="outputs/phoenix_core"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = self.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run_bootstrap(self):
        registry = PhoenixModuleRegistry().ensure()
        health = PhoenixHealthMonitor().check()
        backup = PhoenixBackupManager().create_manifest_backup()

        result = {
            "engine": "Phoenix Update Engine",
            "version": "1.0.0",
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "registry": registry,
            "health": health,
            "backup": backup,
            "next": [
                "koppel update-engine aan BAOEES dashboard",
                "voeg package installer toe",
                "voeg rollback op bestandsniveau toe",
                "voeg plugin-loader toe",
                "start Architectural Suite als eerste grote suite"
            ]
        }

        out = self.output_dir / "phoenix_core_bootstrap_result.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        md = self.output_dir / "phoenix_core_bootstrap_report.md"
        md.write_text(
            "# Phoenix Core v1.0 bootstrap\n\n"
            f"Uitgevoerd: {result['ran_at']}\n\n"
            f"Health OK: {health['overall_ok']}\n\n"
            "## Volgende stappen\n"
            + "\n".join(f"- {x}" for x in result["next"]),
            encoding="utf-8"
        )

        return result


if __name__ == "__main__":
    result = PhoenixUpdateEngine().run_bootstrap()
    print("Phoenix Core v1.0 bootstrap uitgevoerd.")
    print("Health OK:", result["health"]["overall_ok"])
