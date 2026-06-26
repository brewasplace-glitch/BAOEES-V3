from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from baoees.bib_export_engine.main import BibExportEngine
from baoees.bib_export_engine.pdf_export import BibPdfExportEngine
from baoees.bib_export_engine.bib_qa_qc import BibQaQcEngine


class BibFullExportRunner:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB Full Export Runner v3.4

    Doel:
    - Draait de BIB Export Engine.
    - Draait de BIB PDF Export Engine.
    - Draait de BIB QA/QC Engine.
    - Maakt een gecombineerde full export log.
    - Maakt een full ZIP met alle BIB-output.
    """

    ENGINE_NAME = "Project Phoenix BIB Full Export Runner"
    ENGINE_VERSION = "v3.4"

    def __init__(self, output_root: str | Path | None = None) -> None:
        self.output_root = Path(output_root) if output_root else Path("outputs") / "bib"

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)

        bib_export = BibExportEngine(output_root=self.output_root)
        pdf_export = BibPdfExportEngine(output_root=self.output_root)
        qa_qc_export = BibQaQcEngine(output_root=self.output_root)

        bib_result = bib_export.run(**extra_results)
        pdf_result = pdf_export.run(**extra_results)
        qa_qc_result = qa_qc_export.run(**extra_results)

        full_zip_path = self.output_root / "PROJECT_PHOENIX_BIB_FULL_EXPORT.zip"
        full_log_path = self.output_root / "bib_full_export_log.json"

        preliminary_result = {
            "status": "RUNNING",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "output_root": str(self.output_root),
            "bib_export": bib_result,
            "pdf_export": pdf_result,
            "qa_qc_export": qa_qc_result,
            "full_zip": {
                "status": "PENDING",
                "zip_path": str(full_zip_path),
            },
            "full_export_log_path": str(full_log_path),
            "warnings": [],
            "recommendation": {
                "status": "BIB_FULL_EXPORT_ADVIES",
                "advice": [
                    "Open bib_dashboard.html.",
                    "Open PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx.",
                    "Open PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf.",
                    "Open bib_qa_qc_report.html.",
                    "Controleer PROJECT_PHOENIX_BIB_FULL_EXPORT.zip.",
                ],
            },
        }

        self.write_json(full_log_path, preliminary_result)

        zip_result = self.build_full_zip(full_zip_path)

        result = {
            "status": self.determine_status(bib_result, pdf_result, qa_qc_result, zip_result),
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "output_root": str(self.output_root),
            "bib_export": bib_result,
            "pdf_export": pdf_result,
            "qa_qc_export": qa_qc_result,
            "full_zip": zip_result,
            "full_export_log_path": str(full_log_path),
            "warnings": self.build_warnings(bib_result, pdf_result, qa_qc_result, zip_result),
            "recommendation": self.build_recommendation(qa_qc_result),
        }

        self.write_json(full_log_path, result)
        return result

    def determine_status(
        self,
        bib_result: Dict[str, Any],
        pdf_result: Dict[str, Any],
        qa_qc_result: Dict[str, Any],
        zip_result: Dict[str, Any],
    ) -> str:
        if bib_result.get("status") != "OPGESLAGEN":
            return "FAILED"

        if pdf_result.get("status") != "OPGESLAGEN":
            return "FAILED"

        if zip_result.get("status") != "OPGESLAGEN":
            return "FAILED"

        if qa_qc_result.get("status") == "FAILED":
            return "WARNING"

        if qa_qc_result.get("status") == "WARNING":
            return "WARNING"

        return "OPGESLAGEN"

    def build_full_zip(self, zip_path: Path) -> Dict[str, Any]:
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        files = self.collect_output_files()
        file_count = 0

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path.resolve() == zip_path.resolve():
                    continue

                archive_name = Path("outputs") / "bib" / path.name
                zf.write(path, archive_name.as_posix())
                file_count += 1

            bib_root = Path("bib")
            if bib_root.exists():
                for path in sorted(bib_root.rglob("*")):
                    if path.is_file():
                        archive_name = Path("bib") / path.relative_to(bib_root)
                        zf.write(path, archive_name.as_posix())
                        file_count += 1

        return {
            "status": "OPGESLAGEN",
            "zip_path": str(zip_path),
            "file_count": file_count,
            "size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
        }

    def collect_output_files(self) -> List[Path]:
        if not self.output_root.exists():
            return []

        return sorted(
            [
                path
                for path in self.output_root.rglob("*")
                if path.is_file()
            ],
            key=lambda path: path.as_posix().lower(),
        )

    def build_warnings(
        self,
        bib_result: Dict[str, Any],
        pdf_result: Dict[str, Any],
        qa_qc_result: Dict[str, Any],
        zip_result: Dict[str, Any],
    ) -> List[str]:
        warnings: List[str] = []

        if bib_result.get("status") != "OPGESLAGEN":
            warnings.append("BIB basisexport is niet opgeslagen.")

        if pdf_result.get("status") != "OPGESLAGEN":
            warnings.append("BIB PDF-export is niet opgeslagen.")

        if qa_qc_result.get("status") == "FAILED":
            warnings.append("BIB QA/QC heeft verplichte fouten gevonden.")

        if qa_qc_result.get("status") == "WARNING":
            warnings.append("BIB QA/QC heeft waarschuwingen gevonden.")

        if zip_result.get("status") != "OPGESLAGEN":
            warnings.append("BIB full ZIP-export is niet opgeslagen.")

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
        ]

        for path in required_outputs:
            if not path.exists():
                warnings.append(f"Verplichte BIB-output ontbreekt: {path}")

        if not warnings:
            warnings.append("Geen kritieke BIB full export-waarschuwingen.")

        return warnings

    def build_recommendation(self, qa_qc_result: Dict[str, Any]) -> Dict[str, Any]:
        advice = [
            "Open bib_dashboard.html.",
            "Open PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.docx.",
            "Open PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf.",
            "Open bib_qa_qc_report.html.",
            "Controleer PROJECT_PHOENIX_BIB_FULL_EXPORT.zip.",
            "Koppel deze full export in v3.5 aan de Project Phoenix Launcher of hoofdworkflow.",
        ]

        qa_status = qa_qc_result.get("status")

        if qa_status == "FAILED":
            advice.insert(0, "Los eerst de BIB QA/QC fouten op.")
        elif qa_status == "WARNING":
            advice.insert(0, "Controleer de BIB QA/QC waarschuwingen.")

        return {
            "status": "BIB_FULL_EXPORT_ADVIES",
            "qa_qc_status": qa_status,
            "advice": advice,
        }

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )


def main() -> None:
    runner = BibFullExportRunner()
    result = runner.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()