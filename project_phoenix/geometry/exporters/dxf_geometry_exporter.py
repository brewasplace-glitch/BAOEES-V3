from pathlib import Path


class PhoenixDxfGeometryExporter:
    VERSION = "1.0.0"

    def __init__(self, output_dir="outputs/geometry_engine_v1_0/dxf"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_geometry_model(self, geometry_model, filename="pge_geometry_model_v1_0.dxf"):
        path = self.output_dir / filename
        lines = ["0", "SECTION", "2", "ENTITIES"]

        for wall in geometry_model.get("walls", []):
            start = wall["start"]
            end = wall["end"]
            layer = wall.get("floor", "walls")
            lines.extend([
                "0", "LINE",
                "8", layer,
                "10", str(start["x"]), "20", str(start["y"]), "30", "0",
                "11", str(end["x"]), "21", str(end["y"]), "31", "0"
            ])

        lines.extend(["0", "ENDSEC", "0", "EOF"])
        path.write_text("\n".join(lines), encoding="utf-8")

        return {
            "exporter": "PhoenixDxfGeometryExporter",
            "version": self.VERSION,
            "status": "ok",
            "path": str(path)
        }
