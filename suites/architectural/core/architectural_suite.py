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
        report += f"Totaal oppervlak ruimtestaat: {schedule.get('total_area_m2')} mÂ²\n\n"
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
            "Uitbreiding voorlopig circa 20 mÂ².",
            "Definitieve maatvoering wordt gekoppeld aan ingelezen tekeningen.",
            "Deze v1.0 genereert een schematische plattegrond als basis voor latere DXF/PDF/IFC-export."
        ]
    }

    return ArchitecturalSuiteV1().run(payload)


if __name__ == "__main__":
    result = run_demo()
    print("Architectural Suite v1.0 uitgevoerd.")
    print("Status:", result["status"])
