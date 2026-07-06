# PROJECT PHOENIX v7.4 UPDATE
# Structural Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"
Write-Host "PROJECT PHOENIX v7.4 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location
if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\structural_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_4.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_4.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_4_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null
foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) { Copy-Item $Path "$Path.backup_v7_4_$Timestamp" -Force }
}

$EngineContent = @'
from __future__ import annotations
import html, json, sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class StructuralEngine:
    ENGINE_NAME = "Project Phoenix Structural Engine"
    ENGINE_VERSION = "v7.4"

    def __init__(self) -> None:
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.context_path = self.out / "project_context_v7_1.json"
        self.geo_path = self.out / "project_geotechniek_v7_2.json"
        self.foundation_path = self.out / "project_foundation_design_v7_3.json"
        self.structural_json_path = self.out / "project_structural_model_v7_4.json"
        self.structural_summary_path = self.out / "project_structural_summary_v7_4.md"
        self.structural_log_path = self.out / "project_structural_log_v7_4.json"
        self.structural_dashboard_path = self.out / "project_structural_dashboard_v7_4.html"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now().isoformat(timespec="seconds")
        context = self.read_json(self.context_path)
        geotechniek = self.read_json(self.geo_path)
        foundation = self.read_json(self.foundation_path)
        structural = self.build_structural_model(context, geotechniek, foundation)
        self.write_json(self.structural_json_path, structural)
        self.write_text(self.structural_summary_path, self.build_markdown(structural))
        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_context_path": str(self.context_path),
            "geotechniek_path": str(self.geo_path),
            "foundation_path": str(self.foundation_path),
            "structural_json_path": str(self.structural_json_path),
            "structural_summary_path": str(self.structural_summary_path),
            "structural_log_path": str(self.structural_log_path),
            "structural_dashboard_path": str(self.structural_dashboard_path),
            "source_status": {
                "project_context": "GELEZEN" if context else "ONTBREEKT",
                "geotechniek": "GELEZEN" if geotechniek else "ONTBREEKT",
                "foundation": "GELEZEN" if foundation else "ONTBREEKT",
            },
            "project_name": structural["project"]["project_name"],
            "structural_system": structural["selected_system"]["system_type"],
            "foundation_type": structural["foundation_interface"]["foundation_type"],
            "element_count": len(structural["elements"]),
            "load_case_count": len(structural["load_assumptions"]),
            "risk_count": len(structural["risks"]),
            "next_steps": [
                "Controleer project_structural_dashboard_v7_4.html.",
                "Controleer project_structural_model_v7_4.json.",
                "Gebruik structural-output als basis voor v7.5 CAD Drawing Export Engine.",
            ],
        }
        self.write_json(self.structural_log_path, result)
        self.write_text(self.structural_dashboard_path, self.build_dashboard(result, structural))
        return result

    def build_structural_model(self, context: Dict[str, Any], geotechniek: Dict[str, Any], foundation: Dict[str, Any]) -> Dict[str, Any]:
        project = self.resolve_project(context, foundation)
        text = " ".join([json.dumps(context, ensure_ascii=False, default=str), json.dumps(geotechniek, ensure_ascii=False, default=str), json.dumps(foundation, ensure_ascii=False, default=str)]).lower()
        system = self.select_system(text)
        grid = self.build_grid(text)
        elements = self.build_elements(text)
        loads = self.build_loads(text)
        foundation_interface = self.foundation_interface(foundation)
        risks = self.build_risks(project, grid, foundation)
        return {
            "status": "VOORLOPIG_CONCEPT",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "selected_system": system,
            "preliminary_grid": grid,
            "elements": elements,
            "load_assumptions": loads,
            "load_paths": [
                {"path": "dak -> liggers/spanten -> muren/kolommen -> fundering", "status": "conceptueel"},
                {"path": "vloer/wanden -> dragende muren -> funderingsbalk -> ondergrond", "status": "conceptueel"},
                {"path": "wind -> dak/vloerschijf -> stabiliteitswanden -> fundering", "status": "nader te toetsen"},
            ],
            "foundation_interface": foundation_interface,
            "analysis_engines": {
                "open_stack_policy": "SCIA/Viktor vervangen door open engines",
                "future_targets": ["OpenSees", "CalculiX", "FreeCAD BIM"],
            },
            "required_checks": [
                {"check": "geometrie en assen", "status": "open", "input_needed": "plattegrond, doorsnede, SKP/DWG/DXF/BIM"},
                {"check": "belastingcombinaties", "status": "open", "input_needed": "normkeuze, functie, materiaal, overspanningen"},
                {"check": "kolom- en balkdimensionering", "status": "open", "input_needed": "lijnlasten, kolomlasten, overspanningen"},
                {"check": "stabiliteit", "status": "open", "input_needed": "windbelasting, schijfwerking, stabiliteitswanden"},
                {"check": "OpenSees/CalculiX export", "status": "later", "input_needed": "rekenmodelgeneratie"},
            ],
            "risks": risks,
            "assumptions": [
                {"field": "structural_system", "value": system["system_type"], "confidence": "basis", "source": self.ENGINE_NAME, "reason": system["reason"]},
                {"field": "grid", "value": grid["source"], "confidence": "basis", "source": self.ENGINE_NAME, "reason": "Geen definitieve CAD/BIM-geometrie beschikbaar."},
                {"field": "loads", "value": f"{len(loads)} voorlopige load cases", "confidence": "basis", "source": self.ENGINE_NAME, "reason": "Belastingen zijn placeholders."},
            ],
            "outputs_for_next_engine": {
                "next_engine": "CAD Drawing Export Engine v7.5",
                "drawing_layers": ["constructie_assen", "kolommen", "balken", "dragende_muren", "dakconstructie", "fundering_interface"],
                "export_targets": ["DXF", "DWG", "SKP", "IFC", "PDF"],
            },
            "not_for_execution_note": "Automatisch constructief concept; definitief ontwerp vereist geometrie, belastingen, normkeuze en berekening.",
        }

    def resolve_project(self, context: Dict[str, Any], foundation: Dict[str, Any]) -> Dict[str, Any]:
        project = {}
        if isinstance(context.get("project"), dict): project.update(context["project"])
        if isinstance(foundation.get("project"), dict):
            for k, v in foundation["project"].items():
                if v and not project.get(k): project[k] = v
        defaults = {"project_name": "Nieuw Project Phoenix project", "location": "Locatie nog te bepalen", "project_type": "algemeen bouwkundig / civiel project", "description": "Voorlopig constructief concept."}
        for k, v in defaults.items():
            if not str(project.get(k, "")).strip(): project[k] = v
        return project

    def select_system(self, text: str) -> Dict[str, Any]:
        if any(w in text for w in ["moskee", "gebedsruimte", "maatschappelijk", "religieus"]):
            return {"system_type": "gemengd_systeem_dragende_muren_met_stalen_of_houten_dakliggers", "status": "VOORLOPIG", "reason": "Maatschappelijke/religieuze functie herkend; open ruimten vragen om dakliggers/spanten en dragende wanden/kolommen.", "stability_concept": "schijfwerking dak/vloer plus dragende wanden; stabiliteit nader toetsen"}
        if any(w in text for w in ["woning", "villa", "woonhuis"]):
            return {"system_type": "dragende_muren_met_houten_of_stalen_dakconstructie", "status": "VOORLOPIG", "reason": "Woonfunctie herkend; standaard draagstructuur met dragende wanden en dakliggers.", "stability_concept": "dragende wanden en schijfwerking vloeren/dak"}
        return {"system_type": "algemeen_draagstructuur_concept", "status": "VOORLOPIG", "reason": "Geen specifiek gebouwtype met geometrie gevonden; generiek constructief concept gekozen.", "stability_concept": "nog te bepalen na plattegrond en geometrie"}

    def build_grid(self, text: str) -> Dict[str, Any]:
        grid = {"status": "VOORLOPIG", "source": "automatische standaardgrid totdat CAD/BIM-geometrie beschikbaar is", "axis_spacing_m": {"x_default": 5.0, "y_default": 5.0}, "assumed_bays": {"x_direction": 2, "y_direction": 2}, "needs_real_geometry": True}
        if "20 m2" in text or "20 m²" in text or "20m2" in text:
            grid.update({"assumed_extension_area_m2": 20, "axis_spacing_m": {"x_default": 4.0, "y_default": 5.0}, "assumed_bays": {"x_direction": 1, "y_direction": 1}, "source": "uitbreiding circa 20 m2 herkend"})
        return grid

    def build_elements(self, text: str):
        elements = [
            {"element_id": "WALL-001", "type": "dragende_wand", "material": "metselwerk/beton voorlopig", "function": "verticale belastingafdracht en stabiliteit", "status": "concept"},
            {"element_id": "COL-001", "type": "kolom", "material": "staal/beton voorlopig", "function": "ondersteuning balken/dakliggers", "status": "optioneel"},
            {"element_id": "BEAM-001", "type": "balk", "material": "staal/beton/hout voorlopig", "function": "afdracht vloer-/daklasten", "status": "concept"},
            {"element_id": "ROOF-001", "type": "dakconstructie", "material": "hout of staal voorlopig", "function": "afdracht daklasten en wind", "status": "concept"},
            {"element_id": "FOUNDATION-INTERFACE-001", "type": "fundering_koppeling", "material": "beton", "function": "overdracht lijnlasten/kolomlasten naar fundering", "status": "concept"},
        ]
        if any(w in text for w in ["spant", "grote ruimte", "gebedsruimte"]):
            elements.append({"element_id": "TRUSS-001", "type": "dakspant", "material": "staal of hout voorlopig", "function": "vrije overspanning over hoofdruimte", "status": "concept"})
        return elements

    def build_loads(self, text: str):
        loads = [
            {"load_case": "LC1", "name": "eigen gewicht", "type": "permanent", "preliminary_value": "nader te bepalen", "status": "open"},
            {"load_case": "LC2", "name": "vloerbelasting", "type": "veranderlijk", "preliminary_value": "functieafhankelijk", "status": "open"},
            {"load_case": "LC3", "name": "dakbelasting", "type": "permanent/veranderlijk", "preliminary_value": "dakopbouw + variabel", "status": "open"},
            {"load_case": "LC4", "name": "windbelasting", "type": "horizontaal", "preliminary_value": "locatie- en hoogteafhankelijk", "status": "open"},
        ]
        if any(w in text for w in ["moskee", "gebedsruimte", "bijeenkomst"]):
            loads.append({"load_case": "LC5", "name": "bijeenkomstfunctie / personenbelasting", "type": "veranderlijk", "preliminary_value": "nader vast te stellen", "status": "open"})
        return loads

    def foundation_interface(self, foundation: Dict[str, Any]) -> Dict[str, Any]:
        selected = foundation.get("selected_concept", {}) if isinstance(foundation, dict) else {}
        return {"foundation_type": selected.get("type", "onbekend"), "foundation_level": selected.get("foundation_level", "P = -0,50 m voorlopig"), "strip_width_cm": selected.get("strip_width_cm", 150), "strip_height_cm": selected.get("strip_height_cm", 40), "beam_width_cm": selected.get("beam_width_cm", 50), "beam_height_cm": selected.get("beam_height_cm", 60), "needs_load_model": True, "interface_status": "conceptuele koppeling"}

    def build_risks(self, project: Dict[str, Any], grid: Dict[str, Any], foundation: Dict[str, Any]):
        risks = []
        if project.get("location") == "Locatie nog te bepalen": risks.append({"risk": "Locatie ontbreekt", "severity": "middel", "impact": "Windbelasting en lokale eisen kunnen nog niet definitief worden bepaald.", "repair": "Vul locatie/adres in project_intake_input.txt."})
        if grid.get("needs_real_geometry"): risks.append({"risk": "Werkelijke geometrie ontbreekt", "severity": "hoog", "impact": "Constructieve afmetingen, overspanningen en belastingen blijven indicatief.", "repair": "Voeg plattegrond, doorsnede of CAD/BIM-bestand toe."})
        if not foundation: risks.append({"risk": "Foundation output ontbreekt", "severity": "hoog", "impact": "Belastingafdracht naar fundering kan niet gekoppeld worden.", "repair": "Run Foundation Engine v7.3 opnieuw."})
        risks.append({"risk": "Belastingen nog niet projectspecifiek", "severity": "middel", "impact": "OpenSees/CalculiX model kan nog niet definitief worden gegenereerd.", "repair": "Laat toekomstige load engine echte belastingwaarden bepalen."})
        return risks

    def build_markdown(self, structural: Dict[str, Any]) -> str:
        p = structural["project"]; s = structural["selected_system"]
        lines = ["# Project Structural Model v7.4", "", f"Project: {p.get('project_name','')}", f"Locatie: {p.get('location','')}", "", "## Constructief systeem", f"- Type: {s.get('system_type','')}", f"- Status: {s.get('status','')}", f"- Reden: {s.get('reason','')}", "", "## Elementen"]
        for e in structural["elements"]: lines.append(f"- {e.get('element_id','')}: {e.get('type','')} - {e.get('material','')}")
        lines += ["", "## Belastingen"]
        for l in structural["load_assumptions"]: lines.append(f"- {l.get('load_case','')}: {l.get('name','')} - {l.get('status','')}")
        lines += ["", "## Risico's"]
        for r in structural["risks"]: lines.append(f"- {r.get('risk','')}: {r.get('impact','')}")
        return "\n".join(lines) + "\n"

    def build_dashboard(self, result: Dict[str, Any], structural: Dict[str, Any]) -> str:
        p = structural["project"]; s = structural["selected_system"]
        erows = "".join(f"<tr><td>{self.esc(e.get('element_id',''))}</td><td>{self.esc(e.get('type',''))}</td><td>{self.esc(e.get('material',''))}</td><td>{self.esc(e.get('function',''))}</td><td>{self.esc(e.get('status',''))}</td></tr>" for e in structural["elements"])
        lrows = "".join(f"<tr><td>{self.esc(l.get('load_case',''))}</td><td>{self.esc(l.get('name',''))}</td><td>{self.esc(l.get('type',''))}</td><td>{self.esc(l.get('preliminary_value',''))}</td><td>{self.esc(l.get('status',''))}</td></tr>" for l in structural["load_assumptions"])
        crows = "".join(f"<tr><td>{self.esc(c.get('check',''))}</td><td>{self.esc(c.get('status',''))}</td><td>{self.esc(c.get('input_needed',''))}</td></tr>" for c in structural["required_checks"])
        rrows = "".join(f"<tr><td>{self.esc(r.get('risk',''))}</td><td>{self.esc(r.get('severity',''))}</td><td>{self.esc(r.get('impact',''))}</td><td>{self.esc(r.get('repair',''))}</td></tr>" for r in structural["risks"])
        return f'''<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Project Phoenix Structural v7.4</title><style>body{{margin:0;font-family:Arial,sans-serif;background:#0f172a;color:#e5e7eb}}main{{max-width:1240px;margin:0 auto;padding:32px}}section{{background:#111827;border:1px solid #334155;border-radius:14px;padding:20px;margin-bottom:18px}}h1,h2{{color:#f8fafc}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #334155;padding:10px;text-align:left;vertical-align:top}}th{{background:#1e293b}}code{{color:#bfdbfe}}</style></head><body><main><section><h1>Project Phoenix Structural Engine v7.4</h1><p>Status: <strong>{self.esc(result.get("status",""))}</strong></p><p>Voorlopig constructief model op basis van projectcontext, geotechniek en fundering.</p></section><section><h2>Project</h2><p><strong>Naam:</strong> {self.esc(p.get("project_name",""))}</p><p><strong>Locatie:</strong> {self.esc(p.get("location",""))}</p><p><strong>Type:</strong> {self.esc(p.get("project_type",""))}</p></section><section><h2>Constructief systeem</h2><p><strong>Type:</strong> {self.esc(s.get("system_type",""))}</p><p><strong>Status:</strong> {self.esc(s.get("status",""))}</p><p><strong>Reden:</strong> {self.esc(s.get("reason",""))}</p><p><strong>Stabiliteit:</strong> {self.esc(s.get("stability_concept",""))}</p></section><section><h2>Elementen</h2><table><tr><th>ID</th><th>Type</th><th>Materiaal</th><th>Functie</th><th>Status</th></tr>{erows}</table></section><section><h2>Voorlopige belastingen</h2><table><tr><th>Load case</th><th>Naam</th><th>Type</th><th>Waarde</th><th>Status</th></tr>{lrows}</table></section><section><h2>Vereiste controles</h2><table><tr><th>Controle</th><th>Status</th><th>Benodigde input</th></tr>{crows}</table></section><section><h2>Risico's</h2><table><tr><th>Risico</th><th>Ernst</th><th>Impact</th><th>Herstel</th></tr>{rrows}</table></section><section><h2>Bestanden</h2><p><code>{self.esc(result.get("structural_json_path",""))}</code></p><p><code>{self.esc(result.get("structural_summary_path",""))}</code></p></section></main></body></html>'''

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists(): return {}
        try: return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            try: return json.loads(path.read_text(encoding="utf-8"))
            except Exception: return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8-sig")

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)

ConstructieEngine = StructuralEngine
BAOEESStructuralEngine = StructuralEngine

def main() -> None:
    result = StructuralEngine().run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))

if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.4
python baoees\project_analyzer\project_intake_engine.py || goto error
python baoees\project_analyzer\brewster_knowledge_migration_engine.py || goto error
python baoees\project_analyzer\deep_knowledge_harvest_engine.py || goto error
python baoees\project_analyzer\module_registry_engine.py || goto error
python baoees\project_analyzer\aaie_bib_assumption_loader.py || goto error
python baoees\project_analyzer\project_context_builder_engine.py || goto error
python baoees\project_analyzer\geotechniek_engine.py || goto error
python baoees\project_analyzer\foundation_engine.py || goto error
python baoees\project_analyzer\structural_engine.py || goto error
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
echo PROJECT PHOENIX v7.4 START PROJECTANALYSE KLAAR
if exist "outputs\projects\project_structural_dashboard_v7_4.html" (start "" "outputs\projects\project_structural_dashboard_v7_4.html")
git status
pause
exit /b 0
:error
echo FOUT: START PROJECTANALYSE v7.4 is gestopt.
git status
pause
exit /b 1
'@

$Ps1Content = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.4" -ForegroundColor Cyan
$Steps = @(
    "baoees\project_analyzer\project_intake_engine.py",
    "baoees\project_analyzer\brewster_knowledge_migration_engine.py",
    "baoees\project_analyzer\deep_knowledge_harvest_engine.py",
    "baoees\project_analyzer\module_registry_engine.py",
    "baoees\project_analyzer\aaie_bib_assumption_loader.py",
    "baoees\project_analyzer\project_context_builder_engine.py",
    "baoees\project_analyzer\geotechniek_engine.py",
    "baoees\project_analyzer\foundation_engine.py",
    "baoees\project_analyzer\structural_engine.py",
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
    if ($LASTEXITCODE -ne 0) { throw "Stap mislukt: $Step" }
    $Index++
}
Write-Host "PROJECT PHOENIX v7.4 START PROJECTANALYSE KLAAR" -ForegroundColor Green
$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_structural_dashboard_v7_4.html"
if (Test-Path $Dashboard) { Start-Process $Dashboard }
git status
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $BatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $VersionedBatPath -Value $BatContent -Encoding ASCII
Set-Content -Path $Ps1Path -Value $Ps1Content -Encoding UTF8
Set-Content -Path $VersionedPs1Path -Value $Ps1Content -Encoding UTF8

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Structural Connector"
    engine_version = "v7.4"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    structural_engine = "$EnginePath"
    purpose = "Voegt constructief conceptmodel, elementen, belastingen, load paths en CAD-output basis toe aan START_PROJECTANALYSE."
}
$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green
Write-Host "Syntaxcontrole structural engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\structural_engine.py
Write-Host "Test START_PROJECTANALYSE_v7_4.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v7_4.ps1
Write-Host "Git status..." -ForegroundColor Cyan
git status
Write-Host "PROJECT PHOENIX v7.4 UPDATE KLAAR" -ForegroundColor Green
