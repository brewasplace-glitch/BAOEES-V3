# PROJECT PHOENIX v7.2 UPDATE
# Geotechniek Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v7.2 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\geotechniek_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_2.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_2.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_2_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v7_2_$Timestamp" -Force
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


class GeotechniekEngine:
    ENGINE_NAME = "Project Phoenix Geotechniek Engine"
    ENGINE_VERSION = "v7.2"

    def __init__(self) -> None:
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.context_path = self.out / "project_context_v7_1.json"
        self.intake_path = self.out / "project_intake_v7_0.json"
        self.aaie_path = self.out / "aaie_bib_assumptions.json"

        self.geo_json_path = self.out / "project_geotechniek_v7_2.json"
        self.geo_summary_path = self.out / "project_geotechniek_summary_v7_2.md"
        self.geo_log_path = self.out / "project_geotechniek_log_v7_2.json"
        self.geo_dashboard_path = self.out / "project_geotechniek_dashboard_v7_2.html"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        context = self.read_json(self.context_path)
        intake = self.read_json(self.intake_path)
        aaie = self.read_json(self.aaie_path)

        geotechniek = self.build_geotechniek(context, intake, aaie)

        self.write_json(self.geo_json_path, geotechniek)
        self.write_text(self.geo_summary_path, self.build_markdown_summary(geotechniek))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.out),
            "project_context_path": str(self.context_path),
            "geotechniek_json_path": str(self.geo_json_path),
            "geotechniek_summary_path": str(self.geo_summary_path),
            "geotechniek_log_path": str(self.geo_log_path),
            "geotechniek_dashboard_path": str(self.geo_dashboard_path),
            "source_status": {
                "project_context": "GELEZEN" if context else "ONTBREEKT",
                "project_intake": "GELEZEN" if intake else "ONTBREEKT",
                "aaie": "GELEZEN" if aaie else "ONTBREEKT",
            },
            "project_name": geotechniek["project"]["project_name"],
            "location": geotechniek["project"]["location"],
            "groundwater_level": geotechniek["groundwater"]["default_level"],
            "foundation_advice": geotechniek["foundation_advice"]["primary_advice"],
            "risk_count": len(geotechniek["risks"]),
            "assumption_count": len(geotechniek["assumptions"]),
            "next_steps": [
                "Controleer project_geotechniek_dashboard_v7_2.html.",
                "Controleer project_geotechniek_v7_2.json.",
                "Gebruik de geotechniek-output als basis voor v7.3 Fundering Engine.",
                "Vul projectspecifieke bodemgegevens later aan via project_intake_input.txt of project_context.",
            ],
        }

        self.write_json(self.geo_log_path, result)
        self.write_text(self.geo_dashboard_path, self.build_dashboard(result, geotechniek))

        return result

    def build_geotechniek(
        self,
        context: Dict[str, Any],
        intake: Dict[str, Any],
        aaie: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = self.resolve_project(context, intake)
        text = self.collect_context_text(context, intake, aaie)

        soil_profile = self.infer_soil_profile(text, project)
        groundwater = self.build_groundwater(text)
        foundation_advice = self.build_foundation_advice(text, soil_profile, groundwater)
        risks = self.build_risks(project, soil_profile, groundwater)
        assumptions = self.build_assumptions(project, soil_profile, groundwater)

        return {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "input_policy": {
                "option_1": "Grondwaterstand en geo-informatie automatisch genereren via kaartuitsnede / Google Maps / satellietfoto.",
                "option_2": "Handmatige invoer van bodemlagen, grondwaterstand en sondering.",
                "default_mode": "automatisch_voorlopig_met_aannames",
                "manual_override_allowed": True,
            },
            "groundwater": groundwater,
            "soil_profile": soil_profile,
            "foundation_advice": foundation_advice,
            "risks": risks,
            "assumptions": assumptions,
            "required_follow_up_data": [
                "Locatiekaart of kaartuitsnede",
                "Sondering of bodemonderzoek indien beschikbaar",
                "Peil P = 0,00 m bevestigen",
                "Gewenst funderingsniveau",
                "Belastingen uit constructiemodel",
            ],
            "outputs_for_next_engine": {
                "next_engine": "Foundation Engine v7.3",
                "recommended_foundation_type": foundation_advice["primary_advice"],
                "groundwater_level": groundwater["default_level"],
                "soil_profile_source": soil_profile["source"],
            },
        }

    def resolve_project(
        self,
        context: Dict[str, Any],
        intake: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = {}

        if isinstance(context.get("project"), dict):
            project.update(context["project"])

        if isinstance(intake.get("project"), dict):
            for key, value in intake["project"].items():
                if value and not project.get(key):
                    project[key] = value

        defaults = {
            "project_name": "Nieuw Project Phoenix project",
            "location": "Locatie nog te bepalen",
            "project_type": "algemeen bouwkundig / civiel project",
            "description": "Geotechnische projectanalyse op basis van beschikbare context.",
        }

        for key, value in defaults.items():
            if not str(project.get(key, "")).strip():
                project[key] = value

        return project

    def collect_context_text(
        self,
        context: Dict[str, Any],
        intake: Dict[str, Any],
        aaie: Dict[str, Any],
    ) -> str:
        parts = [
            json.dumps(context, ensure_ascii=False, default=str),
            json.dumps(intake, ensure_ascii=False, default=str),
            json.dumps(aaie, ensure_ascii=False, default=str),
        ]

        return " ".join(parts).lower()

    def infer_soil_profile(
        self,
        text: str,
        project: Dict[str, Any],
    ) -> Dict[str, Any]:
        location = str(project.get("location", "")).lower()
        project_name = str(project.get("project_name", "")).lower()

        if "plutostraat" in text or "paramaribo" in location or "paramaribo" in project_name:
            layers = [
                {
                    "layer": 1,
                    "from_m": 0.00,
                    "to_m": -0.50,
                    "thickness_m": 0.50,
                    "soil_type": "zandopvulling",
                    "classification": "matig draagkrachtig",
                    "source": "Brewster Wizard kennis / Plutostraat uitgangspunt",
                },
                {
                    "layer": 2,
                    "from_m": -0.50,
                    "to_m": -1.00,
                    "thickness_m": 0.50,
                    "soil_type": "vaste klei",
                    "classification": "redelijk draagkrachtig",
                    "source": "Brewster Wizard kennis / Plutostraat uitgangspunt",
                },
                {
                    "layer": 3,
                    "from_m": -1.00,
                    "to_m": -2.20,
                    "thickness_m": 1.20,
                    "soil_type": "slappe klei",
                    "classification": "zettingsgevoelig",
                    "source": "Brewster Wizard kennis / Plutostraat uitgangspunt",
                },
                {
                    "layer": 4,
                    "from_m": -2.20,
                    "to_m": -3.70,
                    "thickness_m": 1.50,
                    "soil_type": "zand",
                    "classification": "draagkrachtiger laag",
                    "source": "Brewster Wizard kennis / Plutostraat uitgangspunt",
                },
            ]

            source = "projectspecifiek_uit_brewster_kennis"
            reliability = "middel"

        else:
            layers = [
                {
                    "layer": 1,
                    "from_m": 0.00,
                    "to_m": -0.50,
                    "thickness_m": 0.50,
                    "soil_type": "bovenlaag / ophooglaag",
                    "classification": "onbekend",
                    "source": "voorlopige standaardaanname",
                },
                {
                    "layer": 2,
                    "from_m": -0.50,
                    "to_m": -2.00,
                    "thickness_m": 1.50,
                    "soil_type": "natuurlijke ondergrond",
                    "classification": "nog te verifiëren",
                    "source": "voorlopige standaardaanname",
                },
            ]

            source = "voorlopige_generieke_aanname"
            reliability = "basis"

        return {
            "status": "VOORLOPIG",
            "source": source,
            "reliability": reliability,
            "layers": layers,
            "needs_soil_investigation": True,
            "manual_input_possible": True,
        }

    def build_groundwater(self, text: str) -> Dict[str, Any]:
        return {
            "status": "VOORLOPIG",
            "default_level": "P = -0,50 m",
            "value_m_relative_to_p": -0.50,
            "source": "Brewster Engineering Wizard standaardkeuze",
            "reliability": "basis",
            "needs_verification": True,
            "automatic_generation_supported": True,
            "manual_override_supported": True,
        }

    def build_foundation_advice(
        self,
        text: str,
        soil_profile: Dict[str, Any],
        groundwater: Dict[str, Any],
    ) -> Dict[str, Any]:
        has_soft_clay = any(
            "slappe klei" in str(layer.get("soil_type", "")).lower()
            for layer in soil_profile.get("layers", [])
        )

        if has_soft_clay:
            primary = "strokenfundering voorlopig mogelijk, maar zettingscontrole verplicht; palenvariant onderzoeken"
            variants = [
                "strokenfundering met verbrede strook",
                "palenfundering als risico-/zettingsvariant",
                "grondverbetering indien economisch haalbaar",
            ]
            risk_level = "middel_hoog"
        else:
            primary = "strokenfundering voorlopig uitgangspunt; bodemgegevens verifiëren"
            variants = [
                "strokenfundering",
                "poeren met koppelbalken",
                "palenvariant alleen bij onvoldoende draagkracht",
            ]
            risk_level = "middel"

        return {
            "status": "VOORLOPIG",
            "primary_advice": primary,
            "variants_to_check": variants,
            "standard_brewster_rule": {
                "strip_width_cm": 150,
                "strip_height_cm": 40,
                "foundation_beam_width_cm": 50,
                "foundation_beam_height_cm": 60,
                "note": "Standaardregel; projectspecifiek kan 200 cm strookbreedte nodig zijn.",
            },
            "risk_level": risk_level,
            "requires_structural_loads": True,
            "requires_settlement_check": True,
        }

    def build_risks(
        self,
        project: Dict[str, Any],
        soil_profile: Dict[str, Any],
        groundwater: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        risks = []

        if project.get("location") == "Locatie nog te bepalen":
            risks.append(
                {
                    "risk": "Locatie ontbreekt",
                    "severity": "hoog",
                    "impact": "Automatische geo-informatie kan nog niet locatiespecifiek worden bepaald.",
                    "repair": "Vul project_intake_input.txt met locatie of adres.",
                }
            )

        if soil_profile.get("reliability") == "basis":
            risks.append(
                {
                    "risk": "Bodemopbouw is voorlopig",
                    "severity": "middel",
                    "impact": "Funderingsadvies blijft indicatief.",
                    "repair": "Voeg sondering of bodemonderzoek toe.",
                }
            )

        if groundwater.get("needs_verification"):
            risks.append(
                {
                    "risk": "Grondwaterstand is standaardaanname",
                    "severity": "middel",
                    "impact": "Ontwatering, uitvoerbaarheid en funderingsniveau moeten worden getoetst.",
                    "repair": "Verifieer grondwaterstand projectspecifiek.",
                }
            )

        return risks

    def build_assumptions(
        self,
        project: Dict[str, Any],
        soil_profile: Dict[str, Any],
        groundwater: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "field": "groundwater_level",
                "value": groundwater["default_level"],
                "source": groundwater["source"],
                "confidence": groundwater["reliability"],
                "reason": "Standaard Brewster/BAOEES uitgangspunt totdat projectspecifieke data beschikbaar is.",
            },
            {
                "field": "soil_profile",
                "value": soil_profile["source"],
                "source": "Geotechniek Engine v7.2",
                "confidence": soil_profile["reliability"],
                "reason": "Voorlopige bodemopbouw gekozen op basis van context en beschikbare kennis.",
            },
        ]

    def build_markdown_summary(self, geotechniek: Dict[str, Any]) -> str:
        project = geotechniek["project"]
        lines = []
        lines.append("# Project Geotechniek v7.2")
        lines.append("")
        lines.append(f"Project: {project.get('project_name', '')}")
        lines.append(f"Locatie: {project.get('location', '')}")
        lines.append("")
        lines.append("## Grondwater")
        lines.append(f"- {geotechniek['groundwater']['default_level']}")
        lines.append("")
        lines.append("## Bodemlagen")
        lines.append("")
        for layer in geotechniek["soil_profile"]["layers"]:
            lines.append(
                f"- Laag {layer['layer']}: {layer['from_m']} tot {layer['to_m']} m — {layer['soil_type']} ({layer['classification']})"
            )
        lines.append("")
        lines.append("## Funderingsadvies")
        lines.append(geotechniek["foundation_advice"]["primary_advice"])
        lines.append("")
        return "\n".join(lines)

    def build_dashboard(
        self,
        result: Dict[str, Any],
        geotechniek: Dict[str, Any],
    ) -> str:
        project = geotechniek["project"]

        layer_rows = "".join(
            "<tr>"
            f"<td>{self.esc(layer.get('layer', ''))}</td>"
            f"<td>{self.esc(layer.get('from_m', ''))}</td>"
            f"<td>{self.esc(layer.get('to_m', ''))}</td>"
            f"<td>{self.esc(layer.get('soil_type', ''))}</td>"
            f"<td>{self.esc(layer.get('classification', ''))}</td>"
            f"<td>{self.esc(layer.get('source', ''))}</td>"
            "</tr>"
            for layer in geotechniek["soil_profile"]["layers"]
        )

        risk_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('risk', ''))}</td>"
            f"<td>{self.esc(item.get('severity', ''))}</td>"
            f"<td>{self.esc(item.get('impact', ''))}</td>"
            f"<td>{self.esc(item.get('repair', ''))}</td>"
            "</tr>"
            for item in geotechniek["risks"]
        )

        if not risk_rows:
            risk_rows = "<tr><td>OK</td><td>laag</td><td>Geen hoofdpunten.</td><td>Geen actie.</td></tr>"

        variant_rows = "".join(
            f"<tr><td>{self.esc(item)}</td></tr>"
            for item in geotechniek["foundation_advice"]["variants_to_check"]
        )

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Geotechniek v7.2</title>
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
<h1>Project Phoenix Geotechniek v7.2</h1>
<p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
<p>Voorlopige geotechnische analyse op basis van projectcontext, BIB en Brewster-standaardregels.</p>
</section>

<section>
<h2>Project</h2>
<p><strong>Naam:</strong> {self.esc(project.get("project_name", ""))}</p>
<p><strong>Locatie:</strong> {self.esc(project.get("location", ""))}</p>
<p><strong>Type:</strong> {self.esc(project.get("project_type", ""))}</p>
</section>

<section>
<h2>Grondwater</h2>
<p><strong>Standaard:</strong> {self.esc(geotechniek["groundwater"]["default_level"])}</p>
<p><strong>Bron:</strong> {self.esc(geotechniek["groundwater"]["source"])}</p>
</section>

<section>
<h2>Bodemlagen</h2>
<table>
<tr><th>Laag</th><th>Van</th><th>Tot</th><th>Grondsoort</th><th>Classificatie</th><th>Bron</th></tr>
{layer_rows}
</table>
</section>

<section>
<h2>Funderingsadvies</h2>
<p>{self.esc(geotechniek["foundation_advice"]["primary_advice"])}</p>
<table>{variant_rows}</table>
</section>

<section>
<h2>Risico's</h2>
<table>
<tr><th>Risico</th><th>Ernst</th><th>Impact</th><th>Herstel</th></tr>
{risk_rows}
</table>
</section>

<section>
<h2>Bestanden</h2>
<p><code>{self.esc(result.get("geotechniek_json_path", ""))}</code></p>
<p><code>{self.esc(result.get("geotechniek_summary_path", ""))}</code></p>
</section>
</main>
</body>
</html>
"""

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


GeoEngine = GeotechniekEngine
GeotechnicalEngine = GeotechniekEngine
BAOEESGeotechniekEngine = GeotechniekEngine


def main() -> None:
    engine = GeotechniekEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.2

python baoees\project_analyzer\project_intake_engine.py || goto error
python baoees\project_analyzer\brewster_knowledge_migration_engine.py || goto error
python baoees\project_analyzer\deep_knowledge_harvest_engine.py || goto error
python baoees\project_analyzer\module_registry_engine.py || goto error
python baoees\project_analyzer\aaie_bib_assumption_loader.py || goto error
python baoees\project_analyzer\project_context_builder_engine.py || goto error
python baoees\project_analyzer\geotechniek_engine.py || goto error
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

echo PROJECT PHOENIX v7.2 START PROJECTANALYSE KLAAR

if exist "outputs\projects\project_geotechniek_dashboard_v7_2.html" (
    start "" "outputs\projects\project_geotechniek_dashboard_v7_2.html"
)

git status
pause
exit /b 0

:error
echo FOUT: START PROJECTANALYSE v7.2 is gestopt.
git status
pause
exit /b 1
'@

$Ps1Content = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.2" -ForegroundColor Cyan

$Steps = @(
    "baoees\project_analyzer\project_intake_engine.py",
    "baoees\project_analyzer\brewster_knowledge_migration_engine.py",
    "baoees\project_analyzer\deep_knowledge_harvest_engine.py",
    "baoees\project_analyzer\module_registry_engine.py",
    "baoees\project_analyzer\aaie_bib_assumption_loader.py",
    "baoees\project_analyzer\project_context_builder_engine.py",
    "baoees\project_analyzer\geotechniek_engine.py",
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

Write-Host "PROJECT PHOENIX v7.2 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_geotechniek_dashboard_v7_2.html"
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
    engine = "Project Phoenix Geotechniek Connector"
    engine_version = "v7.2"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    geotechniek_engine = "$EnginePath"
    purpose = "Voegt geotechnische voorlopige analyse, grondwaterstand en funderingsadvies toe aan START_PROJECTANALYSE."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole geotechniek engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\geotechniek_engine.py

Write-Host "Test START_PROJECTANALYSE_v7_2.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v7_2.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v7.2 UPDATE KLAAR" -ForegroundColor Green
