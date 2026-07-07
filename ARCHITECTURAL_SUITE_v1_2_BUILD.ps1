param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX - Architectural Suite v1.2 Export & Digital Twin Build" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) { throw "Geen git repository gevonden." }
if (-not (Test-Path "suites/architectural/core/architectural_suite_v1_1.py")) { throw "Architectural Suite v1.1 niet gevonden." }

Write-Host "Stap 1 - Status veilig vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "ARCHITECTURAL_SUITE_v1_2_pre_build_status.txt"

$changes = git status --short
if ($changes) {
    git add -A
    git commit -m "chore: stabilize before architectural suite v1.2 build"
}

Write-Host "Stap 2 - Export en Digital Twin engines toevoegen..." -ForegroundColor Yellow

$dirs = @(
    "suites/architectural/exporters",
    "suites/architectural/digital_twin",
    "outputs/architectural_suite_v1_2",
    "outputs/architectural_suite_v1_2/drawings",
    "outputs/architectural_suite_v1_2/digital_twin",
    "outputs/architectural_suite_v1_2/reports"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
from pathlib import Path
from datetime import datetime


class ArchitecturalPdfDrawingExporter:
    MODULE_ID = "architectural.export.pdf_drawing_package"
    VERSION = "1.2.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_2/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        try:
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
        except Exception as exc:
            fallback = self.output_dir / "architectural_drawing_package_fallback.md"
            fallback.write_text(
                "# Architectural Drawing Package\n\n"
                "PDF export kon niet worden uitgevoerd omdat reportlab ontbreekt.\n\n"
                f"Fout: {exc}\n",
                encoding="utf-8"
            )
            return {"status": "fallback_markdown", "path": str(fallback)}

        project = result.get("project", {})
        results = result.get("results", {})
        schedule = results.get("space_schedule", {})
        floorplan = results.get("floorplan_generator", {})
        dimensions = results.get("dimensioning", {})

        pdf_path = self.output_dir / "architectural_drawing_package_v1_2.pdf"
        doc = SimpleDocTemplate(str(pdf_path))
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("PROJECT PHOENIX - Architectural Drawing Package v1.2", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Project: {project.get('project_name', '')}", styles["Heading2"]))
        story.append(Paragraph(f"Locatie: {project.get('location', '')}", styles["BodyText"]))
        story.append(Paragraph(f"Gebouwtype: {project.get('building_type', '')}", styles["BodyText"]))
        story.append(Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["BodyText"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Ruimtestaat", styles["Heading2"]))
        table_data = [["Nr", "Bouwlaag", "Ruimte", "Functie", "Opp. m2"]]
        for row in schedule.get("rows", []):
            table_data.append([
                row.get("nr", ""),
                row.get("floor", ""),
                row.get("name", ""),
                row.get("function", ""),
                row.get("area_m2", 0.0)
            ])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        story.append(Paragraph("Schematische plattegrond", styles["Heading2"]))
        for floor, rooms in floorplan.get("floors", {}).items():
            story.append(Paragraph(f"Bouwlaag: {floor}", styles["Heading3"]))
            for room in rooms:
                story.append(Paragraph(
                    f"- {room.get('space', '')}: x={room.get('x')} m, y={room.get('y')} m, "
                    f"b={room.get('width_m')} m, l={room.get('length_m')} m",
                    styles["BodyText"]
                ))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Maatvoering", styles["Heading2"]))
        for dim in dimensions.get("dimensions", []):
            story.append(Paragraph(str(dim), styles["BodyText"]))

        doc.build(story)

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "status": "ok",
            "path": str(pdf_path)
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/exporters/pdf_drawing_exporter.py"

@'
from pathlib import Path


class ArchitecturalDxfExporter:
    MODULE_ID = "architectural.export.dxf_concept"
    VERSION = "1.2.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_2/drawings"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        floorplan = result.get("results", {}).get("floorplan_generator", {})
        dxf_path = self.output_dir / "architectural_floorplan_concept_v1_2.dxf"

        lines = [
            "0", "SECTION", "2", "ENTITIES"
        ]

        for floor, rooms in floorplan.get("floors", {}).items():
            for room in rooms:
                x = float(room.get("x", 0.0))
                y = float(room.get("y", 0.0))
                w = float(room.get("width_m", 0.0))
                l = float(room.get("length_m", 0.0))
                points = [
                    (x, y),
                    (x + w, y),
                    (x + w, y + l),
                    (x, y + l),
                    (x, y)
                ]
                for a, b in zip(points[:-1], points[1:]):
                    lines.extend([
                        "0", "LINE",
                        "8", floor,
                        "10", str(a[0]), "20", str(a[1]), "30", "0",
                        "11", str(b[0]), "21", str(b[1]), "31", "0"
                    ])

        lines.extend(["0", "ENDSEC", "0", "EOF"])
        dxf_path.write_text("\n".join(lines), encoding="utf-8")

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "status": "ok",
            "path": str(dxf_path)
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/exporters/dxf_exporter.py"

@'
from pathlib import Path
from datetime import datetime
import json


class ArchitecturalDigitalTwinExporter:
    MODULE_ID = "architectural.digital_twin.export"
    VERSION = "1.2.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_2/digital_twin"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        project = result.get("project", {})
        results = result.get("results", {})

        dt = {
            "digital_twin_version": "architectural_v1_2",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": {
                "project_id": project.get("project_id"),
                "project_name": project.get("project_name"),
                "location": project.get("location"),
                "building_type": project.get("building_type")
            },
            "spaces": results.get("space_schedule", {}).get("rows", []),
            "floorplans": results.get("floorplan_generator", {}).get("floors", {}),
            "facades": results.get("facade_generator", {}).get("facades", []),
            "sections": results.get("section_generator", {}).get("sections", []),
            "roof": results.get("roof_generator", {}).get("roof", {}),
            "dimensions": results.get("dimensioning", {}).get("dimensions", []),
            "source_traceability": {
                "knowledge_sources": ["PKB", "BIB", "Knowledge Graph", "EAMS"],
                "created_by": "Project Phoenix Architectural Suite v1.2"
            }
        }

        path = self.output_dir / "architectural_digital_twin_v1_2.json"
        path.write_text(json.dumps(dt, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "status": "ok",
            "path": str(path),
            "object_counts": {
                "spaces": len(dt["spaces"]),
                "facades": len(dt["facades"]),
                "sections": len(dt["sections"])
            }
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/digital_twin/digital_twin_exporter.py"

@'
from pathlib import Path
from datetime import datetime
import json

from suites.architectural.core.architectural_suite_v1_1 import ArchitecturalSuiteV11
from suites.architectural.exporters.pdf_drawing_exporter import ArchitecturalPdfDrawingExporter
from suites.architectural.exporters.dxf_exporter import ArchitecturalDxfExporter
from suites.architectural.digital_twin.digital_twin_exporter import ArchitecturalDigitalTwinExporter


class ArchitecturalSuiteV12:
    VERSION = "1.2.0"

    def run(self, payload):
        base = ArchitecturalSuiteV11().run(payload)

        pdf_export = ArchitecturalPdfDrawingExporter().export(base)
        dxf_export = ArchitecturalDxfExporter().export(base)
        digital_twin_export = ArchitecturalDigitalTwinExporter().export(base)

        result = {
            **base,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "exports": {
                **base.get("exports", {}),
                "pdf_drawing_package": pdf_export,
                "dxf_concept": dxf_export,
                "digital_twin": digital_twin_export,
                "ifc_next": "planned_v1_3",
                "skp_next": "planned_v1_3"
            },
            "status": "ok"
        }

        out = Path("outputs/architectural_suite_v1_2")
        out.mkdir(parents=True, exist_ok=True)
        (out / "architectural_suite_v1_2_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return result


def run_demo():
    payload = {
        "project_id": "moskee_bikkersweg_88",
        "project_name": "Moskee Bikkersweg 88 Bunschoten",
        "location": "Bikkersweg 88, Bunschoten",
        "building_type": "Maatschappelijke/religieuze voorziening",
        "client": "A. Brewster Architects.sr",
        "extension_area_m2": 20.0,
        "spaces": [
            {"name": "Entree", "function": "verkeersruimte", "floor": "begane grond", "area_m2": 10.0, "width_m": 3.0, "length_m": 3.5},
            {"name": "Gebedsruimte heren", "function": "bijeenkomstfunctie", "floor": "begane grond", "area_m2": 120.0, "width_m": 10.0, "length_m": 12.0},
            {"name": "Conferentie / ontmoeting", "function": "bijeenkomstfunctie", "floor": "begane grond", "area_m2": 40.0, "width_m": 6.0, "length_m": 7.0},
            {"name": "Rituele wasruimte", "function": "sanitaire functie", "floor": "begane grond", "area_m2": 12.0, "width_m": 3.0, "length_m": 4.0},
            {"name": "Gebedsruimte dames", "function": "bijeenkomstfunctie", "floor": "verdieping", "area_m2": 80.0, "width_m": 8.0, "length_m": 10.0},
            {"name": "Leslokalen", "function": "onderwijs/nevenfunctie", "floor": "verdieping", "area_m2": 30.0, "width_m": 5.0, "length_m": 6.0}
        ],
        "assumptions": [
            "Architectural Suite v1.2 voegt PDF, DXF en Digital Twin export toe.",
            "IFC/SKP-export wordt voorbereid voor v1.3."
        ]
    }

    return ArchitecturalSuiteV12().run(payload)


if __name__ == "__main__":
    result = run_demo()
    print("Architectural Suite v1.2 uitgevoerd.")
    print("Status:", result["status"])
    print("PDF:", result["exports"]["pdf_drawing_package"]["path"])
    print("DXF:", result["exports"]["dxf_concept"]["path"])
    print("DT:", result["exports"]["digital_twin"]["path"])
'@ | Set-Content -Encoding UTF8 "suites/architectural/core/architectural_suite_v1_2.py"

@'
{
  "suite_id": "architectural",
  "suite_title": "Architectural Suite",
  "version": "1.2.0",
  "status": "implemented_v1_2",
  "modules": [
    "project_intake",
    "program_of_requirements",
    "space_schedule",
    "floorplan_generator",
    "facade_generator",
    "section_generator",
    "roof_generator",
    "dimensioning",
    "pdf_drawing_exporter",
    "dxf_exporter",
    "digital_twin_exporter"
  ],
  "exports_current": [
    "json",
    "markdown",
    "pdf",
    "dxf",
    "digital_twin_json"
  ],
  "exports_next": [
    "ifc",
    "skp",
    "freecad"
  ]
}
'@ | Set-Content -Encoding UTF8 "suites/architectural/suite_manifest.json"

@'
# Architectural Suite v1.2

## Toegevoegd

- PDF drawing package exporter
- DXF concept exporter
- Architectural Digital Twin payload
- IFC/SKP voorbereidingsvelden

## Doel

Deze release maakt de eerste exporteerbare bouwkundige keten:

Project Intake → PvE → Ruimtestaat → Plattegrond → Gevels → Doorsneden → Dak → Maatvoering → PDF/DXF/Digital Twin

## Volgende release

Architectural Suite v1.3:
- IFC-export
- SketchUp/SKP-koppeling
- FreeCAD payload
- betere geometrische objecten
'@ | Set-Content -Encoding UTF8 "suites/architectural/docs/ARCHITECTURAL_SUITE_v1_2.md"

Write-Host "Stap 3 - Architectural Suite v1.2 demo uitvoeren..." -ForegroundColor Yellow
python -m suites.architectural.core.architectural_suite_v1_2

Write-Host "Stap 4 - Commit maken..." -ForegroundColor Yellow
git add suites/architectural outputs/architectural_suite_v1_2 ARCHITECTURAL_SUITE_v1_2_pre_build_status.txt
git commit -m "feat: add architectural suite v1.2 pdf dxf digital twin exports"

Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Architectural Suite v1.2 is gebouwd." -ForegroundColor Green
Write-Host "Voer daarna uit: git push" -ForegroundColor Green