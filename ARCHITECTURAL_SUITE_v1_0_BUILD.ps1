param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "PROJECT PHOENIX - Architectural Suite v1.0 Build" -ForegroundColor Cyan
Write-Host ""

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path ".git")) { throw "Geen git repository gevonden." }
if (-not (Test-Path "project_phoenix/pdk")) { throw "PDK niet gevonden. Installeer eerst Phoenix Development Kit v1.0." }

Write-Host "Stap 1 - Openstaande documentatie en status veilig vastleggen..." -ForegroundColor Yellow
git status --short | Set-Content -Encoding UTF8 "ARCHITECTURAL_SUITE_v1_0_pre_build_status.txt"

$changes = git status --short
if ($changes) {
    git add -A
    git commit -m "chore: stabilize before architectural suite v1.0 build"
}

Write-Host "Stap 2 - Architectural Suite v1.0 structuur uitbreiden..." -ForegroundColor Yellow

$dirs = @(
    "suites/architectural/core",
    "suites/architectural/engines",
    "suites/architectural/models",
    "suites/architectural/schemas",
    "suites/architectural/tests",
    "suites/architectural/docs",
    "suites/architectural/exports",
    "suites/architectural/examples",
    "outputs/architectural_suite_v1_0"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class ArchitecturalSpace:
    name: str
    function: str
    floor: str
    area_m2: float = 0.0
    width_m: float = 0.0
    length_m: float = 0.0
    notes: str = ""


@dataclass
class ArchitecturalProject:
    project_id: str
    project_name: str
    location: str
    building_type: str
    client: str = ""
    extension_area_m2: float = 0.0
    gross_floor_area_m2: float = 0.0
    spaces: List[ArchitecturalSpace] = None
    assumptions: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        if data["spaces"] is None:
            data["spaces"] = []
        if data["assumptions"] is None:
            data["assumptions"] = []
        return data
'@ | Set-Content -Encoding UTF8 "suites/architectural/models/architectural_models.py"

@'
from datetime import datetime
from suites.architectural.models.architectural_models import ArchitecturalProject, ArchitecturalSpace


class ProjectIntakeEngine:
    MODULE_ID = "architectural.project_intake"
    VERSION = "1.0.0"

    def run(self, payload=None):
        payload = payload or {}

        spaces = []
        for item in payload.get("spaces", []):
            spaces.append(
                ArchitecturalSpace(
                    name=item.get("name", ""),
                    function=item.get("function", ""),
                    floor=item.get("floor", "begane grond"),
                    area_m2=float(item.get("area_m2", 0.0)),
                    width_m=float(item.get("width_m", 0.0)),
                    length_m=float(item.get("length_m", 0.0)),
                    notes=item.get("notes", "")
                )
            )

        project = ArchitecturalProject(
            project_id=payload.get("project_id", "architectural_demo"),
            project_name=payload.get("project_name", "Architectural Demo Project"),
            location=payload.get("location", ""),
            building_type=payload.get("building_type", ""),
            client=payload.get("client", ""),
            extension_area_m2=float(payload.get("extension_area_m2", 0.0)),
            gross_floor_area_m2=float(payload.get("gross_floor_area_m2", 0.0)),
            spaces=spaces,
            assumptions=payload.get("assumptions", [])
        )

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "project": project.to_dict(),
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/project_intake.py"

@'
from datetime import datetime


class ProgramOfRequirementsEngine:
    MODULE_ID = "architectural.program_of_requirements"
    VERSION = "1.0.0"

    def run(self, project):
        spaces = project.get("spaces", [])
        requirements = {
            "functional_requirements": [],
            "spatial_requirements": [],
            "technical_requirements": [],
            "permit_requirements": []
        }

        for space in spaces:
            requirements["spatial_requirements"].append({
                "space": space.get("name", ""),
                "function": space.get("function", ""),
                "floor": space.get("floor", ""),
                "target_area_m2": space.get("area_m2", 0.0)
            })

        requirements["technical_requirements"].extend([
            "maatvoering controleren",
            "bestaand en nieuw onderscheiden",
            "koppeling met Digital Twin voorbereiden",
            "export naar PDF/DXF/IFC/SKP voorbereiden"
        ])

        requirements["permit_requirements"].extend([
            "situatie bestaand/nieuw",
            "plattegronden bestaand/nieuw",
            "gevels bestaand/nieuw",
            "doorsneden",
            "ruimtestaat",
            "projectomschrijving"
        ])

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "requirements": requirements,
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/program_of_requirements.py"

@'
from datetime import datetime


class SpaceScheduleEngine:
    MODULE_ID = "architectural.space_schedule"
    VERSION = "1.0.0"

    def run(self, project):
        rows = []
        total_area = 0.0

        for idx, space in enumerate(project.get("spaces", []), start=1):
            area = float(space.get("area_m2", 0.0))
            total_area += area
            rows.append({
                "nr": idx,
                "floor": space.get("floor", ""),
                "name": space.get("name", ""),
                "function": space.get("function", ""),
                "area_m2": area,
                "width_m": space.get("width_m", 0.0),
                "length_m": space.get("length_m", 0.0),
                "notes": space.get("notes", "")
            })

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "rows": rows,
            "total_area_m2": round(total_area, 2),
            "space_count": len(rows),
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/space_schedule.py"

@'
from datetime import datetime


class FloorplanGeneratorEngine:
    MODULE_ID = "architectural.floorplan_generator"
    VERSION = "1.0.0"

    def run(self, project, space_schedule):
        floors = {}
        x_cursor_by_floor = {}

        for row in space_schedule.get("rows", []):
            floor = row.get("floor", "begane grond")
            floors.setdefault(floor, [])
            x = x_cursor_by_floor.get(floor, 0.0)

            width = float(row.get("width_m") or 4.0)
            length = float(row.get("length_m") or 4.0)

            if width <= 0:
                width = 4.0
            if length <= 0:
                length = 4.0

            room_rect = {
                "space": row.get("name", ""),
                "function": row.get("function", ""),
                "x": round(x, 2),
                "y": 0.0,
                "width_m": round(width, 2),
                "length_m": round(length, 2),
                "area_m2": row.get("area_m2", 0.0)
            }

            floors[floor].append(room_rect)
            x_cursor_by_floor[floor] = x + width

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "drawing_type": "schematic_floorplan",
            "floors": floors,
            "exports_prepared": ["json", "pdf_next", "dxf_next", "ifc_next", "skp_next"],
            "status": "ok"
        }
'@ | Set-Content -Encoding UTF8 "suites/architectural/engines/floorplan_generator.py"

@'
from pathlib import Path
from datetime import datetime
import json

from suites.architectural.engines.project_intake import ProjectIntakeEngine
from suites.architectural.engines.program_of_requirements import ProgramOfRequirementsEngine
from suites.architectural.engines.space_schedule import SpaceScheduleEngine
from suites.architectural.engines.floorplan_generator import FloorplanGeneratorEngine


class ArchitecturalSuiteV1:
    VERSION = "1.0.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_0"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, payload):
        intake = ProjectIntakeEngine().run(payload)
        project = intake["project"]

        requirements = ProgramOfRequirementsEngine().run(project)
        schedule = SpaceScheduleEngine().run(project)
        floorplan = FloorplanGeneratorEngine().run(project, schedule)

        result = {
            "suite": "Architectural Suite",
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "results": {
                "project_intake": intake,
                "program_of_requirements": requirements,
                "space_schedule": schedule,
                "floorplan_generator": floorplan
            },
            "status": "ok"
        }

        (self.output_dir / "architectural_suite_v1_0_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        report = "# Architectural Suite v1.0 Report\n\n"
        report += f"Project: {project.get('project_name')}\n\n"
        report += f"Locatie: {project.get('location')}\n\n"
        report += f"Ruimten: {schedule.get('space_count')}\n\n"
        report += f"Totaal oppervlak ruimtestaat: {schedule.get('total_area_m2')} m²\n\n"
        report += "## Modules uitgevoerd\n"
        report += "- Project Intake\n- Programma van Eisen\n- Ruimtestaat\n- Schematische plattegrondgenerator\n"

        (self.output_dir / "architectural_suite_v1_0_report.md").write_text(
            report,
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
        "gross_floor_area_m2": 0.0,
        "spaces": [
            {"name": "Entree", "function": "verkeersruimte", "floor": "begane grond", "area_m2": 10.0, "width_m": 3.0, "length_m": 3.5},
            {"name": "Gebedsruimte heren", "function": "bijeenkomstfunctie", "floor": "begane grond", "area_m2": 120.0, "width_m": 10.0, "length_m": 12.0},
            {"name": "Conferentie / ontmoeting", "function": "bijeenkomstfunctie", "floor": "begane grond", "area_m2": 40.0, "width_m": 6.0, "length_m": 7.0},
            {"name": "Rituele wasruimte", "function": "sanitaire functie", "floor": "begane grond", "area_m2": 12.0, "width_m": 3.0, "length_m": 4.0},
            {"name": "Gebedsruimte dames", "function": "bijeenkomstfunctie", "floor": "verdieping", "area_m2": 80.0, "width_m": 8.0, "length_m": 10.0},
            {"name": "Leslokalen", "function": "onderwijs/nevenfunctie", "floor": "verdieping", "area_m2": 30.0, "width_m": 5.0, "length_m": 6.0}
        ],
        "assumptions": [
            "Uitbreiding voorlopig circa 20 m².",
            "Definitieve maatvoering wordt gekoppeld aan ingelezen tekeningen.",
            "Deze v1.0 genereert een schematische plattegrond als basis voor latere DXF/PDF/IFC-export."
        ]
    }

    return ArchitecturalSuiteV1().run(payload)


if __name__ == "__main__":
    result = run_demo()
    print("Architectural Suite v1.0 uitgevoerd.")
    print("Status:", result["status"])
'@ | Set-Content -Encoding UTF8 "suites/architectural/core/architectural_suite.py"

@'
{
  "suite_id": "architectural",
  "suite_title": "Architectural Suite",
  "version": "1.0.0",
  "status": "implemented_v1",
  "modules": [
    "project_intake",
    "program_of_requirements",
    "space_schedule",
    "floorplan_generator"
  ],
  "knowledge_sources": [
    "PKB",
    "BIB",
    "Knowledge Graph",
    "Executable Architectural Master Specification"
  ],
  "exports_current": [
    "json",
    "markdown"
  ],
  "exports_next": [
    "pdf",
    "docx",
    "dxf",
    "ifc",
    "skp"
  ]
}
'@ | Set-Content -Encoding UTF8 "suites/architectural/suite_manifest.json"

@'
# Architectural Suite v1.0

## Geïmplementeerde modules

- Project Intake Engine
- Programma van Eisen Engine
- Ruimtestaat Engine
- Schematische Plattegrondgenerator

## Doel

Deze release maakt de eerste werkende bouwkundige keten binnen Project Phoenix.

Input → Intake → PvE → Ruimtestaat → Plattegrond-schema → Output

## Volgende release

Architectural Suite v1.1:
- Gevelgenerator
- Doorsnedegenerator
- Dakgenerator
- PDF/DXF export basis
'@ | Set-Content -Encoding UTF8 "suites/architectural/docs/ARCHITECTURAL_SUITE_v1_0.md"

Write-Host "Stap 3 - Architectural Suite v1.0 demo uitvoeren..." -ForegroundColor Yellow
python -m suites.architectural.core.architectural_suite

Write-Host "Stap 4 - Commit maken..." -ForegroundColor Yellow
git add suites/architectural outputs/architectural_suite_v1_0 ARCHITECTURAL_SUITE_v1_0_pre_build_status.txt
git commit -m "feat: implement architectural suite v1.0 core workflow"

Write-Host "Stap 5 - Status tonen..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "KLAAR: Architectural Suite v1.0 is gebouwd." -ForegroundColor Green
Write-Host "Voer daarna uit: git push" -ForegroundColor Green