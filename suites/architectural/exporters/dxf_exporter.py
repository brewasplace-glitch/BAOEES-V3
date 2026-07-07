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
