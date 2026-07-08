from pathlib import Path
from datetime import datetime
import json


class PhoenixGeometryDigitalTwinExporter:
    VERSION = "1.0.0"

    def __init__(self, output_dir="outputs/geometry_engine_v1_0/digital_twin"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, geometry_model, filename="pge_geometry_digital_twin_v1_0.json"):
        payload = {
            "digital_twin_layer": "geometry",
            "version": self.VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "geometry_model": geometry_model,
            "source": {
                "engine": "Phoenix Geometry Engine",
                "version": self.VERSION
            }
        }

        path = self.output_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "exporter": "PhoenixGeometryDigitalTwinExporter",
            "version": self.VERSION,
            "status": "ok",
            "path": str(path)
        }
