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
