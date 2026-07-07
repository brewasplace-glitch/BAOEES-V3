from pathlib import Path
from datetime import datetime
import json


class ArchitecturalDigitalTwinExporter:
    MODULE_ID = "architectural.digital_twin.export"
    VERSION = "1.2.0"

    def __init__(self, output_dir="outputs/architectural_suite_v1_2/digital_twin"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, result):
        project = result.get("project", {})
        results = result.get("results", {})

        dt = {
            "digital_twin_version": "architectural_v1_2",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": {
                "project_id": project.get("project_id"),
                "project_name": project.get("project_name"),
                "location": project.get("location"),
                "building_type": project.get("building_type")
            },
            "spaces": results.get("space_schedule", {}).get("rows", []),
            "floorplans": results.get("floorplan_generator", {}).get("floors", {}),
            "facades": results.get("facade_generator", {}).get("facades", []),
            "sections": results.get("section_generator", {}).get("sections", []),
            "roof": results.get("roof_generator", {}).get("roof", {}),
            "dimensions": results.get("dimensioning", {}).get("dimensions", []),
            "source_traceability": {
                "knowledge_sources": ["PKB", "BIB", "Knowledge Graph", "EAMS"],
                "created_by": "Project Phoenix Architectural Suite v1.2"
            }
        }

        path = self.output_dir / "architectural_digital_twin_v1_2.json"
        path.write_text(json.dumps(dt, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "status": "ok",
            "path": str(path),
            "object_counts": {
                "spaces": len(dt["spaces"]),
                "facades": len(dt["facades"]),
                "sections": len(dt["sections"])
            }
        }
