from __future__ import annotations

import hashlib
import html
import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BibExportEngine:
    """
    PROJECT PHOENIX / BAOEES V3
    BIB Export Engine v2.8

    Doel:
    - Scan de Brewster Integrated Bibliotheek in bib/
    - Maak manifest JSON
    - Maak exportlog JSON
    - Maak HTML knowledge dashboard
    - Maak ZIP-export
    - Leg basis Git Evidence vast
    """

    ENGINE_NAME = "Project Phoenix BIB Export Engine"
    ENGINE_VERSION = "v2.8"

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
        """
        Compatibility runner voor BAOEES Core.

        Deze methode moet bestaan zodat de engine later veilig vanuit de
        orchestrator kan worden aangeroepen.
        """

        self.output_root.mkdir(parents=True, exist_ok=True)

        scanned_files = self.scan_bib_files()
        manifest = self.build_manifest(scanned_files)
        git_evidence = self.build_git_evidence()

        manifest_path = self.output_root / "bib_manifest.json"
        export_log_path = self.output_root / "bib_export_log.json"
        git_evidence_path = self.output_root / "bib_git_evidence.json"
        dashboard_path = self.output_root / "bib_dashboard.html"
        zip_path = self.output_root / "PROJECT_PHOENIX_BIB_EXPORT.zip"

        self.write_json(manifest_path, manifest)
        self.write_json(git_evidence_path, git_evidence)

        dashboard_html = self.build_html_dashboard(
            manifest=manifest,
            git_evidence=git_evidence,
        )
        dashboard_path.write_text(dashboard_html, encoding="utf-8")

        zip_result = self.build_zip_export(
            files=scanned_files,
            zip_path=zip_path,
            extra_files=[manifest_path, git_evidence_path, dashboard_path],
        )

        export_log = self.build_export_log(
            manifest=manifest,
            git_evidence=git_evidence,
            dashboard_path=dashboard_path,
            zip_path=zip_path,
            zip_result=zip_result,
            extra_results=extra_results,
        )
        self.write_json(export_log_path, export_log)

        warnings = self.build_warnings(manifest, git_evidence)

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "bib_root": str(self.bib_root),
            "output_root": str(self.output_root),
            "file_count": len(scanned_files),
            "manifest_path": str(manifest_path),
            "export_log_path": str(export_log_path),
            "git_evidence_path": str(git_evidence_path),
            "dashboard_path": str(dashboard_path),
            "zip_path": str(zip_path),
            "zip_file_count": zip_result.get("file_count", 0),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "warnings": warnings,
            "recommendation": self.build_recommendation(warnings),
        }

    def scan_bib_files(self) -> List[Path]:
        if not self.bib_root.exists():
            return []

        files = []
        for path in self.bib_root.rglob("*"):
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

    def build_manifest(self, files: List[Path]) -> Dict[str, Any]:
        categories: Dict[str, Dict[str, Any]] = {}

        records = []
        for path in files:
            rel = self.safe_relative(path, self.bib_root)
            category = self.category_for(path)
            size = path.stat().st_size if path.exists() else 0

            record = {
                "name": path.name,
                "relative_path": rel,
                "category": category,
                "suffix": path.suffix,
                "size_bytes": size,
                "sha256": self.sha256_file(path),
            }
            records.append(record)

            if category not in categories:
                categories[category] = {
                    "category": category,
                    "file_count": 0,
                    "size_bytes": 0,
                }

            categories[category]["file_count"] += 1
            categories[category]["size_bytes"] += size

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "bib_root": str(self.bib_root),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "file_count": len(records),
            "categories": list(categories.values()),
            "files": records,
        }

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

    def build_html_dashboard(
        self,
        manifest: Dict[str, Any],
        git_evidence: Dict[str, Any],
    ) -> str:
        file_rows = []
        for item in manifest.get("files", []):
            rel = item.get("relative_path", "")
            file_rows.append(
                "<tr>"
                f"<td>{self.esc(item.get('category', ''))}</td>"
                f"<td><a href='../../bib/{self.esc(rel)}'>{self.esc(item.get('name', ''))}</a></td>"
                f"<td>{self.esc(item.get('suffix', ''))}</td>"
                f"<td>{self.esc(item.get('size_bytes', ''))}</td>"
                f"<td><code>{self.esc(item.get('sha256', ''))}</code></td>"
                "</tr>"
            )

        category_cards = []
        for category in manifest.get("categories", []):
            category_cards.append(
                "<div class='card'>"
                f"<h3>{self.esc(category.get('category', ''))}</h3>"
                f"<p><strong>{self.esc(category.get('file_count', 0))}</strong> bestanden</p>"
                f"<p>{self.esc(category.get('size_bytes', 0))} bytes</p>"
                "</div>"
            )

        git_badge_class = "ok" if git_evidence.get("working_tree_clean") else "warn"
        git_badge_text = "WORKING TREE CLEAN" if git_evidence.get("working_tree_clean") else "WORKING TREE DIRTY"

        return f"""<!doctype html>
<html lang="nl">
<head>
  <meta charset="utf-8">
  <title>Project Phoenix BIB Dashboard</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #050816;
      color: #f8fafc;
      line-height: 1.5;
    }}
    header {{
      padding: 34px 42px;
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
      border-bottom: 1px solid #334155;
    }}
    header h1 {{
      margin: 0;
      font-size: 34px;
    }}
    header p {{
      margin: 8px 0 0;
      color: #dbeafe;
    }}
    main {{
      padding: 30px 38px 50px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 18px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      font-weight: bold;
      font-size: 12px;
      border: 1px solid #334155;
    }}
    .ok {{
      background: rgba(16, 185, 129, 0.16);
      color: #86efac;
      border-color: rgba(16, 185, 129, 0.45);
    }}
    .warn {{
      background: rgba(245, 158, 11, 0.16);
      color: #fcd34d;
      border-color: rgba(245, 158, 11, 0.45);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #111827;
      border: 1px solid #334155;
      margin-top: 18px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #334155;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #0f172a;
      color: #bfdbfe;
    }}
    a {{
      color: #93c5fd;
      font-weight: bold;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    code {{
      color: #cbd5e1;
      font-size: 12px;
    }}
    footer {{
      padding: 22px 38px;
      border-top: 1px solid #334155;
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <h1>PROJECT PHOENIX BIB</h1>
    <p>Brewster Integrated Bibliotheek — HTML Knowledge Dashboard</p>
  </header>

  <main>
    <section class="grid">
      <div class="card">
        <h3>Status</h3>
        <p><span class="badge ok">{self.esc(manifest.get("status", ""))}</span></p>
      </div>
      <div class="card">
        <h3>Bestanden</h3>
        <p><strong>{self.esc(manifest.get("file_count", 0))}</strong> BIB-bestanden</p>
      </div>
      <div class="card">
        <h3>Git</h3>
        <p><span class="badge {git_badge_class}">{git_badge_text}</span></p>
        <p>Branch: {self.esc(git_evidence.get("branch", ""))}</p>
        <p>Commit: {self.esc(git_evidence.get("commit", ""))}</p>
      </div>
      <div class="card">
        <h3>Exportdatum</h3>
        <p>{self.esc(manifest.get("generated_at", ""))}</p>
      </div>
    </section>

    <h2>Categorieën</h2>
    <section class="grid">
      {''.join(category_cards)}
    </section>

    <h2>Bestandsmanifest</h2>
    <table>
      <thead>
        <tr>
          <th>Categorie</th>
          <th>Bestand</th>
          <th>Type</th>
          <th>Bytes</th>
          <th>SHA256</th>
        </tr>
      </thead>
      <tbody>
        {''.join(file_rows)}
      </tbody>
    </table>
  </main>

  <footer>
    {self.esc(self.ENGINE_NAME)} {self.esc(self.ENGINE_VERSION)}
  </footer>
</body>
</html>
"""

    def build_zip_export(
        self,
        files: List[Path],
        zip_path: Path,
        extra_files: Optional[List[Path]] = None,
    ) -> Dict[str, Any]:
        extra_files = extra_files or []

        zip_path.parent.mkdir(parents=True, exist_ok=True)

        file_count = 0
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path.exists() and path.is_file():
                    archive_name = Path("bib") / Path(self.safe_relative(path, self.bib_root))
                    zf.write(path, archive_name.as_posix())
                    file_count += 1

            for path in extra_files:
                if path.exists() and path.is_file():
                    archive_name = Path("exports") / path.name
                    zf.write(path, archive_name.as_posix())
                    file_count += 1

        return {
            "status": "OPGESLAGEN",
            "zip_path": str(zip_path),
            "file_count": file_count,
            "size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
        }

    def build_export_log(
        self,
        manifest: Dict[str, Any],
        git_evidence: Dict[str, Any],
        dashboard_path: Path,
        zip_path: Path,
        zip_result: Dict[str, Any],
        extra_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "bib_file_count": manifest.get("file_count", 0),
            "dashboard_path": str(dashboard_path),
            "zip_path": str(zip_path),
            "zip_result": zip_result,
            "git_evidence": git_evidence,
            "extra_results": extra_results,
        }

    def build_warnings(
        self,
        manifest: Dict[str, Any],
        git_evidence: Dict[str, Any],
    ) -> List[str]:
        warnings = []

        if not self.bib_root.exists():
            warnings.append("BIB-map ontbreekt.")

        if manifest.get("file_count", 0) == 0:
            warnings.append("Geen BIB-bestanden gevonden.")

        required_files = [
            self.bib_root / "00_BIB_INDEX.md",
            self.bib_root / "01_MASTER_KNOWLEDGE" / "PROJECT_PHOENIX_CORE_KNOWLEDGE.md",
            self.bib_root / "03_ENGINES" / "BAOEES_V3_ENGINE_REGISTER.md",
            self.bib_root / "04_STANDARDS_AND_RULES" / "PROJECT_PHOENIX_STANDARDS.md",
            self.bib_root / "09_ASSUMPTIONS" / "PROJECT_PHOENIX_ASSUMPTIONS.md",
            self.bib_root / "10_EXPORTS" / "BIB_EXPORT_PLAN.md",
        ]

        for required in required_files:
            if not required.exists():
                warnings.append(f"Verplicht BIB-bestand ontbreekt: {required}")

        if not git_evidence.get("working_tree_clean", False):
            warnings.append("Git working tree is niet clean tijdens BIB-export.")

        if not warnings:
            warnings.append("Geen kritieke BIB-exportwaarschuwingen.")

        return warnings

    def build_recommendation(self, warnings: List[str]) -> Dict[str, Any]:
        return {
            "status": "BIB_EXPORT_ADVIES",
            "advice": [
                "Controleer bib_dashboard.html visueel.",
                "Controleer bib_manifest.json op volledigheid.",
                "Controleer PROJECT_PHOENIX_BIB_EXPORT.zip.",
                "Voeg in v2.9 DOCX-export toe.",
                "Voeg in v3.0 PDF-export toe.",
            ],
            "warnings_count": len(warnings),
        }

    def category_for(self, path: Path) -> str:
        rel = self.safe_relative(path, self.bib_root)
        parts = Path(rel).parts

        if len(parts) == 1:
            return "00_INDEX"

        return parts[0]

    def sha256_file(self, path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

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

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


def main() -> None:
    engine = BibExportEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()