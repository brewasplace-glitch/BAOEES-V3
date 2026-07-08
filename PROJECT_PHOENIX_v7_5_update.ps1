# PROJECT PHOENIX v7.5 UPDATE
# CAD Drawing Export Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v7.5 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot "baoees"))) {
    throw "Dit script moet vanuit C:\BREWSTER-ENGINEERING-WIZARD worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "baoees\project_analyzer\cad_drawing_export_engine.py"
$BatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE.bat"
$Ps1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE.ps1"
$VersionedBatPath = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_5.bat"
$VersionedPs1Path = Join-Path $ProjectRoot "START_PROJECTANALYSE_v7_5.ps1"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v7_5_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $BatPath, $Ps1Path)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v7_5_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import html
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class CADDrawingExportEngine:
    ENGINE_NAME = "Project Phoenix CAD Drawing Export Engine"
    ENGINE_VERSION = "v7.5"

    def __init__(self) -> None:
        self.out = PROJECT_ROOT / "outputs" / "projects"
        self.drawings_out = self.out / "drawings" / "v7_5"

        self.context_path = self.out / "project_context_v7_1.json"
        self.geo_path = self.out / "project_geotechniek_v7_2.json"
        self.foundation_path = self.out / "project_foundation_design_v7_3.json"
        self.structural_path = self.out / "project_structural_model_v7_4.json"

        self.export_plan_path = self.out / "project_cad_export_plan_v7_5.json"
        self.export_summary_path = self.out / "project_cad_export_summary_v7_5.md"
        self.export_log_path = self.out / "project_cad_export_log_v7_5.json"
        self.export_dashboard_path = self.out / "project_cad_export_dashboard_v7_5.html"

        self.dxf_situation_path = self.drawings_out / "01_situatie_concept_v7_5.dxf"
        self.dxf_foundation_path = self.drawings_out / "02_fundering_concept_v7_5.dxf"
        self.dxf_structural_path = self.drawings_out / "03_constructie_concept_v7_5.dxf"
        self.dxf_section_path = self.drawings_out / "04_doorsnede_concept_v7_5.dxf"

    def run(self) -> Dict[str, Any]:
        self.out.mkdir(parents=True, exist_ok=True)
        self.drawings_out.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat(timespec="seconds")

        context = self.read_json(self.context_path)
        geotechniek = self.read_json(self.geo_path)
        foundation = self.read_json(self.foundation_path)
        structural = self.read_json(self.structural_path)

        export_plan = self.build_export_plan(context, geotechniek, foundation, structural)

        self.write_dxf_files(export_plan)
        self.write_json(self.export_plan_path, export_plan)
        self.write_text(self.export_summary_path, self.build_markdown_summary(export_plan))

        result = {
            "status": "OPGESLAGEN",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(PROJECT_ROOT),
            "project_output_root": str(self.out),
            "drawings_output_root": str(self.drawings_out),
            "source_status": {
                "project_context": "GELEZEN" if context else "ONTBREEKT",
                "geotechniek": "GELEZEN" if geotechniek else "ONTBREEKT",
                "foundation": "GELEZEN" if foundation else "ONTBREEKT",
                "structural": "GELEZEN" if structural else "ONTBREEKT",
            },
            "export_plan_path": str(self.export_plan_path),
            "export_summary_path": str(self.export_summary_path),
            "export_log_path": str(self.export_log_path),
            "export_dashboard_path": str(self.export_dashboard_path),
            "drawing_files": export_plan["drawing_files"],
            "project_name": export_plan["project"]["project_name"],
            "drawing_count": len(export_plan["drawing_files"]),
            "layer_count": len(export_plan["cad_layers"]),
            "risk_count": len(export_plan["risks"]),
            "next_steps": [
                "Controleer project_cad_export_dashboard_v7_5.html.",
                "Controleer de DXF-bestanden in outputs/projects/drawings/v7_5.",
                "Gebruik deze CAD-output als basis voor v7.6 Report Drawing Integration Engine.",
                "Vervang conceptgeometrie later door echte SKP/DWG/DXF/BIM-geometrie.",
            ],
        }

        self.write_json(self.export_log_path, result)
        self.write_text(self.export_dashboard_path, self.build_dashboard(result, export_plan))

        return result

    def build_export_plan(
        self,
        context: Dict[str, Any],
        geotechniek: Dict[str, Any],
        foundation: Dict[str, Any],
        structural: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = self.resolve_project(context, structural, foundation)
        geometry = self.resolve_geometry(structural, foundation)
        layers = self.build_cad_layers()
        drawing_files = self.build_drawing_file_list()
        sheets = self.build_sheets(project, geometry)
        risks = self.build_risks(project, geometry, structural)
        assumptions = self.build_assumptions(geometry)

        return {
            "status": "VOORLOPIG_CONCEPT",
            "engine": self.ENGINE_NAME,
            "engine_version": self.ENGINE_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "geometry_basis": geometry,
            "cad_layers": layers,
            "sheets": sheets,
            "drawing_files": drawing_files,
            "export_formats": {
                "created_now": ["DXF"],
                "planned_next": ["DWG", "SKP", "IFC", "PDF"],
                "note": "DXF wordt nu als open tekstformaat gegenereerd; DWG/SKP/IFC/PDF volgen via latere koppelingen.",
            },
            "source_files": {
                "project_context": str(self.context_path),
                "geotechniek": str(self.geo_path),
                "foundation": str(self.foundation_path),
                "structural": str(self.structural_path),
            },
            "risks": risks,
            "assumptions": assumptions,
            "outputs_for_next_engine": {
                "next_engine": "Report Drawing Integration Engine v7.6",
                "drawing_folder": str(self.drawings_out),
                "drawing_files": drawing_files,
                "report_sections_to_update": [
                    "Situatie",
                    "Funderingsconcept",
                    "Constructief concept",
                    "Doorsnede concept",
                ],
            },
            "not_for_execution_note": "Deze tekeningen zijn concept-DXF's. Definitieve bestek-/uitvoeringstekeningen vereisen echte maatvoering, CAD/BIM-geometrie, berekening en projectcontrole.",
        }

    def resolve_project(
        self,
        context: Dict[str, Any],
        structural: Dict[str, Any],
        foundation: Dict[str, Any],
    ) -> Dict[str, Any]:
        project = {}

        for source in [context, structural, foundation]:
            if isinstance(source.get("project"), dict):
                for key, value in source["project"].items():
                    if value and not project.get(key):
                        project[key] = value

        defaults = {
            "project_name": "Nieuw Project Phoenix project",
            "location": "Locatie nog te bepalen",
            "project_type": "algemeen bouwkundig / civiel project",
            "description": "Concept CAD-export op basis van projectcontext, fundering en constructie.",
        }

        for key, value in defaults.items():
            if not str(project.get(key, "")).strip():
                project[key] = value

        return project

    def resolve_geometry(
        self,
        structural: Dict[str, Any],
        foundation: Dict[str, Any],
    ) -> Dict[str, Any]:
        grid = structural.get("preliminary_grid", {}) if isinstance(structural, dict) else {}
        foundation_interface = structural.get("foundation_interface", {}) if isinstance(structural, dict) else {}

        x_spacing = float(grid.get("axis_spacing_m", {}).get("x_default", 5.0))
        y_spacing = float(grid.get("axis_spacing_m", {}).get("y_default", 5.0))
        x_bays = int(grid.get("assumed_bays", {}).get("x_direction", 2))
        y_bays = int(grid.get("assumed_bays", {}).get("y_direction", 2))

        width = max(1, x_bays) * x_spacing
        depth = max(1, y_bays) * y_spacing

        strip_width = float(foundation_interface.get("strip_width_cm", 150)) / 100
        strip_height = float(foundation_interface.get("strip_height_cm", 40)) / 100
        beam_width = float(foundation_interface.get("beam_width_cm", 50)) / 100
        beam_height = float(foundation_interface.get("beam_height_cm", 60)) / 100

        return {
            "status": "CONCEPT",
            "source": grid.get("source", "structural preliminary grid"),
            "width_m": round(width, 3),
            "depth_m": round(depth, 3),
            "axis_spacing_x_m": x_spacing,
            "axis_spacing_y_m": y_spacing,
            "x_bays": x_bays,
            "y_bays": y_bays,
            "strip_width_m": strip_width,
            "strip_height_m": strip_height,
            "beam_width_m": beam_width,
            "beam_height_m": beam_height,
            "foundation_level": foundation_interface.get("foundation_level", "P = -0,50 m voorlopig"),
            "needs_real_geometry": bool(grid.get("needs_real_geometry", True)),
        }

    def build_cad_layers(self) -> List[Dict[str, Any]]:
        return [
            {"name": "A-ASSEN", "description": "Constructieassen", "status": "created"},
            {"name": "A-MAATVOERING", "description": "Conceptmaatvoering", "status": "created"},
            {"name": "S-FUNDERING-STROOK", "description": "Strokenfundering", "status": "created"},
            {"name": "S-FUNDERING-BALK", "description": "Funderingsbalken", "status": "created"},
            {"name": "S-KOLOMMEN", "description": "Kolommen", "status": "created"},
            {"name": "S-BALKEN", "description": "Balken", "status": "created"},
            {"name": "S-DAK", "description": "Dakconstructie/spanten", "status": "created"},
            {"name": "T-TEKST", "description": "Teksten en labels", "status": "created"},
            {"name": "P-PROJECTKADER", "description": "Bladkader / projectinfo", "status": "created"},
        ]

    def build_drawing_file_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "sheet": "01",
                "name": "Situatie concept",
                "format": "DXF",
                "path": str(self.dxf_situation_path),
                "status": "created",
            },
            {
                "sheet": "02",
                "name": "Fundering concept",
                "format": "DXF",
                "path": str(self.dxf_foundation_path),
                "status": "created",
            },
            {
                "sheet": "03",
                "name": "Constructie concept",
                "format": "DXF",
                "path": str(self.dxf_structural_path),
                "status": "created",
            },
            {
                "sheet": "04",
                "name": "Doorsnede concept",
                "format": "DXF",
                "path": str(self.dxf_section_path),
                "status": "created",
            },
        ]

    def build_sheets(
        self,
        project: Dict[str, Any],
        geometry: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "sheet": "01",
                "title": "Situatie concept",
                "scale": "conceptueel / niet op definitieve schaal",
                "content": ["projectkader", "gebouwfootprint", "noordpijl", "projecttekst"],
            },
            {
                "sheet": "02",
                "title": "Funderingsconcept",
                "scale": "1:100 concept",
                "content": ["assen", "strokenfundering", "funderingsbalk", "maatvoering"],
            },
            {
                "sheet": "03",
                "title": "Constructieconcept",
                "scale": "1:100 concept",
                "content": ["assen", "kolommen", "balken", "dragende lijnen", "dakconstructie"],
            },
            {
                "sheet": "04",
                "title": "Doorsnede concept",
                "scale": "1:50 concept",
                "content": ["maaiveld", "grondwater P=-0,50", "fundering", "wand/kolom", "dak"],
            },
        ]

    def write_dxf_files(self, export_plan: Dict[str, Any]) -> None:
        project = export_plan["project"]
        geometry = export_plan["geometry_basis"]

        self.write_text(self.dxf_situation_path, self.build_situation_dxf(project, geometry))
        self.write_text(self.dxf_foundation_path, self.build_foundation_dxf(project, geometry))
        self.write_text(self.dxf_structural_path, self.build_structural_dxf(project, geometry))
        self.write_text(self.dxf_section_path, self.build_section_dxf(project, geometry))

    def build_situation_dxf(self, project: Dict[str, Any], geometry: Dict[str, Any]) -> str:
        width = geometry["width_m"]
        depth = geometry["depth_m"]
        margin = 4.0

        e = DXFBuilder()
        self.add_standard_layers(e)
        e.text(0, depth + 5, f"SITUATIE CONCEPT - {project.get('project_name', '')}", 0.35, "T-TEKST")
        e.text(0, depth + 4.2, f"Locatie: {project.get('location', '')}", 0.25, "T-TEKST")
        e.rect(-margin, -margin, width + margin, depth + margin, "P-PROJECTKADER")
        e.rect(0, 0, width, depth, "S-BALKEN")
        e.text(width + 1.0, depth / 2, "CONCEPT FOOTPRINT", 0.25, "T-TEKST")
        e.line(width + 2, depth + 1, width + 2, depth + 3, "A-ASSEN")
        e.line(width + 2, depth + 3, width + 1.6, depth + 2.4, "A-ASSEN")
        e.line(width + 2, depth + 3, width + 2.4, depth + 2.4, "A-ASSEN")
        e.text(width + 2.25, depth + 2.2, "N", 0.3, "T-TEKST")
        return e.render()

    def build_foundation_dxf(self, project: Dict[str, Any], geometry: Dict[str, Any]) -> str:
        width = geometry["width_m"]
        depth = geometry["depth_m"]
        strip = geometry["strip_width_m"]
        beam = geometry["beam_width_m"]

        e = DXFBuilder()
        self.add_standard_layers(e)
        e.text(0, depth + 3, f"FUNDERING CONCEPT - {project.get('project_name', '')}", 0.35, "T-TEKST")
        self.add_grid(e, geometry)
        e.rect(0, 0, width, depth, "S-FUNDERING-STROOK")
        e.rect(strip / 2, strip / 2, width - strip / 2, depth - strip / 2, "S-FUNDERING-STROOK")
        center_offset = strip / 2 - beam / 2
        e.rect(center_offset, center_offset, width - center_offset, depth - center_offset, "S-FUNDERING-BALK")
        e.text(0, -1.2, f"Strook concept: {geometry['strip_width_m']}m x {geometry['strip_height_m']}m", 0.25, "T-TEKST")
        e.text(0, -1.8, f"Funderingsbalk: {geometry['beam_width_m']}m x {geometry['beam_height_m']}m", 0.25, "T-TEKST")
        e.text(0, -2.4, f"Niveau: {geometry['foundation_level']}", 0.25, "T-TEKST")
        return e.render()

    def build_structural_dxf(self, project: Dict[str, Any], geometry: Dict[str, Any]) -> str:
        width = geometry["width_m"]
        depth = geometry["depth_m"]

        e = DXFBuilder()
        self.add_standard_layers(e)
        e.text(0, depth + 3, f"CONSTRUCTIE CONCEPT - {project.get('project_name', '')}", 0.35, "T-TEKST")
        self.add_grid(e, geometry)
        e.rect(0, 0, width, depth, "S-BALKEN")

        for ix in range(geometry["x_bays"] + 1):
            x = ix * geometry["axis_spacing_x_m"]
            for iy in range(geometry["y_bays"] + 1):
                y = iy * geometry["axis_spacing_y_m"]
                e.circle(x, y, 0.15, "S-KOLOMMEN")

        for iy in range(geometry["y_bays"] + 1):
            y = iy * geometry["axis_spacing_y_m"]
            e.line(0, y, width, y, "S-BALKEN")

        for ix in range(geometry["x_bays"] + 1):
            x = ix * geometry["axis_spacing_x_m"]
            e.line(x, 0, x, depth, "S-BALKEN")

        e.line(0, 0, width, depth, "S-DAK")
        e.line(0, depth, width, 0, "S-DAK")
        e.text(0, -1.2, "Concept: kolommen/balken/dakschoren; definitief na geometrie en berekening.", 0.22, "T-TEKST")
        return e.render()

    def build_section_dxf(self, project: Dict[str, Any], geometry: Dict[str, Any]) -> str:
        width = min(geometry["width_m"], 12.0)
        foundation_depth = -0.50
        strip_height = geometry["strip_height_m"]
        beam_height = geometry["beam_height_m"]

        e = DXFBuilder()
        self.add_standard_layers(e)
        e.text(0, 5.0, f"DOORSNEDE CONCEPT - {project.get('project_name', '')}", 0.35, "T-TEKST")

        e.line(0, 0, width, 0, "A-ASSEN")
        e.text(width + 0.4, 0, "P = 0,00 maaiveld", 0.22, "T-TEKST")
        e.line(0, -0.5, width, -0.5, "A-MAATVOERING")
        e.text(width + 0.4, -0.5, "grondwater P = -0,50 m", 0.22, "T-TEKST")

        e.rect(1.0, foundation_depth - strip_height, width - 1.0, foundation_depth, "S-FUNDERING-STROOK")
        beam_x1 = width / 2 - geometry["beam_width_m"] / 2
        beam_x2 = width / 2 + geometry["beam_width_m"] / 2
        e.rect(beam_x1, foundation_depth - beam_height, beam_x2, foundation_depth, "S-FUNDERING-BALK")

        e.line(width / 2, foundation_depth, width / 2, 3.2, "S-KOLOMMEN")
        e.line(1.0, 3.2, width - 1.0, 3.2, "S-DAK")
        e.line(1.0, 3.2, width / 2, 4.2, "S-DAK")
        e.line(width / 2, 4.2, width - 1.0, 3.2, "S-DAK")

        e.text(0, -1.6, "Conceptdoorsnede; hoogten/peilen definitief uit projectgegevens.", 0.22, "T-TEKST")
        return e.render()

    def add_grid(self, e: "DXFBuilder", geometry: Dict[str, Any]) -> None:
        width = geometry["width_m"]
        depth = geometry["depth_m"]
        for ix in range(geometry["x_bays"] + 1):
            x = ix * geometry["axis_spacing_x_m"]
            e.line(x, -0.6, x, depth + 0.6, "A-ASSEN")
            e.text(x - 0.08, -0.95, chr(65 + ix), 0.22, "T-TEKST")
        for iy in range(geometry["y_bays"] + 1):
            y = iy * geometry["axis_spacing_y_m"]
            e.line(-0.6, y, width + 0.6, y, "A-ASSEN")
            e.text(-1.0, y - 0.08, str(iy + 1), 0.22, "T-TEKST")

    def add_standard_layers(self, e: "DXFBuilder") -> None:
        for layer in self.build_cad_layers():
            e.layer(layer["name"])

    def build_risks(
        self,
        project: Dict[str, Any],
        geometry: Dict[str, Any],
        structural: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        risks = []

        if geometry.get("needs_real_geometry"):
            risks.append(
                {
                    "risk": "Conceptgeometrie gebruikt",
                    "severity": "hoog",
                    "impact": "DXF-tekeningen zijn nog niet definitief maatvast.",
                    "repair": "Lees echte SKP/DWG/DXF/BIM-geometrie in.",
                }
            )

        if project.get("location") == "Locatie nog te bepalen":
            risks.append(
                {
                    "risk": "Locatie ontbreekt",
                    "severity": "middel",
                    "impact": "Situatietekening kan nog niet kadastraal/kaartvast worden gemaakt.",
                    "repair": "Vul projectlocatie en kaartuitsnede in.",
                }
            )

        if not structural:
            risks.append(
                {
                    "risk": "Structural output ontbreekt",
                    "severity": "hoog",
                    "impact": "Constructietekening kan alleen generiek worden gemaakt.",
                    "repair": "Run Structural Engine v7.4 opnieuw.",
                }
            )

        return risks

    def build_assumptions(self, geometry: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "field": "geometry",
                "value": geometry["source"],
                "confidence": "basis",
                "source": self.ENGINE_NAME,
                "reason": "CAD/BIM-geometrie nog niet definitief beschikbaar.",
            },
            {
                "field": "export_format",
                "value": "DXF",
                "confidence": "hoog",
                "source": self.ENGINE_NAME,
                "reason": "DXF is open tekstformaat en kan zonder commerciële CAD-library worden gegenereerd.",
            },
        ]

    def build_markdown_summary(self, export_plan: Dict[str, Any]) -> str:
        project = export_plan["project"]
        geometry = export_plan["geometry_basis"]

        lines = [
            "# Project CAD Export Plan v7.5",
            "",
            f"Project: {project.get('project_name', '')}",
            f"Locatie: {project.get('location', '')}",
            "",
            "## Geometry basis",
            "",
            f"- Breedte: {geometry.get('width_m')} m",
            f"- Diepte: {geometry.get('depth_m')} m",
            f"- Bron: {geometry.get('source')}",
            "",
            "## DXF-bestanden",
            "",
        ]

        for item in export_plan["drawing_files"]:
            lines.append(f"- {item.get('sheet')}: {item.get('name')} — {item.get('path')}")

        lines.extend(["", "## Risico's", ""])

        for risk in export_plan["risks"]:
            lines.append(f"- {risk.get('risk', '')}: {risk.get('impact', '')}")

        lines.append("")
        return "\n".join(lines)

    def build_dashboard(self, result: Dict[str, Any], export_plan: Dict[str, Any]) -> str:
        project = export_plan["project"]
        geometry = export_plan["geometry_basis"]

        file_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('sheet', ''))}</td>"
            f"<td>{self.esc(item.get('name', ''))}</td>"
            f"<td>{self.esc(item.get('format', ''))}</td>"
            f"<td><code>{self.esc(item.get('path', ''))}</code></td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            "</tr>"
            for item in export_plan["drawing_files"]
        )

        layer_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('name', ''))}</td>"
            f"<td>{self.esc(item.get('description', ''))}</td>"
            f"<td>{self.esc(item.get('status', ''))}</td>"
            "</tr>"
            for item in export_plan["cad_layers"]
        )

        risk_rows = "".join(
            "<tr>"
            f"<td>{self.esc(item.get('risk', ''))}</td>"
            f"<td>{self.esc(item.get('severity', ''))}</td>"
            f"<td>{self.esc(item.get('impact', ''))}</td>"
            f"<td>{self.esc(item.get('repair', ''))}</td>"
            "</tr>"
            for item in export_plan["risks"]
        ) or "<tr><td>OK</td><td>laag</td><td>Geen hoofdpunten.</td><td>Geen actie.</td></tr>"

        return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix CAD Drawing Export v7.5</title>
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
<h1>Project Phoenix CAD Drawing Export Engine v7.5</h1>
<p>Status: <strong>{self.esc(result.get("status", ""))}</strong></p>
<p>Concept-DXF tekeningen zijn automatisch gegenereerd uit projectcontext, fundering en constructie.</p>
</section>

<section>
<h2>Project</h2>
<p><strong>Naam:</strong> {self.esc(project.get("project_name", ""))}</p>
<p><strong>Locatie:</strong> {self.esc(project.get("location", ""))}</p>
<p><strong>Type:</strong> {self.esc(project.get("project_type", ""))}</p>
</section>

<section>
<h2>Geometriebasis</h2>
<p><strong>Breedte:</strong> {self.esc(geometry.get("width_m", ""))} m</p>
<p><strong>Diepte:</strong> {self.esc(geometry.get("depth_m", ""))} m</p>
<p><strong>Bron:</strong> {self.esc(geometry.get("source", ""))}</p>
<p><strong>Werkelijke geometrie nodig:</strong> {self.esc(geometry.get("needs_real_geometry", ""))}</p>
</section>

<section>
<h2>Gegenereerde DXF-bestanden</h2>
<table>
<tr><th>Blad</th><th>Naam</th><th>Formaat</th><th>Pad</th><th>Status</th></tr>
{file_rows}
</table>
</section>

<section>
<h2>CAD-lagen</h2>
<table>
<tr><th>Laag</th><th>Omschrijving</th><th>Status</th></tr>
{layer_rows}
</table>
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
<p><code>{self.esc(result.get("export_plan_path", ""))}</code></p>
<p><code>{self.esc(result.get("export_summary_path", ""))}</code></p>
<p><code>{self.esc(result.get("drawings_output_root", ""))}</code></p>
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


class DXFBuilder:
    def __init__(self) -> None:
        self.layers: List[str] = []
        self.entities: List[str] = []

    def layer(self, name: str) -> None:
        if name not in self.layers:
            self.layers.append(name)

    def line(self, x1: float, y1: float, x2: float, y2: float, layer: str = "0") -> None:
        self.layer(layer)
        self.entities.extend([
            "0", "LINE", "8", layer,
            "10", self.n(x1), "20", self.n(y1), "30", "0",
            "11", self.n(x2), "21", self.n(y2), "31", "0",
        ])

    def rect(self, x1: float, y1: float, x2: float, y2: float, layer: str = "0") -> None:
        self.line(x1, y1, x2, y1, layer)
        self.line(x2, y1, x2, y2, layer)
        self.line(x2, y2, x1, y2, layer)
        self.line(x1, y2, x1, y1, layer)

    def circle(self, x: float, y: float, r: float, layer: str = "0") -> None:
        self.layer(layer)
        self.entities.extend([
            "0", "CIRCLE", "8", layer,
            "10", self.n(x), "20", self.n(y), "30", "0",
            "40", self.n(r),
        ])

    def text(self, x: float, y: float, text: str, height: float = 0.25, layer: str = "0") -> None:
        self.layer(layer)
        clean = str(text).replace("\n", " ")[:240]
        self.entities.extend([
            "0", "TEXT", "8", layer,
            "10", self.n(x), "20", self.n(y), "30", "0",
            "40", self.n(height),
            "1", clean,
        ])

    def render(self) -> str:
        parts: List[str] = []
        parts.extend(["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC"])
        parts.extend(["0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(self.layers))])
        for layer in self.layers:
            parts.extend(["0", "LAYER", "2", layer, "70", "0", "62", "7", "6", "CONTINUOUS"])
        parts.extend(["0", "ENDTAB", "0", "ENDSEC"])
        parts.extend(["0", "SECTION", "2", "ENTITIES"])
        parts.extend(self.entities)
        parts.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(parts) + "\n"

    def n(self, value: Any) -> str:
        try:
            return f"{float(value):.4f}"
        except Exception:
            return "0.0000"


CADExportEngine = CADDrawingExportEngine
DrawingExportEngine = CADDrawingExportEngine
BAOEESCADDrawingExportEngine = CADDrawingExportEngine


def main() -> None:
    engine = CADDrawingExportEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    main()
'@

$BatContent = @'
@echo off
setlocal
cd /d "%~dp0"

echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.5

python baoees\project_analyzer\project_intake_engine.py || goto error
python baoees\project_analyzer\brewster_knowledge_migration_engine.py || goto error
python baoees\project_analyzer\deep_knowledge_harvest_engine.py || goto error
python baoees\project_analyzer\module_registry_engine.py || goto error
python baoees\project_analyzer\aaie_bib_assumption_loader.py || goto error
python baoees\project_analyzer\project_context_builder_engine.py || goto error
python baoees\project_analyzer\geotechniek_engine.py || goto error
python baoees\project_analyzer\foundation_engine.py || goto error
python baoees\project_analyzer\structural_engine.py || goto error
python baoees\project_analyzer\cad_drawing_export_engine.py || goto error
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

echo PROJECT PHOENIX v7.5 START PROJECTANALYSE KLAAR

if exist "outputs\projects\project_cad_export_dashboard_v7_5.html" (
    start "" "outputs\projects\project_cad_export_dashboard_v7_5.html"
)

git status
pause
exit /b 0

:error
echo FOUT: START PROJECTANALYSE v7.5 is gestopt.
git status
pause
exit /b 1
'@

$Ps1Content = @'
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.5" -ForegroundColor Cyan

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
    "baoees\project_analyzer\cad_drawing_export_engine.py",
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

Write-Host "PROJECT PHOENIX v7.5 START PROJECTANALYSE KLAAR" -ForegroundColor Green

$Dashboard = Join-Path $PSScriptRoot "outputs\projects\project_cad_export_dashboard_v7_5.html"
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
    engine = "Project Phoenix CAD Drawing Export Connector"
    engine_version = "v7.5"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    cad_drawing_export_engine = "$EnginePath"
    purpose = "Genereert concept-DXF bestanden voor situatie, fundering, constructie en doorsnede."
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole CAD Drawing Export Engine..." -ForegroundColor Cyan
python -m py_compile baoees\project_analyzer\cad_drawing_export_engine.py

Write-Host "Test START_PROJECTANALYSE_v7_5.ps1..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\START_PROJECTANALYSE_v7_5.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v7.5 UPDATE KLAAR" -ForegroundColor Green
