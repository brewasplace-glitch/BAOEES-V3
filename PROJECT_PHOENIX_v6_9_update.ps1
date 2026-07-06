# PROJECT PHOENIX v6.9 UPDATE
# Module Registry & Engine Dashboard
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v6.9 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\module_registry_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_9.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v6_9.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v6_9_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v6_9_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import ast
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ModuleRegistryEngine:
    ENGINE_NAME = "Project Phoenix Module Registry & Engine Dashboard"
    ENGINE_VERSION = "v6.9"

    EXPECTED = [
        ("brewster_knowledge_migration_engine.py", "knowledge", True, "Brewster kennis naar BIB"),
        ("deep_knowledge_harvest_engine.py", "knowledge", True, "Deep harvest lokale kennis"),
        ("module_registry_engine.py", "registry", True, "Engine register"),
        ("project_start_analysis_engine.py", "workflow", True, "Startanalyse"),
        ("project_analyzer_workflow_engine.py", "workflow", True, "Workflow"),
        ("aaie_bib_assumption_loader.py", "aaie", True, "AAIE/BIB aannames"),
        ("project_report_bib_engine.py", "reporting", True, "Rapportagepackage"),
        ("project_report_export_engine.py", "export", True, "DOCX/PDF export"),
        ("project_package_evidence_engine.py", "evidence", True, "Evidence en projectpakket"),
        ("project_analyzer_launcher_bridge.py", "dashboard", True, "Startdashboard bridge"),
        ("project_analysis_health_check_engine.py", "qaqc", True, "Health check"),
        ("project_error_diagnostics_engine.py", "qaqc", True, "Foutherkenning"),
        ("project_auto_repair_engine.py", "qaqc", True, "Veilige auto repair"),
        ("geotechniek_engine.py", "to_build", False, "Nog te bouwen: geotechniek"),
        ("foundation_engine.py", "to_build", False, "Nog te bouwen: fundering"),
        ("structural_engine.py", "to_build", False, "Nog te bouwen: constructie"),
        ("cad_drawing_export_engine.py", "to_build", False, "Nog te bouwen: tekeningen/CAD"),
        ("permit_engine.py", "to_build", False, "Nog te bouwen: vergunningen"),
        ("traffic_parking_engine.py", "to_build", False, "Nog te bouwen: verkeer/parkeren"),
        ("cost_planning_engine.py", "to_build", False, "Nog te bouwen: kosten/planning"),
    ]

    def __init__(self) -> None:
        self.root = PROJECT_ROOT / "baoees" / "project_analyzer"
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.bib_index = PROJECT_ROOT / "outputs" / "bib" / "index" / "bib_knowledge_content_index.json"
        self.registry_path = self.out / "module_registry_v6_9.json"
        self.log_path = self.out / "module_registry_log_v6_9.json"
        self.dashboard_path = self.out / "module_registry_dashboard_v6_9.html"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)
        items = self.build_items()
        summary = self.summary(items)
        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "registry_path": str(self.registry_path),
            "log_path": str(self.log_path),
            "dashboard_path": str(self.dashboard_path),
            "summary": summary,
            "registry_items": items,
            "next_steps": [
                "Controleer module_registry_dashboard_v6_9.html.",
                "Gebruik dit register als basis voor de echte vakmodules.",
                "Volgende stap: Project Intake Engine of Geotechniek Engine.",
            ],
        }
        self.write_json(self.registry_path, result)
        self.write_json(self.log_path, result)
        self.write_text(self.dashboard_path, self.dashboard(result))
        self.update_bib(result)
        return result

    def build_items(self) -> List[Dict[str, Any]]:
        found = {}
        if self.root.exists():
            for path in self.root.glob("*.py"):
                found[path.name] = self.inspect(path)

        items = []
        for file_name, category, required, description in self.EXPECTED:
            info = found.get(file_name, {})
            exists = bool(info)
            if exists:
                status = "AANWEZIG"
            elif required:
                status = "ONTBREEKT_REQUIRED"
            else:
                status = "NOG_TE_BOUWEN"
            items.append({
                "file": file_name,
                "engine_key": file_name.replace(".py", ""),
                "category": category,
                "required": required,
                "description": description,
                "exists": exists,
                "status": status,
                "relative_path": info.get("relative_path", f"baoees/project_analyzer/{file_name}"),
                "classes": info.get("classes", []),
                "functions": info.get("functions", []),
                "size_bytes": info.get("size_bytes", 0),
                "modified_at": info.get("modified_at", ""),
            })

        expected_files = {item[0] for item in self.EXPECTED}
        for file_name, info in sorted(found.items()):
            if file_name not in expected_files and file_name != "__init__.py":
                items.append({
                    "file": file_name,
                    "engine_key": file_name.replace(".py", ""),
                    "category": "extra_discovered",
                    "required": False,
                    "description": "Extra ontdekt Pythonbestand.",
                    "exists": True,
                    "status": "AANWEZIG_EXTRA",
                    "relative_path": info.get("relative_path", ""),
                    "classes": info.get("classes", []),
                    "functions": info.get("functions", []),
                    "size_bytes": info.get("size_bytes", 0),
                    "modified_at": info.get("modified_at", ""),
                })
        return items

    def inspect(self, path: Path) -> Dict[str, Any]:
        text = self.read_text(path)
        classes = []
        functions = []
        try:
            tree = ast.parse(text)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except Exception:
            pass
        stat = path.stat()
        return {
            "relative_path": self.relative(path),
            "classes": classes,
            "functions": functions,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        }

    def summary(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        required = [item for item in items if item["required"]]
        required_present = [item for item in required if item["exists"]]
        missing_required = [item for item in required if not item["exists"]]
        optional_missing = [item for item in items if not item["required"] and not item["exists"]]
        readiness = int(round((len(required_present) / len(required)) * 100)) if required else 0
        return {
            "status": "CORE_COMPLEET" if not missing_required else "CORE_ONVOLLEDIG",
            "total_items": len(items),
            "present_count": len([item for item in items if item["exists"]]),
            "required_count": len(required),
            "required_present_count": len(required_present),
            "required_missing_count": len(missing_required),
            "optional_missing_count": len(optional_missing),
            "core_readiness_percent": readiness,
        }

    def update_bib(self, result: Dict[str, Any]) -> None:
        data = self.read_json(self.bib_index)
        if not data:
            data = {}
        data["status"] = "BIJGEWERKT"
        data["last_updated_by"] = self.ENGINE_NAME
        data["last_updated_version"] = self.ENGINE_VERSION
        data["last_updated_at"] = datetime.now().isoformat(timespec="seconds")
        data["module_registry"] = {
            "registry_path": str(self.registry_path),
            "dashboard_path": str(self.dashboard_path),
            "summary": result["summary"],
        }
        records = data.get("recognized_text_items", [])
        if not isinstance(records, list):
            records = []
        records.append({
            "source": "module_registry_v6_9",
            "type": "engine_registry",
            "title": "Module Registry & Engine Dashboard v6.9",
            "summary": "Alle bekende Phoenix-engines en geplande modules geregistreerd.",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        data["recognized_text_items"] = records
        self.write_json(self.bib_index, data)

    def dashboard(self, result: Dict[str, Any]) -> str:
        summary = result["summary"]
        rows = "".join(
            "<tr>"
            f"<td>{self.esc(item['engine_key'])}</td>"
            f"<td>{self.esc(item['category'])}</td>"
            f"<td>{self.esc(item['status'])}</td>"
            f"<td>{self.esc(item['required'])}</td>"
            f"<td><code>{self.esc(item['relative_path'])}</code></td>"
            f"<td>{self.esc(', '.join(item['classes']))}</td>"
            f"<td>{self.esc(item['description'])}</td>"
            "</tr>"
            for item in result["registry_items"]
        )
        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Module Registry v6.9</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1320px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; margin-bottom:18px; }}
h1,h2 {{ color:#f8fafc; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ border:1px solid #334155; padding:10px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
code {{ color:#bfdbfe; }}
.score {{ font-size:34px; font-weight:bold; color:#86efac; }}
</style>
</head>
<body>
<main>
<section>
<h1>Project Phoenix Module Registry & Engine Dashboard v6.9</h1>
<p>Status: <strong>{self.esc(summary['status'])}</strong></p>
<p class="score">{self.esc(summary['core_readiness_percent'])}% core readiness</p>
</section>
<section>
<h2>Samenvatting</h2>
<p>Items totaal: {self.esc(summary['total_items'])}</p>
<p>Aanwezig: {self.esc(summary['present_count'])}</p>
<p>Required aanwezig: {self.esc(summary['required_present_count'])}/{self.esc(summary['required_count'])}</p>
<p>Required ontbrekend: {self.esc(summary['required_missing_count'])}</p>
<p>Optioneel nog te bouwen: {self.esc(summary['optional_missing_count'])}</p>
</section>
<section>
<h2>Engine Registry</h2>
<table>
<tr><th>Engine</th><th>Categorie</th><th>Status</th><th>Required</th><th>Bestand</th><th>Classes</th><th>Omschrijving</th></tr>
{rows}
</table>
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

    def relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(PROJECT_ROOT))
        except Exception:
            return str(path)

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


EngineRegistry = ModuleRegistryEngine
ProjectModuleRegistryEngine = ModuleRegistryEngine


def main() -> None:
    engine = ModuleRegistryEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.9
echo ============================================================

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

echo.
echo PROJECT PHOENIX v6.9 START PROJECTANALYSE KLAAR

if exist "outputs\projects\module_registry_dashboard_v6_9.html" (
    start "" "outputs\projects\module_registry_dashboard_v6_9.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.9 is gestopt.
git status
pause
exit /b 1
'@

$Ps1Content = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.9" -ForegroundColor Cyan

$Steps = @(
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

Write-Host "PROJECT PHOENIX v6.9 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$Dashboard = Join-Path $PSScriptRoot "outputs\projects\module_registry_dashboard_v6_9.html"
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
    engine = "Project Phoenix Module Registry Connector"
    engine_version = "v6.9"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    module_registry_engine = "$EnginePath"
    purpose = "Registreert alle bestaande en geplande Phoenix-engines en koppelt dashboard aan START_PROJECTANALYSE."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole module registry engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\module_registry_engine.py

Write-Host "Test START_PROJECTANALYSE_v6_9.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v6_9.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v6.9 UPDATE KLAAR" -ForegroundColor Green
