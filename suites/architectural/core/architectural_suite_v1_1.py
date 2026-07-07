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
