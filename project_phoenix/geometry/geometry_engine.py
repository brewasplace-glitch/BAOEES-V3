from pathlib import Path
from datetime import datetime
import json

from project_phoenix.geometry.building.architectural_geometry_builder import ArchitecturalGeometryBuilder
from project_phoenix.geometry.exporters.dxf_geometry_exporter import PhoenixDxfGeometryExporter
from project_phoenix.geometry.digital_twin.geometry_digital_twin_exporter import PhoenixGeometryDigitalTwinExporter


class PhoenixGeometryEngine:
    VERSION = "1.0.0"

    def run_from_floorplan(self, floorplan):
        geometry_model = ArchitecturalGeometryBuilder().build_from_floorplan(floorplan)
        dxf_export = PhoenixDxfGeometryExporter().export_geometry_model(geometry_model)
        dt_export = PhoenixGeometryDigitalTwinExporter().export(geometry_model)

        result = {
            "engine": "Phoenix Geometry Engine",
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "geometry_model": geometry_model,
            "exports": {
                "dxf": dxf_export,
                "digital_twin": dt_export
            },
            "status": "ok"
        }

        out = Path("outputs/geometry_engine_v1_0")
        out.mkdir(parents=True, exist_ok=True)
        (out / "pge_v1_0_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        return result


def run_demo():
    floorplan = {
        "floors": {
            "begane grond": [
                {"space": "Entree", "function": "verkeersruimte", "x": 0, "y": 0, "width_m": 3, "length_m": 3.5},
                {"space": "Gebedsruimte heren", "function": "bijeenkomstfunctie", "x": 3, "y": 0, "width_m": 10, "length_m": 12},
                {"space": "Wasruimte", "function": "sanitair", "x": 13, "y": 0, "width_m": 3, "length_m": 4}
            ],
            "verdieping": [
                {"space": "Gebedsruimte dames", "function": "bijeenkomstfunctie", "x": 0, "y": 0, "width_m": 8, "length_m": 10},
                {"space": "Leslokaal", "function": "onderwijs", "x": 8, "y": 0, "width_m": 5, "length_m": 6}
            ]
        }
    }
    return PhoenixGeometryEngine().run_from_floorplan(floorplan)


if __name__ == "__main__":
    result = run_demo()
    print("Phoenix Geometry Engine v1.0 uitgevoerd.")
    print("Status:", result["status"])
    print("Spaces:", result["geometry_model"]["counts"]["spaces"])
    print("Walls:", result["geometry_model"]["counts"]["walls"])
