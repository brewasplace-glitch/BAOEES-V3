# PROJECT PHOENIX v7.1 UPDATE
# Project Context Builder Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v7.1 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\project_context_builder_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_1.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_1.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_1_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v7_1_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ProjectContextBuilderEngine:
    ENGINE_NAME = "Project Phoenix Project Context Builder Engine"
    ENGINE_VERSION = "v7.1"

    def __init__(self) -> None:
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.bib_root = PROJECT_ROOT / "outputs" / "bib"

        self.intake_path = self.out / "project_intake_v7_0.json"
        self.context_seed_path = self.out / "project_context_seed_v7_0.json"
        self.bib_index_path = self.bib_root / "index" / "bib_knowledge_content_index.json"
        self.aaie_path = self.out / "aaie_bib_assumptions.json"
        self.module_registry_path = self.out / "module_registry_v6_9.json"
        self.knowledge_base_path = self.bib_root / "knowledge" / "brewster_engineering_wizard_knowledge_base_v6_6.json"
        self.harvest_index_path = self.bib_root / "harvest" / "deep_knowledge_harvest_index_v6_8.json"

        self.context_path = self.out / "project_context_v7_1.json"
        self.context_summary_path = self.out / "project_context_summary_v7_1.md"
        self.context_log_path = self.out / "project_context_builder_log_v7_1.json"
        self.context_dashboard_path = self.out / "project_context_dashboard_v7_1.html"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        intake = self.read_json(self.intake_path)
        seed = self.read_json(self.context_seed_path)
        bib_index = self.read_json(self.bib_index_path)
        aaie = self.read_json(self.aaie_path)
        module_registry = self.read_json(self.module_registry_path)
        knowledge_base = self.read_json(self.knowledge_base_path)
        harvest_index = self.read_json(self.harvest_index_path)

        context = self.build_context(
            intake=intake,
            seed=seed,
            bib_index=bib_index,
            aaie=aaie,
            module_registry=module_registry,
            knowledge_base=knowledge_base,
            harvest_index=harvest_index,
        )

        self.write_json(self.context_path, context)
        self.write_text(self.context_summary_path, self.build_markdown_summary(context))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.out),
            "project_context_path": str(self.context_path),
            "project_context_summary_path": str(self.context_summary_path),
            "project_context_log_path": str(self.context_log_path),
            "project_context_dashboard_path": str(self.context_dashboard_path),
            "source_status": {
                "intake": "GELEZEN" if intake else "ONTBREEKT",
                "context_seed": "GELEZEN" if seed else "ONTBREEKT",
                "bib_index": "GELEZEN" if bib_index else "ONTBREEKT",
                "aaie": "GELEZEN" if aaie else "ONTBREEKT",
                "module_registry": "GELEZEN" if module_registry else "ONTBREEKT",
                "knowledge_base": "GELEZEN" if knowledge_base else "ONTBREEKT",
                "deep_harvest": "GELEZEN" if harvest_index else "ONTBREEKT",
            },
            "project_name": context["project"]["project_name"],
            "location": context["project"]["location"],
            "recommended_module_count": len(context["modules"]["recommended_modules"]),
            "active_core_engine_count": len(context["modules"]["active_core_engines"]),
            "assumption_count": len(context["assumptions"]),
            "knowledge_source_count": len(context["knowledge"]["sources"]),
            "risk_count": len(context["risks"]),
            "next_steps": [
                "Controleer project_context_dashboard_v7_1.html.",
                "Gebruik project_context_v7_1.json als centrale bron voor alle volgende engines.",
                "Leg v7.1 vast met git add, commit en push.",
                "Ga daarna door naar v7.2: geotechniek of fundering engine laten lezen uit project_context_v7_1.json.",
            ],
        }

        self.write_json(self.context_log_path, result)
        self.write_text(self.context_dashboard_path, self.build_dashboard(result, context))

        return result

    def build_context(
        self,
        intake: Dict[str, Any],
        seed: Dict[str, Any],
        bib_index: Dict[str, Any],
        aaie: Dict[str, Any],
        module_registry: Dict[str, Any],
        knowledge_base: Dict[str, Any],
        harvest_index: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = self.resolve_project(intake, seed)
        requested_outputs = self.resolve_requested_outputs(intake, seed)
        recommended_modules = self.resolve_recommended_modules(intake, seed)
        active_core_engines = self.resolve_active_core_engines(module_registry)
        assumptions = self.resolve_assumptions(intake, seed, aaie)
        knowledge_sources = self.resolve_knowledge_sources(bib_index, knowledge_base, harvest_index)
        risks = self.build_risks(project, recommended_modules, assumptions, module_registry)

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project": project,
            "requested_outputs": requested_outputs,
            "modules": {
                "recommended_modules": recommended_modules,
                "active_core_engines": active_core_engines,
                "missing_required_engines": self.resolve_missing_required_engines(module_registry),
            },
            "knowledge": {
                "bib_index_path": str(self.bib_index_path),
                "knowledge_base_path": str(self.knowledge_base_path),
                "harvest_index_path": str(self.harvest_index_path),
                "sources": knowledge_sources,
                "use_bib_first": True,
            },
            "assumptions": assumptions,
            "risks": risks,
            "workflow_policy": {
                "mode": "volledig_autonoom",
                "project_context_is_source_of_truth": True,
                "use_aaie_for_missing_data": True,
                "create_evidence": True,
                "create_project_zip": True,
                "run_health_check": True,
                "run_diagnostics_and_auto_repair": True,
            },
            "source_files": {
                "intake": str(self.intake_path),
                "context_seed": str(self.context_seed_path),
                "bib_index": str(self.bib_index_path),
                "aaie": str(self.aaie_path),
                "module_registry": str(self.module_registry_path),
                "knowledge_base": str(self.knowledge_base_path),
                "deep_harvest": str(self.harvest_index_path),
            },
        }

    def resolve_project(self, intake: Dict[str, Any], seed: Dict[str, Any]) -> Dict[str, Any]:
        project = {}
        if isinstance(seed.get("project"), dict):
            project.update(seed["project"])
        if isinstance(intake.get("project"), dict):
            project.update(intake["project"])

        defaults = {
            "project_name": "Nieuw Project Phoenix project",
            "location": "Locatie nog te bepalen",
            "project_type": "algemeen bouwkundig / civiel project",
            "client": "",
            "description": "Projectcontext automatisch opgebouwd.",
        }

        for key, value in defaults.items():
            if not str(project.get(key, "")).strip():
                project[key] = value

        return project

    def resolve_requested_outputs(self, intake: Dict[str, Any], seed: Dict[str, Any]) -> List[str]:
        outputs = []

        if isinstance(seed.get("requested_outputs"), list):
            outputs.extend(seed["requested_outputs"])

        if isinstance(intake.get("requested_outputs"), list):
            outputs.extend(intake["requested_outputs"])

        if not outputs:
            outputs = [
                "project_context",
                "rapportage_docx",
                "rapportage_pdf",
                "bronvermelding",
                "project_zip",
            ]

        return self.unique_strings(outputs)

    def resolve_recommended_modules(self, intake: Dict[str, Any], seed: Dict[str, Any]) -> List[Dict[str, Any]]:
        modules = []

        if isinstance(seed.get("recommended_modules"), list):
            modules.extend(seed["recommended_modules"])

        if isinstance(intake.get("recommended_modules"), list):
            modules.extend(intake["recommended_modules"])

        cleaned = []
        seen = set()

        for item in modules:
            if not isinstance(item, dict):
                continue

            module_name = str(item.get("module", "")).strip()

            if not module_name or module_name in seen:
                continue

            seen.add(module_name)
            cleaned.append(item)

        return cleaned

    def resolve_active_core_engines(self, module_registry: Dict[str, Any]) -> List[Dict[str, Any]]:
        registry_items = module_registry.get("registry_items", [])

        if not isinstance(registry_items, list):
            return []

        active = []

        for item in registry_items:
            if not isinstance(item, dict):
                continue

            if item.get("exists") and item.get("required"):
                active.append(
                    {
                        "engine_key": item.get("engine_key", ""),
                        "file": item.get("file", ""),
                        "category": item.get("category", ""),
                        "status": item.get("status", ""),
                    }
                )

        return active

    def resolve_missing_required_engines(self, module_registry: Dict[str, Any]) -> List[Dict[str, Any]]:
        registry_items = module_registry.get("registry_items", [])

        if not isinstance(registry_items, list):
            return []

        missing = []

        for item in registry_items:
            if not isinstance(item, dict):
                continue

            if item.get("required") and not item.get("exists"):
                missing.append(
                    {
                        "engine_key": item.get("engine_key", ""),
                        "file": item.get("file", ""),
                        "category": item.get("category", ""),
                        "status": item.get("status", ""),
                    }
                )

        return missing

    def resolve_assumptions(
        self,
        intake: Dict[str, Any],
        seed: Dict[str, Any],
        aaie: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        assumptions = []

        for source_name, source in [
            ("intake", intake),
            ("seed", seed),
            ("aaie", aaie),
        ]:
            source_assumptions = source.get("assumptions", [])

            if not isinstance(source_assumptions, list):
                continue

            for item in source_assumptions:
                if not isinstance(item, dict):
                    continue

                copied = dict(item)
                copied["source_group"] = source_name
                assumptions.append(copied)

        return assumptions

    def resolve_knowledge_sources(
        self,
        bib_index: Dict[str, Any],
        knowledge_base: Dict[str, Any],
        harvest_index: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        sources = []

        if bib_index:
            sources.append(
                {
                    "name": "BIB Knowledge Content Index",
                    "path": str(self.bib_index_path),
                    "status": bib_index.get("status", "GELEZEN"),
                    "type": "bib_index",
                }
            )

        if knowledge_base:
            sources.append(
                {
                    "name": "Brewster Engineering Wizard Knowledge Base",
                    "path": str(self.knowledge_base_path),
                    "status": knowledge_base.get("status", "GELEZEN"),
                    "type": "knowledge_base",
                }
            )

        if harvest_index:
            sources.append(
                {
                    "name": "Deep Knowledge Harvest",
                    "path": str(self.harvest_index_path),
                    "status": harvest_index.get("status", "GELEZEN"),
                    "type": "deep_harvest",
                }
            )

        return sources

    def build_risks(
        self,
        project: Dict[str, Any],
        recommended_modules: List[Dict[str, Any]],
        assumptions: List[Dict[str, Any]],
        module_registry: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        risks = []

        if project.get("location") == "Locatie nog te bepalen":
            risks.append(
                {
                    "risk": "Locatie ontbreekt",
                    "impact": "Kan geo, vergunning, parkeren en kosten beïnvloeden.",
                    "severity": "hoog",
                    "repair": "Vul project_intake_input.txt met locatie of adres.",
                }
            )

        if assumptions:
            risks.append(
                {
                    "risk": "Aannames aanwezig",
                    "impact": "Projectcontext bevat automatisch ingevulde gegevens.",
                    "severity": "middel",
                    "repair": "Controleer aannames in project_context_v7_1.json.",
                }
            )

        missing_required = self.resolve_missing_required_engines(module_registry)

        if missing_required:
            risks.append(
                {
                    "risk": "Verplichte engines ontbreken",
                    "impact": "Volledige workflow kan onvolledig zijn.",
                    "severity": "hoog",
                    "repair": "Controleer module_registry_dashboard_v6_9.html.",
                }
            )

        module_names = [str(item.get("module", "")) for item in recommended_modules]

        for required_module in ["geotechniek", "fundering", "constructie"]:
            if required_module in module_names:
                risks.append(
                    {
                        "risk": f"{required_module} nog conceptueel",
                        "impact": "Vakengine moet nog verder worden uitgebouwd.",
                        "severity": "middel",
                        "repair": f"Bouw {required_module} engine in volgende versies.",
                    }
                )

        return risks

    def build_markdown_summary(self, context: Dict[str, Any]) -> str:
        lines = []
        project = context["project"]

        lines.append("# Project Context v7.1")
        lines.append("")
        lines.append(f"Project: {project.get('project_name', '')}")
        lines.append(f"Locatie: {project.get('location', '')}")
        lines.append(f"Type: {project.get('project_type', '')}")
        lines.append("")
        lines.append("## Aanbevolen modules")
        lines.append("")

        for item in context["modules"]["recommended_modules"]:
            lines.append(f"- {item.get('module', '')}: {item.get('reason', '')}")

        lines.append("")
        lines.append("## Risico's")
        lines.append("")

        for risk in context["risks"]:
            lines.append(f"- {risk.get('risk', '')}: {risk.get('impact', '')}")

        lines.append("")

        return "\n".join(lines)

    def build_dashboard(
        self,
        result: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        project = context["project"]

        module_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('module', item.get('engine_key', '')))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            f"<td>{self.esc(item.get('reason', item.get('category', '')))}</td>"
            "</tr>"
            for item in context["modules"]["recommended_modules"]
        )

        core_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('engine_key', ''))}</td>"
            f"<td>{self.esc(item.get('category', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            "</tr>"
            for item in context["modules"]["active_core_engines"]
        )

        risk_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('risk', ''))}</td>"
            f"<td>{self.esc(item.get('severity', ''))}</td>"
            f"<td>{self.esc(item.get('impact', ''))}</td>"
            f"<td>{self.esc(item.get('repair', ''))}</td>"
            "</tr>"
            for item in context["risks"]
        )

        if not risk_rows:
            risk_rows = "<tr><td>OK</td><td>laag</td><td>Geen hoofdproblemen gevonden.</td><td>Geen actie nodig.</td></tr>"

        knowledge_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('name', ''))}</td>"
            f"<td>{self.esc(item.get('type', ''))}</td>"
            f"<td><code>{self.esc(item.get('path', ''))}</code></td>"
            "</tr>"
            for item in context["knowledge"]["sources"]
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Project Context v7.1</title>
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
<h1>Project Phoenix Project Context v7.1</h1>
<p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
<p>De centrale projectcontext is opgebouwd uit intake, BIB, AAIE, Module Registry en Deep Harvest.</p>
</section>

<section>
<h2>Project</h2>
<p><strong>Naam:</strong> {self.esc(project.get("project_name", ""))}</p>
<p><strong>Locatie:</strong> {self.esc(project.get("location", ""))}</p>
<p><strong>Type:</strong> {self.esc(project.get("project_type", ""))}</p>
<p><strong>Omschrijving:</strong> {self.esc(project.get("description", ""))}</p>
</section>

<section>
<h2>Aanbevolen modules</h2>
<table>
<tr><th>Module</th><th>Status</th><th>Reden</th></tr>
{module_rows}
</table>
</section>

<section>
<h2>Actieve core engines</h2>
<table>
<tr><th>Engine</th><th>Categorie</th><th>Status</th></tr>
{core_rows}
</table>
</section>

<section>
<h2>Kennisbronnen</h2>
<table>
<tr><th>Naam</th><th>Type</th><th>Pad</th></tr>
{knowledge_rows}
</table>
</section>

<section>
<h2>Risico's en aandachtspunten</h2>
<table>
<tr><th>Risico</th><th>Ernst</th><th>Impact</th><th>Herstel</th></tr>
{risk_rows}
</table>
</section>

<section>
<h2>Bestanden</h2>
<p><code>{self.esc(result.get("project_context_path", ""))}</code></p>
<p><code>{self.esc(result.get("project_context_summary_path", ""))}</code></p>
</section>
</main>
</body>
</html>
"""

    def unique_strings(self, values: List[Any]) -> List[str]:
        result = []
        seen = set()

        for value in values:
            text = str(value).strip()

            if not text or text in seen:
                continue

            seen.add(text)
            result.append(text)

        return result

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
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8-sig",
        )

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


ContextBuilderEngine = ProjectContextBuilderEngine
ProjectContextEngine = ProjectContextBuilderEngine


def main() -> None:
    engine = ProjectContextBuilderEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.1

python baoees\project_analyzer\project_intake_engine.py || goto error
python baoees\project_analyzer\brewster_knowledge_migration_engine.py || goto error
python baoees\project_analyzer\deep_knowledge_harvest_engine.py || goto error
python baoees\project_analyzer\module_registry_engine.py || goto error
python baoees\project_analyzer\aaie_bib_assumption_loader.py || goto error
python baoees\project_analyzer\project_context_builder_engine.py || goto error
python baoees\project_analyzer\project_start_analysis_engine.py || goto error
python baoees\project_analyzer\project_analyzer_workflow_engine.py || goto error
python baoees\project_analyzer\project_report_bib_engine.py || goto error
python baoees\project_analyzer\project_report_export_engine.py || goto error
python baoees\project_analyzer\project_package_evidence_engine.py || goto error
python baoees\project_analyzer\project_analyzer_launcher_bridge.py || goto error
python baoees\project_analyzer\project_analysis_health_check_engine.py || goto error
python baoees\project_analyzer\project_error_diagnostics_engine.py || goto error
python baoees\project_analyzer\project_auto_repair_engine.py || goto error
python baoees\project_analyzer\project_analysis_health_check_engine.py || goto error

echo PROJECT PHOENIX v7.1 START PROJECTANALYSE KLAAR

if exist "outputs\projects\project_context_dashboard_v7_1.html" (
    start "" "outputs\projects\project_context_dashboard_v7_1.html"
)

git status
pause
exit /b 0

:error
echo FOUT: START PROJECTANALYSE v7.1 is gestopt.
git status
pause
exit /b 1
'@

$Ps1Content = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.1" -ForegroundColor Cyan

$Steps = @(
    "baoees\project_analyzer\project_intake_engine.py",
    "baoees\project_analyzer\brewster_knowledge_migration_engine.py",
    "baoees\project_analyzer\deep_knowledge_harvest_engine.py",
    "baoees\project_analyzer\module_registry_engine.py",
    "baoees\project_analyzer\aaie_bib_assumption_loader.py",
    "baoees\project_analyzer\project_context_builder_engine.py",
    "baoees\project_analyzer\project_start_analysis_engine.py",
    "baoees\project_analyzer\project_analyzer_workflow_engine.py",
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

Write-Host "PROJECT PHOENIX v7.1 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_context_dashboard_v7_1.html"
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
    engine = "Project Phoenix Project Context Builder Connector"
    engine_version = "v7.1"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    project_context_builder_engine = "$EnginePath"
    purpose = "Maakt centrale project_context_v7_1.json uit intake, BIB, AAIE, Module Registry en Deep Harvest."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole project context builder engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\project_context_builder_engine.py

Write-Host "Test START_PROJECTANALYSE_v7_1.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v7_1.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v7.1 UPDATE KLAAR" -ForegroundColor Green
