param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX - Architectural Suite v1.1 Build" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) { throw "Geen git repository gevonden." }
if (-not (Test-Path "suites/architectural")) { throw "Architectural Suite v1.0 niet gevonden." }

Write-Host "Stap 1 - Status veilig vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "ARCHITECTURAL_SUITE_v1_1_pre_build_status.txt"

$changes = git status --short
if ($changes) {
    git add -A
    git commit -m "chore: stabilize before architectural suite v1.1 build"
}

Write-Host "Stap 2 - v1.1 engines toevoegen..." -ForegroundColor Yellow

New-Item -ItemType Directory -Force -Path "outputs/architectural_suite_v1_1" | Out-Null
New-Item -ItemType Directory -Force -Path "suites/architectural/exporters" | Out-Null

@'
from datetime import datetime


class FacadeGeneratorEngine:
    MODULE_ID = "architectural.facade_generator"
    VERSION = "1.1.0"

    def run(self, project, floorplan):
        facades = []

        for floor_name, rooms in floorplan.get("floors", {}).items():
            total_width = sum(float(room.get("width_m", 0.0)) for room in rooms)
            max_depth = max([float(room.get("length_m", 0.0)) for room in rooms] or [0.0])

            facades.append({
                "floor": floor_name,
                "facade": "voor",
                "width_m": round(total_width, 2),
                "height_m": 3.2,
                "openings": self._generate_openings(rooms, "voor")
            })
            facades.append({
                "floor": floor_name,
                "facade": "achter",
                "width_m": round(total_width, 2),
                "height_m": 3.2,
                "openings": self._generate_openings(rooms, "achter")
            })
            facades.append({
                "floor": floor_name,
                "facade": "links",
                "width_m": round(max_depth, 2),
                "height_m": 3.2,
                "openings": []
            })
            facades.append({
                "floor": floor_name,
                "facade": "rechts",
                "width_m": round(max_depth, 2),
                "height_m": 3.2,
                "openings": []
            })

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "facades": facades,
            "status": "ok"
        }

    def _generate_openings(self, rooms, side):
        openings = []
        x = 1.0
        for room in rooms:
            openings.append({
                "room": room.get("space", ""),
                "type": "window",
                "x_m": round(x, 2),
                "sill_height_m": 0.9,
                "width_m": 1.2,
                "height_m": 1.4
            })
            x += 2.5
        return openings
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/facade_generator.py"

@'
from datetime import datetime


class SectionGeneratorEngine:
    MODULE_ID = "architectural.section_generator"
    VERSION = "1.1.0"

    def run(self, project, floorplan):
        floor_count = len(floorplan.get("floors", {}))
        if floor_count <= 0:
            floor_count = 1

        sections = [
            {
                "section_id": "A-A",
                "description": "schematische langsdoorsnede",
                "floor_count": floor_count,
                "floor_height_m": 3.2,
                "total_height_m": round(floor_count * 3.2 + 1.2, 2),
                "roof_type": "kap/plat dak nader te bepalen",
                "elements": [
                    "fundering indicatief",
                    "vloeren",
                    "wanden",
                    "dak",
                    "maatvoering"
                ]
            },
            {
                "section_id": "B-B",
                "description": "schematische dwarsdoorsnede",
                "floor_count": floor_count,
                "floor_height_m": 3.2,
                "total_height_m": round(floor_count * 3.2 + 1.2, 2),
                "roof_type": "kap/plat dak nader te bepalen",
                "elements": [
                    "vloerpeilen",
                    "vrije hoogte",
                    "dakopbouw",
                    "gevelhoogte"
                ]
            }
        ]

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "sections": sections,
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/section_generator.py"

@'
from datetime import datetime


class RoofGeneratorEngine:
    MODULE_ID = "architectural.roof_generator"
    VERSION = "1.1.0"

    def run(self, project, floorplan):
        footprint_width = 0.0
        footprint_depth = 0.0

        for rooms in floorplan.get("floors", {}).values():
            width = sum(float(room.get("width_m", 0.0)) for room in rooms)
            depth = max([float(room.get("length_m", 0.0)) for room in rooms] or [0.0])
            footprint_width = max(footprint_width, width)
            footprint_depth = max(footprint_depth, depth)

        roof = {
            "roof_type": "conceptueel plat dak / kap optioneel",
            "footprint_width_m": round(footprint_width, 2),
            "footprint_depth_m": round(footprint_depth, 2),
            "roof_area_m2": round(footprint_width * footprint_depth, 2),
            "drainage": "HWA nader uitwerken in MEP/riolering module",
            "notes": [
                "Dakvorm wordt later projectafhankelijk geoptimaliseerd.",
                "Voor moskeeproject kan koepel/minaret als architectonisch element worden toegevoegd."
            ]
        }

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "roof": roof,
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/roof_generator.py"

@'
from datetime import datetime


class DimensioningEngine:
    MODULE_ID = "architectural.dimensioning"
    VERSION = "1.1.0"

    def run(self, floorplan):
        dimensions = []

        for floor, rooms in floorplan.get("floors", {}).items():
            total_width = sum(float(room.get("width_m", 0.0)) for room in rooms)
            max_depth = max([float(room.get("length_m", 0.0)) for room in rooms] or [0.0])

            dimensions.append({
                "floor": floor,
                "type": "overall_width",
                "value_m": round(total_width, 2)
            })
            dimensions.append({
                "floor": floor,
                "type": "overall_depth",
                "value_m": round(max_depth, 2)
            })

            for room in rooms:
                dimensions.append({
                    "floor": floor,
                    "type": "room_dimension",
                    "space": room.get("space", ""),
                    "width_m": room.get("width_m", 0.0),
                    "length_m": room.get("length_m", 0.0)
                })

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "dimensions": dimensions,
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/dimensioning.py"

@'
from pathlib import Path
from datetime import datetime
import json


class ArchitecturalJsonExporter:
    VERSION = "1.1.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_1"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        json_path = self.output_dir / "architectural_suite_v1_1_full_output.json"
        json_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        report_path = self.output_dir / "architectural_suite_v1_1_report.md"
        project = result.get("project", {})
        report = "# Architectural Suite v1.1 Report\n\n"
        report += f"Project: {project.get('project_name', '')}\n\n"
        report += f"Locatie: {project.get('location', '')}\n\n"
        report += "## Modules\n\n"
        for key in result.get("results", {}).keys():
            report += f"- {key}\n"
        report += "\n## Status\n\n"
        report += result.get("status", "unknown")
        report_path.write_text(report, encoding="utf-8")

        return {
            "json": str(json_path),
            "markdown": str(report_path),
            "next_exports": ["pdf", "dxf", "ifc", "skp"]
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/exporters/json_exporter.py"

@'
from pathlib import Path
from datetime import datetime
import json

from suites.architectural.core.architectural_suite import ArchitecturalSuiteV1
from suites.architectural.engines.facade_generator import FacadeGeneratorEngine
from suites.architectural.engines.section_generator import SectionGeneratorEngine
from suites.architectural.engines.roof_generator import RoofGeneratorEngine
from suites.architectural.engines.dimensioning import DimensioningEngine
from suites.architectural.exporters.json_exporter import ArchitecturalJsonExporter


class ArchitecturalSuiteV11:
    VERSION = "1.1.0"

    def run(self, payload):
        base = ArchitecturalSuiteV1(output_dir="outputs/architectural_suite_v1_1/base").run(payload)
        project = base["project"]
        floorplan = base["results"]["floorplan_generator"]

        facade = FacadeGeneratorEngine().run(project, floorplan)
        section = SectionGeneratorEngine().run(project, floorplan)
        roof = RoofGeneratorEngine().run(project, floorplan)
        dimensions = DimensioningEngine().run(floorplan)

        result = {
            "suite": "Architectural Suite",
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "results": {
                **base["results"],
                "facade_generator": facade,
                "section_generator": section,
                "roof_generator": roof,
                "dimensioning": dimensions
            },
            "status": "ok"
        }

        export = ArchitecturalJsonExporter().export(result)
        result["exports"] = export

        Path("outputs/architectural_suite_v1_1").mkdir(parents=True, exist_ok=True)
        (Path("outputs/architectural_suite_v1_1") / "architectural_suite_v1_1_result.json").write_text(
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
            "Architectural Suite v1.1 genereert gevels, doorsneden, daken en maatvoering conceptueel.",
            "PDF/DXF/IFC/SKP worden in volgende release als echte exporters toegevoegd."
        ]
    }

    return ArchitecturalSuiteV11().run(payload)


if __name__ == "__main__":
    result = run_demo()
    print("Architectural Suite v1.1 uitgevoerd.")
    print("Status:", result["status"])
    print("Exports:", result.get("exports", {}))
'@ | Set-Content -Encoding UTF8 "suites/architectural/core/architectural_suite_v1_1.py"

@'
{
  "suite_id": "architectural",
  "suite_title": "Architectural Suite",
  "version": "1.1.0",
  "status": "implemented_v1_1",
  "modules": [
    "project_intake",
    "program_of_requirements",
    "space_schedule",
    "floorplan_generator",
    "facade_generator",
    "section_generator",
    "roof_generator",
    "dimensioning"
  ],
  "exports_current": [
    "json",
    "markdown"
  ],
  "exports_next": [
    "pdf",
    "dxf",
    "ifc",
    "skp"
  ]
}
'@ | Set-Content -Encoding UTF8 "suites/architectural/suite_manifest.json"

@'
# Architectural Suite v1.1

## Toegevoegd

- Gevelgenerator
- Doorsnedegenerator
- Dakgenerator
- Maatvoering
- JSON/Markdown exportstructuur

## Doel

Architectural Suite v1.1 vormt de eerste volledige bouwkundige conceptketen:

Project Intake → PvE → Ruimtestaat → Plattegrond → Gevels → Doorsneden → Dak → Maatvoering → Export

## Volgende release

Architectural Suite v1.2:
- PDF drawing exporter
- DXF drawing exporter
- Digital Twin payload
- IFC/SKP voorbereiding
'@ | Set-Content -Encoding UTF8 "suites/architectural/docs/ARCHITECTURAL_SUITE_v1_1.md"

Write-Host "Stap 3 - Architectural Suite v1.1 demo uitvoeren..." -ForegroundColor Yellow
python -m suites.architectural.core.architectural_suite_v1_1

Write-Host "Stap 4 - Commit maken..." -ForegroundColor Yellow
git add suites/architectural outputs/architectural_suite_v1_1 ARCHITECTURAL_SUITE_v1_1_pre_build_status.txt
git commit -m "feat: extend architectural suite to v1.1 drawing concept engines"

Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Architectural Suite v1.1 is gebouwd." -ForegroundColor Green
Write-Host "Voer daarna uit: git push" -ForegroundColor Green