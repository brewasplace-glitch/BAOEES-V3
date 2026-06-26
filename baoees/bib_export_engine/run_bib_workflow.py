from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


# Zorgt dat dit bestand ook veilig werkt als iemand het per ongeluk direct start.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baoees.bib_export_engine.run_full_export import BibFullExportRunner
from baoees.bib_export_engine.launcher_bridge import BibLauncherBridge


class BibWorkflowRunner:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB Workflow Runner v3.5

    Doel:
    - Draait de volledige BIB-export.
    - Draait daarna de launcher bridge.
    - Maakt een centrale workflow-log.
    - Vormt de hoofdworkflow voor de Brewster Integrated Bibliotheek.
    """

    ENGINE_NAME = "Project Phoenix BIB Workflow Runner"
    ENGINE_VERSION = "v3.5"

    def __init__(
        self,
        output_root: str | Path | None = None,
        project_index_path: str | Path | None = None,
    ) -> None:
        self.output_root = Path(output_root) if output_root else Path("outputs") / "bib"
        self.project_index_path = (
            Path(project_index_path)
            if project_index_path
            else Path("outputs") / "projects" / "index.html"
        )

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)

        full_export_runner = BibFullExportRunner(output_root=self.output_root)
        launcher_bridge = BibLauncherBridge(
            project_index_path=self.project_index_path,
            bib_output_root=self.output_root,
        )

        full_export_result = full_export_runner.run(**extra_results)
        launcher_result = launcher_bridge.run(**extra_results)

        workflow_log_path = self.output_root / "bib_workflow_log.json"

        result = {
            "status": self.determine_status(full_export_result, launcher_result),
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "output_root": str(self.output_root),
            "project_index_path": str(self.project_index_path),
            "full_export_result": full_export_result,
            "launcher_bridge_result": launcher_result,
            "workflow_log_path": str(workflow_log_path),
            "warnings": self.build_warnings(full_export_result, launcher_result),
            "recommendation": self.build_recommendation(full_export_result, launcher_result),
        }

        self.write_json(workflow_log_path, result)
        return result

    def determine_status(
        self,
        full_export_result: Dict[str, Any],
        launcher_result: Dict[str, Any],
    ) -> str:
        full_status = full_export_result.get("status")
        launcher_status = launcher_result.get("status")

        if full_status in {"FAILED", "FOUT"}:
            return "FAILED"

        if launcher_status in {"FAILED", "FOUT"}:
            return "FAILED"

        if full_status == "WARNING":
            return "WARNING"

        if launcher_status == "WARNING":
            return "WARNING"

        return "OPGESLAGEN"

    def build_warnings(
        self,
        full_export_result: Dict[str, Any],
        launcher_result: Dict[str, Any],
    ) -> List[str]:
        warnings: List[str] = []

        for warning in full_export_result.get("warnings", []):
            if warning and "Geen kritieke" not in str(warning):
                warnings.append(f"Full export: {warning}")

        for warning in launcher_result.get("warnings", []):
            if warning and "Geen kritieke" not in str(warning):
                warnings.append(f"Launcher bridge: {warning}")

        required_outputs = [
            self.output_root / "bib_dashboard.html",
            self.output_root / "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx",
            self.output_root / "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf",
            self.output_root / "PROJECT_PHOENIX_BIB_EXPORT.zip",
            self.output_root / "PROJECT_PHOENIX_BIB_FULL_EXPORT.zip",
            self.output_root / "bib_manifest.json",
            self.output_root / "bib_export_log.json",
            self.output_root / "bib_pdf_export_log.json",
            self.output_root / "bib_full_export_log.json",
            self.output_root / "bib_qa_qc_report.json",
            self.output_root / "bib_qa_qc_report.html",
            self.output_root / "bib_launcher_bridge_log.json",
        ]

        for path in required_outputs:
            if not path.exists():
                warnings.append(f"Verplichte workflow-output ontbreekt: {path}")

        if not self.project_index_path.exists():
            warnings.append(f"Project launcher ontbreekt: {self.project_index_path}")

        if not warnings:
            warnings.append("Geen kritieke BIB workflow-waarschuwingen.")

        return warnings

    def build_recommendation(
        self,
        full_export_result: Dict[str, Any],
        launcher_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        advice = [
            "Open outputs/projects/index.html en controleer de BIB-sectie.",
            "Open outputs/bib/bib_dashboard.html.",
            "Open outputs/bib/bib_qa_qc_report.html.",
            "Open outputs/bib/PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx.",
            "Open outputs/bib/PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf.",
            "Controleer outputs/bib/PROJECT_PHOENIX_BIB_FULL_EXPORT.zip.",
            "Na visuele controle: committen en pushen.",
        ]

        if full_export_result.get("status") == "WARNING":
            advice.insert(0, "Controleer eerst de QA/QC-waarschuwingen uit de full export.")

        if launcher_result.get("status") != "OPGESLAGEN":
            advice.insert(0, "Controleer eerst waarom de launcher bridge niet volledig is opgeslagen.")

        return {
            "status": "BIB_WORKFLOW_ADVIES",
            "advice": advice,
        }

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


def main() -> None:
    runner = BibWorkflowRunner()
    result = runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()