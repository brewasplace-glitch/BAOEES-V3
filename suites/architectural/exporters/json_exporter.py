from pathlib import Path
from datetime import datetime
import json


class ArchitecturalJsonExporter:
    VERSION = "1.1.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_1"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        json_path = self.output_dir / "architectural_suite_v1_1_full_output.json"
        json_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        report_path = self.output_dir / "architectural_suite_v1_1_report.md"
        project = result.get("project", {})
        report = "# Architectural Suite v1.1 Report\n\n"
        report += f"Project: {project.get('project_name', '')}\n\n"
        report += f"Locatie: {project.get('location', '')}\n\n"
        report += "## Modules\n\n"
        for key in result.get("results", {}).keys():
            report += f"- {key}\n"
        report += "\n## Status\n\n"
        report += result.get("status", "unknown")
        report_path.write_text(report, encoding="utf-8")

        return {
            "json": str(json_path),
            "markdown": str(report_path),
            "next_exports": ["pdf", "dxf", "ifc", "skp"]
        }
