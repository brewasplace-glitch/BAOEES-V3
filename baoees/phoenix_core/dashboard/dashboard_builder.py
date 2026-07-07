from pathlib import Path
from datetime import datetime
import json


class PhoenixDashboardBuilder:
    def __init__(self, output_dir="outputs/phoenix_core/dashboard"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, registry_path="baoees/phoenix_core/registry/modules.json"):
        registry_file = Path(registry_path)
        registry = {}
        if registry_file.exists():
            registry = json.loads(registry_file.read_text(encoding="utf-8"))

        payload = {
            "dashboard": "Project Phoenix Core Dashboard",
            "version": "1.1.0",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "registry": registry,
            "cards": [
                {"title": "Phoenix Core", "status": "installed", "type": "core"},
                {"title": "Architectural Suite", "status": "next", "type": "suite"},
                {"title": "Structural Suite", "status": "planned", "type": "suite"},
                {"title": "Geotechnical Suite", "status": "planned", "type": "suite"},
                {"title": "Permit Suite", "status": "planned", "type": "suite"}
            ]
        }

        (self.output_dir / "phoenix_dashboard_payload.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        markdown = "# Project Phoenix Dashboard\n\n"
        markdown += f"Versie: {payload['version']}\n\n"
        markdown += "## Modules\n\n"
        for card in payload["cards"]:
            markdown += f"- {card['title']} â€” {card['status']}\n"

        (self.output_dir / "phoenix_dashboard.md").write_text(markdown, encoding="utf-8")
        return payload
