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
