# PROJECT PHOENIX v7.0 UPDATE
# Project Intake Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v7.0 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\project_intake_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_0.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_0.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_0_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v7_0_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectIntakeEngine:
    ENGINE_NAME = "Project Phoenix Project Intake Engine"
    ENGINE_VERSION = "v7.0"

    def __init__(self) -> None:
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.input_txt = self.out / "project_intake_input.txt"
        self.input_json = self.out / "project_intake_input.json"
        self.template = self.out / "project_intake_input_template_v7_0.txt"
        self.intake = self.out / "project_intake_v7_0.json"
        self.context_seed = self.out / "project_context_seed_v7_0.json"
        self.log = self.out / "project_intake_log_v7_0.json"
        self.dashboard = self.out / "project_intake_dashboard_v7_0.html"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)
        self.write_template()
        raw = self.load_raw_input()
        parsed = self.parse(raw)
        intake = self.build_intake(parsed, raw)
        seed = self.build_context_seed(intake)

        self.write_json(self.intake, intake)
        self.write_json(self.context_seed, seed)

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "input_template_path": str(self.template),
            "intake_json_path": str(self.intake),
            "project_context_seed_path": str(self.context_seed),
            "intake_log_path": str(self.log),
            "intake_dashboard_path": str(self.dashboard),
            "project_name": intake["project"]["project_name"],
            "location": intake["project"]["location"],
            "project_type": intake["project"]["project_type"],
            "requested_output_count": len(intake["requested_outputs"]),
            "recommended_module_count": len(intake["recommended_modules"]),
            "assumption_count": len(intake["assumptions"]),
            "next_steps": [
                "Vul project_intake_input.txt of project_intake_input.json voor projectspecifieke invoer.",
                "Run START_PROJECTANALYSE opnieuw.",
                "Gebruik project_context_seed_v7_0.json als basis voor v7.1 Project Context Builder.",
            ],
        }

        self.write_json(self.log, result)
        self.write_text(self.dashboard, self.build_dashboard(result, intake))
        return result

    def write_template(self) -> None:
        if self.template.exists():
            return
        text = """PROJECT INTAKE TEMPLATE v7.0

Sla een ingevulde kopie op als:
outputs/projects/project_intake_input.txt

project_name: Moskee Bunschoten uitbreiding
location: Bikkersweg 88, Bunschoten
project_type: maatschappelijk / religieus gebouw
client: opdrachtgever
description: Ontwerp een uitbreiding inclusief vergunning, parkeren, AERIUS, constructie en tekeningen.
requested_outputs: rapportage_docx, rapportage_pdf, situatietekening, plattegronden, gevels, doorsneden, project_zip
uploads: tekeningen, foto's, kaartuitsnede
notes: Volledig autonoom uitvoeren met bronvermelding.
"""
        self.write_text(self.template, text)

    def load_raw_input(self) -> Dict[str, Any]:
        if self.input_json.exists():
            data = self.read_json(self.input_json)
            if data:
                return {"source": "json", "path": str(self.input_json), "data": data, "text": json.dumps(data, ensure_ascii=False)}
        if self.input_txt.exists():
            text = self.read_text(self.input_txt)
            if text.strip():
                return {"source": "text", "path": str(self.input_txt), "data": {}, "text": text}
        text = (
            "project_name: Project Phoenix intake test\n"
            "location: Locatie nog te bepalen\n"
            "project_type: algemeen bouwkundig / civiel project\n"
            "description: Automatische testintake voor Project Phoenix v7.0.\n"
            "requested_outputs: project_context, rapportage_docx, rapportage_pdf, bronvermelding, project_zip\n"
        )
        return {"source": "default", "path": "", "data": {}, "text": text}

    def parse(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if raw.get("source") == "json" and isinstance(raw.get("data"), dict):
            return raw["data"]
        parsed: Dict[str, Any] = {}
        aliases = {
            "project_name": ["project_name", "projectnaam", "project", "naam"],
            "location": ["location", "locatie", "adres"],
            "project_type": ["project_type", "projecttype", "type"],
            "client": ["client", "opdrachtgever"],
            "description": ["description", "omschrijving", "beschrijving"],
            "requested_outputs": ["requested_outputs", "outputs", "gewenste_outputs"],
            "uploads": ["uploads", "bijlagen", "bestanden"],
            "notes": ["notes", "notities", "opmerkingen"],
        }
        for line in str(raw.get("text", "")).splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            for target, names in aliases.items():
                if key in names:
                    parsed[target] = value
        for list_key in ["requested_outputs", "uploads"]:
            if isinstance(parsed.get(list_key), str):
                parsed[list_key] = [item.strip() for item in re.split(r"[,;]", parsed[list_key]) if item.strip()]
        return parsed

    def build_intake(self, parsed: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
        project = {
            "project_name": str(parsed.get("project_name", "")).strip() or "Nieuw Project Phoenix project",
            "location": str(parsed.get("location", "")).strip() or "Locatie nog te bepalen",
            "project_type": str(parsed.get("project_type", "")).strip() or "algemeen bouwkundig / civiel project",
            "client": str(parsed.get("client", "")).strip(),
            "description": str(parsed.get("description", "")).strip() or "Automatisch aangemaakte projectintake.",
        }
        assumptions = []
        for field in ["project_name", "location", "project_type", "description"]:
            if not str(parsed.get(field, "")).strip():
                assumptions.append({
                    "field": field,
                    "value": project[field],
                    "reason": "Ontbrekende invoer automatisch aangevuld.",
                    "confidence": "basis",
                    "source": self.ENGINE_NAME,
                })
        outputs = parsed.get("requested_outputs") or ["project_context", "rapportage_docx", "rapportage_pdf", "bronvermelding", "project_zip"]
        if not isinstance(outputs, list):
            outputs = ["project_context", "rapportage_docx", "rapportage_pdf", "bronvermelding", "project_zip"]
        modules = self.recommend_modules(project, outputs)
        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": raw.get("source", ""),
            "source_path": raw.get("path", ""),
            "project": project,
            "requested_outputs": outputs,
            "uploads": parsed.get("uploads", []) if isinstance(parsed.get("uploads", []), list) else [],
            "notes": str(parsed.get("notes", "")),
            "missing_required_fields": [field for field in ["project_name", "location", "project_type", "description"] if not str(parsed.get(field, "")).strip()],
            "assumptions": assumptions,
            "recommended_modules": modules,
            "workflow_policy": {
                "mode": "volledig_autonoom",
                "use_bib_first": True,
                "use_aaie_for_missing_data": True,
                "create_evidence": True,
                "create_project_zip": True,
                "run_health_check": True,
                "run_diagnostics_and_auto_repair": True,
            },
        }

    def recommend_modules(self, project: Dict[str, str], outputs: List[str]) -> List[Dict[str, str]]:
        text = " ".join([project.get("project_name", ""), project.get("location", ""), project.get("project_type", ""), project.get("description", ""), " ".join(outputs)]).lower()
        rules = [
            ("geotechniek", ["grond", "bodem", "fundering", "sondering", "grondwater"]),
            ("fundering", ["fundering", "poer", "strook", "palen"]),
            ("constructie", ["constructie", "kolom", "balk", "spant", "dak"]),
            ("cad_drawing_export", ["tekening", "dxf", "dwg", "skp", "plattegrond", "gevel", "doorsnede"]),
            ("vergunning", ["vergunning", "bopa", "omgevingswet", "aerius", "stikstof"]),
            ("verkeer_parkeren", ["parkeren", "parkeer", "verkeer", "crow"]),
            ("kosten_planning", ["kosten", "raming", "planning", "grex"]),
            ("rapportage_export", ["rapport", "pdf", "docx"]),
            ("evidence", ["bron", "evidence", "project_zip", "zip"]),
        ]
        found = []
        for module, keywords in rules:
            matched = [keyword for keyword in keywords if keyword in text]
            if matched:
                found.append({"module": module, "status": "aanbevolen", "reason": "Herkenning op: " + ", ".join(matched)})
        return found or [{"module": "project_start_analysis", "status": "aanbevolen", "reason": "Geen specifieke vakmodule herkend."}]

    def build_context_seed(self, intake: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "SEED",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": intake["project"],
            "requested_outputs": intake["requested_outputs"],
            "recommended_modules": intake["recommended_modules"],
            "assumptions": intake["assumptions"],
            "source_intake_path": str(self.intake),
            "next_engine": "Project Context Builder v7.1",
        }

    def build_dashboard(self, result: Dict[str, Any], intake: Dict[str, Any]) -> str:
        project = intake["project"]
        module_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('module', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            f"<td>{self.esc(item.get('reason', ''))}</td>"
            "</tr>"
            for item in intake["recommended_modules"]
        )
        output_rows = "".join(f"<tr><td>{self.esc(item)}</td></tr>" for item in intake["requested_outputs"])
        assumption_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('field', ''))}</td>"
            f"<td>{self.esc(item.get('value', ''))}</td>"
            f"<td>{self.esc(item.get('reason', ''))}</td>"
            "</tr>"
            for item in intake["assumptions"]
        ) or "<tr><td>OK</td><td>Geen</td><td>Geen ontbrekende basisvelden.</td></tr>"
        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Project Intake v7.0</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1240px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; margin-bottom:18px; }}
h1,h2 {{ color:#f8fafc; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ border:1px solid #334155; padding:10px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
code {{ color:#bfdbfe; }}
</style>
</head>
<body>
<main>
<section>
<h1>Project Phoenix Project Intake v7.0</h1>
<p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
<p>De projectopdracht is omgezet naar een gestructureerde intake en project context seed.</p>
</section>
<section>
<h2>Project</h2>
<p><strong>Naam:</strong> {self.esc(project.get("project_name", ""))}</p>
<p><strong>Locatie:</strong> {self.esc(project.get("location", ""))}</p>
<p><strong>Type:</strong> {self.esc(project.get("project_type", ""))}</p>
<p><strong>Omschrijving:</strong> {self.esc(project.get("description", ""))}</p>
</section>
<section><h2>Gewenste outputs</h2><table>{output_rows}</table></section>
<section><h2>Aanbevolen modules</h2><table><tr><th>Module</th><th>Status</th><th>Reden</th></tr>{module_rows}</table></section>
<section><h2>Aannames</h2><table><tr><th>Veld</th><th>Waarde</th><th>Reden</th></tr>{assumption_rows}</table></section>
<section>
<h2>Bestanden</h2>
<p><code>{self.esc(result.get("intake_json_path", ""))}</code></p>
<p><code>{self.esc(result.get("project_context_seed_path", ""))}</code></p>
<p><code>{self.esc(result.get("input_template_path", ""))}</code></p>
</section>
</main>
</body>
</html>
"""

    def read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return ""

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8-sig")

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


IntakeEngine = ProjectIntakeEngine
ProjectInputEngine = ProjectIntakeEngine


def main() -> None:
    engine = ProjectIntakeEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.0

python baoees\project_analyzer\project_intake_engine.py || goto error
python baoees\project_analyzer\brewster_knowledge_migration_engine.py || goto error
python baoees\project_analyzer\deep_knowledge_harvest_engine.py || goto error
python baoees\project_analyzer\module_registry_engine.py || goto error
python baoees\project_analyzer\project_start_analysis_engine.py || goto error
python baoees\project_analyzer\project_analyzer_workflow_engine.py || goto error
python baoees\project_analyzer\aaie_bib_assumption_loader.py || goto error
python baoees\project_analyzer\project_report_bib_engine.py || goto error
python baoees\project_analyzer\project_report_export_engine.py || goto error
python baoees\project_analyzer\project_package_evidence_engine.py || goto error
python baoees\project_analyzer\project_analyzer_launcher_bridge.py || goto error
python baoees\project_analyzer\project_analysis_health_check_engine.py || goto error
python baoees\project_analyzer\project_error_diagnostics_engine.py || goto error
python baoees\project_analyzer\project_auto_repair_engine.py || goto error
python baoees\project_analyzer\project_analysis_health_check_engine.py || goto error

echo PROJECT PHOENIX v7.0 START PROJECTANALYSE KLAAR

if exist "outputs\projects\project_intake_dashboard_v7_0.html" (
    start "" "outputs\projects\project_intake_dashboard_v7_0.html"
)

git status
pause
exit /b 0

:error
echo FOUT: START PROJECTANALYSE v7.0 is gestopt.
git status
pause
exit /b 1
'@

$Ps1Content = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.0" -ForegroundColor Cyan

$Steps = @(
    "baoees\project_analyzer\project_intake_engine.py",
    "baoees\project_analyzer\brewster_knowledge_migration_engine.py",
    "baoees\project_analyzer\deep_knowledge_harvest_engine.py",
    "baoees\project_analyzer\module_registry_engine.py",
    "baoees\project_analyzer\project_start_analysis_engine.py",
    "baoees\project_analyzer\project_analyzer_workflow_engine.py",
    "baoees\project_analyzer\aaie_bib_assumption_loader.py",
    "baoees\project_analyzer\project_report_bib_engine.py",
    "baoees\project_analyzer\project_report_export_engine.py",
    "baoees\project_analyzer\project_package_evidence_engine.py",
    "baoees\project_analyzer\project_analyzer_launcher_bridge.py",
    "baoees\project_analyzer\project_analysis_health_check_engine.py",
    "baoees\project_analyzer\project_error_diagnostics_engine.py",
    "baoees\project_analyzer\project_auto_repair_engine.py",
    "baoees\project_analyzer\project_analysis_health_check_engine.py"
)

$Index = 1
foreach ($Step in $Steps) {
    Write-Host "[$Index/$($Steps.Count)] $Step" -ForegroundColor Yellow
    python $Step
    if ($LASTEXITCODE -ne 0) {
        throw "Stap mislukt: $Step"
    }
    $Index++
}

Write-Host "PROJECT PHOENIX v7.0 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_intake_dashboard_v7_0.html"
if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $VersionedBatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $Ps1Path -Value $Ps1Content -Encoding UTF8
Set-Content -Path $VersionedPs1Path -Value $Ps1Content -Encoding UTF8

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Project Intake Connector"
    engine_version = "v7.0"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    project_intake_engine = "$EnginePath"
    purpose = "Voegt projectinvoer, intake-template en project context seed toe aan START_PROJECTANALYSE."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole project intake engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\project_intake_engine.py

Write-Host "Test START_PROJECTANALYSE_v7_0.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v7_0.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v7.0 UPDATE KLAAR" -ForegroundColor Green
