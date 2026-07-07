param(
    [string]$RepoPath = "."
)

$ErrorActionPreference = "Stop"

Write-Host "BREWSTER ENGINEERING WIZARD - Architectural Module v1 installer" -ForegroundColor Cyan

$repo = Resolve-Path $RepoPath
Set-Location $repo

if (-not (Test-Path "baoees")) {
    throw "Map 'baoees' niet gevonden. Voer dit script uit vanuit de hoofdmap van je BAOEES/BREWSTER repository."
}

$dirs = @(
    "baoees/architectural",
    "baoees/architectural/templates",
    "baoees/architectural/rules",
    "outputs/architectural_examples",
    "docs/architectural"
)

foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

@'
"""
BREWSTER Architectural Engine v1.0

Doel:
- Bouwkundig programma van eisen verwerken
- Ruimteschema genereren
- Bouwkundige controles uitvoeren
- Tekenpakket-output voorbereiden
- Vergunningsteksten voorbereiden
- Digital Twin architectural payload maken
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any
import json
from pathlib import Path


@dataclass
class Room:
    name: str
    function: str
    floor: str
    area_m2: float
    notes: str = ""


@dataclass
class ArchitecturalProject:
    project_name: str
    location: str
    building_type: str
    gross_floor_area_m2: float
    extension_area_m2: float
    rooms: List[Room]
    assumptions: List[str]


class ArchitecturalEngine:
    def __init__(self, output_dir: str = "outputs/architectural_examples"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, project: ArchitecturalProject) -> Dict[str, Any]:
        room_total = round(sum(room.area_m2 for room in project.rooms), 2)

        result = {
            "engine": "BREWSTER Architectural Engine",
            "version": "1.0",
            "project": asdict(project),
            "checks": {
                "room_total_m2": room_total,
                "gross_floor_area_m2": project.gross_floor_area_m2,
                "extension_area_m2": project.extension_area_m2,
                "area_balance_ok": room_total <= project.gross_floor_area_m2,
            },
            "outputs": {
                "architectural_program": "architectural_program.json",
                "permit_text": "architectural_permit_text.md",
                "drawing_brief": "architectural_drawing_brief.md",
                "digital_twin_payload": "architectural_digital_twin.json",
            },
        }

        self._write_outputs(result)
        return result

    def _write_outputs(self, result: Dict[str, Any]) -> None:
        project = result["project"]

        (self.output_dir / "architectural_program.json").write_text(
            json.dumps(project, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        permit_text = f"""# Bouwkundige projectomschrijving

Project: {project['project_name']}
Locatie: {project['location']}
Gebouwtype: {project['building_type']}

De bouwkundige opgave betreft het uitwerken van het ruimtelijk programma, de bestaande en nieuwe situatie, de bouwkundige tekeningen, de gebruiksfuncties en de vergunningstechnische onderbouwing.

Uitbreiding: {project['extension_area_m2']} m².

## Ruimten
""" + "\n".join(
            f"- {r['floor']} - {r['name']} ({r['function']}): {r['area_m2']} m²"
            for r in project["rooms"]
        )

        (self.output_dir / "architectural_permit_text.md").write_text(
            permit_text,
            encoding="utf-8",
        )

        drawing_brief = f"""# Bouwkundig tekenpakket - opdrachtbrief

Project: {project['project_name']}

Te genereren tekeningen:
1. Situatietekening bestaand/nieuw
2. Plattegronden bestaand/nieuw per bouwlaag
3. Gevelaanzichten bestaand/nieuw
4. Doorsneden
5. Bouwkundige maatvoering
6. Ruimtestempel per ruimte
7. 3D massa-impressie
8. Vergunningstekeningenset PDF/DXF/DWG/SKP

Controlepunten:
- Schaal en maatvoering
- Noordpijl en legenda
- Bestaand versus nieuw duidelijk onderscheiden
- Gebruiksfuncties per ruimte
- Oppervlaktebalans
- Aansluiting op vergunningdossier
"""
        (self.output_dir / "architectural_drawing_brief.md").write_text(
            drawing_brief,
            encoding="utf-8",
        )

        digital_twin = {
            "discipline": "architectural",
            "project_name": project["project_name"],
            "location": project["location"],
            "spaces": project["rooms"],
            "gross_floor_area_m2": project["gross_floor_area_m2"],
            "extension_area_m2": project["extension_area_m2"],
            "status": "concept",
        }

        (self.output_dir / "architectural_digital_twin.json").write_text(
            json.dumps(digital_twin, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def demo_moskee_bunschoten() -> Dict[str, Any]:
    project = ArchitecturalProject(
        project_name="Moskee Bikkersweg 88 Bunschoten - Bouwkundig deel",
        location="Bikkersweg 88, Bunschoten",
        building_type="Maatschappelijke/religieuze voorziening",
        gross_floor_area_m2=0.0,
        extension_area_m2=20.0,
        rooms=[
            Room("Entree", "verkeersruimte", "begane grond", 0.0),
            Room("Gebedsruimte heren", "bijeenkomstfunctie", "begane grond", 0.0),
            Room("Conferentie/ontmoeting", "bijeenkomstfunctie", "begane grond", 0.0),
            Room("Rituele wasruimte", "sanitaire functie", "begane grond", 0.0),
            Room("Toiletten", "sanitaire functie", "begane grond", 0.0),
            Room("Gebedsruimte dames", "bijeenkomstfunctie", "verdieping", 0.0),
            Room("Leslokalen", "onderwijs/nevenfunctie", "verdieping", 0.0),
            Room("Kantine", "bijeenkomst/nevenfunctie", "verdieping", 0.0),
        ],
        assumptions=[
            "Uitbreiding voorlopig gesteld op circa 20 m².",
            "Definitieve maatvoering moet worden gekoppeld aan ingelezen tekeningen.",
            "Bestaande uploads/foto's worden gebruikt als bron voor gevels, plattegronden en situatie.",
        ],
    )

    return ArchitecturalEngine().run(project)


if __name__ == "__main__":
    result = demo_moskee_bunschoten()
    print(json.dumps(result, indent=2, ensure_ascii=False))
'@ | Set-Content -Encoding UTF8 "baoees/architectural/architectural_engine.py"

@'
# BREWSTER Bouwkundig Deel v1.0

Deze module vormt de basis voor het volledig afbouwen van het bouwkundige deel van BREWSTER ENGINEERING WIZARD / BAOEES.

## Functies v1
- Bouwkundig programma van eisen
- Ruimteschema
- Projectomschrijving
- Vergunningstekst
- Tekenpakket-opdrachtbrief
- Digital Twin architectural payload

## Volgende bouwlagen
1. Inlezen bestaande tekeningen en foto's
2. Automatische ruimtestempels
3. Bouwkundige maatvoering
4. Plattegronden bestaand/nieuw
5. Gevels bestaand/nieuw
6. Doorsneden
7. 3D massa
8. Export PDF/DOCX/DXF/DWG/SKP
'@ | Set-Content -Encoding UTF8 "docs/architectural/ARCHITECTURAL_MODULE_v1.md"

@'
{
  "module": "architectural",
  "version": "1.0",
  "status": "installed",
  "default_outputs": [
    "architectural_program.json",
    "architectural_permit_text.md",
    "architectural_drawing_brief.md",
    "architectural_digital_twin.json"
  ],
  "next_modules": [
    "drawing_reader",
    "room_stamp_engine",
    "floorplan_generator",
    "facade_generator",
    "section_generator",
    "architectural_pdf_export"
  ]
}
'@ | Set-Content -Encoding UTF8 "baoees/architectural/module_manifest.json"

python "baoees/architectural/architectural_engine.py"

git status

Write-Host ""
Write-Host "Klaar: Architectural Module v1 is geplaatst en demo-output is gegenereerd." -ForegroundColor Green
Write-Host "Controleer de output in: outputs/architectural_examples" -ForegroundColor Green