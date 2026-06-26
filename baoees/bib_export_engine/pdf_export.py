from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class BibPdfExportEngine:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB PDF Export Engine v3.0

    Doel:
    - Scan de BIB-map.
    - Lees Markdown-bestanden.
    - Maak een eenvoudige PDF-export met alleen Python standaardbibliotheek.
    - Maak exportlog JSON.
    """

    ENGINE_NAME = "Project Phoenix BIB PDF Export Engine"
    ENGINE_VERSION = "v3.0"

    CATEGORY_ORDER = [
        "00_BIB_INDEX.md",
        "01_MASTER_KNOWLEDGE",
        "02_PROJECTS",
        "03_ENGINES",
        "04_STANDARDS_AND_RULES",
        "05_TEMPLATES",
        "06_WORKFLOWS",
        "07_LESSONS_LEARNED",
        "08_SOURCE_EVIDENCE",
        "09_ASSUMPTIONS",
        "10_EXPORTS",
    ]

    def __init__(
        self,
        bib_root: Optional[str | Path] = None,
        output_root: Optional[str | Path] = None,
    ) -> None:
        self.bib_root = Path(bib_root) if bib_root else Path("bib")
        self.output_root = Path(output_root) if output_root else Path("outputs") / "bib"

    def run(self, **extra_results: Any) -> Dict[str, Any]:
        self.output_root.mkdir(parents=True, exist_ok=True)

        markdown_files = self.scan_markdown_files()
        git_evidence = self.build_git_evidence()

        pdf_path = self.output_root / "PROJECT_PHOENIX_BIB_KNOWLEDGE_LIBRARY.pdf"
        log_path = self.output_root / "bib_pdf_export_log.json"

        pages = self.build_pages(markdown_files=markdown_files, git_evidence=git_evidence)
        self.write_pdf(pdf_path=pdf_path, pages=pages)

        export_log = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "bib_root": str(self.bib_root),
            "output_root": str(self.output_root),
            "pdf_path": str(pdf_path),
            "pdf_exists": pdf_path.exists(),
            "pdf_size_bytes": pdf_path.stat().st_size if pdf_path.exists() else 0,
            "markdown_file_count": len(markdown_files),
            "markdown_files": [self.safe_relative(path, self.bib_root) for path in markdown_files],
            "page_count": len(pages),
            "git_evidence": git_evidence,
            "extra_results": extra_results,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "warnings": self.build_warnings(markdown_files, pdf_path, git_evidence),
            "recommendation": {
                "status": "BIB_PDF_EXPORT_ADVIES",
                "advice": [
                    "Open de PDF visueel en controleer of de inhoud leesbaar is.",
                    "Gebruik deze v3.0 PDF als basisexport.",
                    "Maak later een professionele PDF op basis van DOCX of HTML styling.",
                    "Koppel deze PDF-export in een volgende versie aan BibExportEngine.run().",
                ],
            },
        }

        self.write_json(log_path, export_log)

        result = dict(export_log)
        result["export_log_path"] = str(log_path)
        return result

    def scan_markdown_files(self) -> List[Path]:
        if not self.bib_root.exists():
            return []

        files = []
        for path in self.bib_root.rglob("*.md"):
            if path.is_file():
                files.append(path)

        return sorted(files, key=self.sort_key)

    def sort_key(self, path: Path) -> tuple:
        rel = self.safe_relative(path, self.bib_root)
        parts = Path(rel).parts
        first = parts[0] if parts else rel

        try:
            index = self.CATEGORY_ORDER.index(first)
        except ValueError:
            index = 999

        return index, rel.lower()

    def build_pages(
        self,
        markdown_files: List[Path],
        git_evidence: Dict[str, Any],
    ) -> List[List[Tuple[str, int]]]:
        pages: List[List[Tuple[str, int]]] = []
        current_page: List[Tuple[str, int]] = []

        def add_line(text: str, size: int = 10) -> None:
            nonlocal current_page

            max_lines = 42
            if len(current_page) >= max_lines:
                pages.append(current_page)
                current_page = []

            current_page.append((text, size))

        def add_blank() -> None:
            add_line("", 10)

        add_line("PROJECT PHOENIX BIB KNOWLEDGE LIBRARY", 18)
        add_line("Brewster Integrated Bibliotheek", 13)
        add_blank()
        add_line(f"Exportdatum: {datetime.now().isoformat(timespec='seconds')}", 10)
        add_line(f"Branch: {git_evidence.get('branch', '')}", 10)
        add_line(f"Commit: {git_evidence.get('commit', '')}", 10)
        add_line(f"Working tree clean: {git_evidence.get('working_tree_clean', False)}", 10)
        add_line(f"Aantal Markdown-bestanden: {len(markdown_files)}", 10)
        add_blank()
        add_line("INHOUD", 14)

        for path in markdown_files:
            add_line(f"- {self.safe_relative(path, self.bib_root)}", 9)

        pages.append(current_page)
        current_page = []

        for path in markdown_files:
            rel = self.safe_relative(path, self.bib_root)
            add_line(rel, 15)
            add_blank()

            text = self.read_text_file(path)
            for raw_line in text.splitlines():
                for line, size in self.markdown_line_to_pdf_lines(raw_line):
                    wrapped = self.wrap_text(line, size)
                    for wrapped_line in wrapped:
                        add_line(wrapped_line, size)

            if current_page:
                pages.append(current_page)
                current_page = []

        if current_page:
            pages.append(current_page)

        return pages

    def markdown_line_to_pdf_lines(self, line: str) -> List[Tuple[str, int]]:
        stripped = line.strip()

        if stripped == "":
            return [("", 10)]

        if stripped.startswith("# "):
            return [(stripped[2:].strip(), 15)]

        if stripped.startswith("## "):
            return [(stripped[3:].strip(), 13)]

        if stripped.startswith("### "):
            return [(stripped[4:].strip(), 12)]

        if stripped.startswith("- "):
            return [(f"• {stripped[2:].strip()}", 10)]

        if re.match(r"^\d+\.\s+", stripped):
            return [(stripped, 10)]

        if stripped.startswith("|") and stripped.endswith("|"):
            return [(stripped, 8)]

        if stripped.startswith("```"):
            return [("", 10)]

        return [(stripped, 10)]

    def wrap_text(self, text: str, size: int) -> List[str]:
        if not text:
            return [""]

        max_chars = 95
        if size >= 15:
            max_chars = 55
        elif size >= 13:
            max_chars = 65
        elif size <= 8:
            max_chars = 115

        words = text.split()
        if not words:
            return [""]

        lines = []
        current = ""

        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    def write_pdf(self, pdf_path: Path, pages: List[List[Tuple[str, int]]]) -> None:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        objects: Dict[int, bytes] = {}

        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

        page_ids = []
        next_object_id = 4

        for page in pages:
            page_id = next_object_id
            content_id = next_object_id + 1
            next_object_id += 2

            page_ids.append(page_id)

            content_stream = self.build_pdf_content_stream(page)
            content_bytes = content_stream.encode("latin-1", errors="replace")

            objects[page_id] = (
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("latin-1")

            objects[content_id] = (
                f"<< /Length {len(content_bytes)} >>\n"
                "stream\n"
            ).encode("latin-1") + content_bytes + b"\nendstream"

        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects[2] = f"<< /Type /Pages /Kids [ {kids} ] /Count {len(page_ids)} >>".encode("latin-1")

        self.write_pdf_objects(pdf_path, objects)

    def build_pdf_content_stream(self, page: List[Tuple[str, int]]) -> str:
        y = 790
        lines = []

        for text, size in page:
            safe = self.pdf_escape(text)
            leading = max(size + 5, 14)

            lines.append(f"BT /F1 {size} Tf 50 {y} Td ({safe}) Tj ET")
            y -= leading

        return "\n".join(lines)

    def write_pdf_objects(self, pdf_path: Path, objects: Dict[int, bytes]) -> None:
        output = bytearray()
        output.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets: Dict[int, int] = {}

        for object_id in sorted(objects.keys()):
            offsets[object_id] = len(output)
            output.extend(f"{object_id} 0 obj\n".encode("latin-1"))
            output.extend(objects[object_id])
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        max_object_id = max(objects.keys())

        output.extend(f"xref\n0 {max_object_id + 1}\n".encode("latin-1"))
        output.extend(b"0000000000 65535 f \n")

        for object_id in range(1, max_object_id + 1):
            offset = offsets.get(object_id, 0)
            output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

        output.extend(
            (
                "trailer\n"
                f"<< /Size {max_object_id + 1} /Root 1 0 R >>\n"
                "startxref\n"
                f"{xref_offset}\n"
                "%%EOF\n"
            ).encode("latin-1")
        )

        pdf_path.write_bytes(bytes(output))

    def pdf_escape(self, text: str) -> str:
        text = text.replace("\\", "\\\\")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")
        text = text.replace("\t", " ")
        return text

    def build_git_evidence(self) -> Dict[str, Any]:
        branch = self.git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        commit = self.git_command(["rev-parse", "--short", "HEAD"])
        commit_full = self.git_command(["rev-parse", "HEAD"])
        commit_message = self.git_command(["log", "-1", "--pretty=%s"])
        status_short = self.git_command(["status", "--short"])
        remote = self.git_command(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])

        is_clean = status_short.strip() == ""

        return {
            "status": "CLEAN" if is_clean else "DIRTY",
            "repository": Path.cwd().name,
            "branch": branch.strip(),
            "remote_tracking_branch": remote.strip(),
            "commit": commit.strip(),
            "commit_full": commit_full.strip(),
            "commit_message": commit_message.strip(),
            "working_tree_clean": is_clean,
            "git_status_short": status_short,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def build_warnings(
        self,
        markdown_files: List[Path],
        pdf_path: Path,
        git_evidence: Dict[str, Any],
    ) -> List[str]:
        warnings = []

        if not self.bib_root.exists():
            warnings.append("BIB-map ontbreekt.")

        if not markdown_files:
            warnings.append("Geen Markdown-bestanden gevonden voor PDF-export.")

        if not pdf_path.exists():
            warnings.append("PDF-bestand is niet aangemaakt.")

        if not git_evidence.get("working_tree_clean", False):
            warnings.append("Git working tree was niet clean tijdens PDF-export.")

        if not warnings:
            warnings.append("Geen kritieke BIB PDF-exportwaarschuwingen.")

        return warnings

    def git_command(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return result.stderr.strip()
        except Exception as exc:
            return f"git command failed: {exc}"

    def read_text_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as exc:
            return f"[Kon bestand niet lezen: {path} — {exc}]"

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def safe_relative(self, path: Path, start: Path) -> str:
        try:
            return path.resolve().relative_to(start.resolve()).as_posix()
        except Exception:
            try:
                return path.relative_to(start).as_posix()
            except Exception:
                return path.as_posix()

    def sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()


def main() -> None:
    engine = BibPdfExportEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()