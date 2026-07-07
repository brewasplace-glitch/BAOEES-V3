from datetime import datetime


class SpaceScheduleEngine:
    MODULE_ID = "architectural.space_schedule"
    VERSION = "1.0.0"

    def run(self, project):
        rows = []
        total_area = 0.0

        for idx, space in enumerate(project.get("spaces", []), start=1):
            area = float(space.get("area_m2", 0.0))
            total_area += area
            rows.append({
                "nr": idx,
                "floor": space.get("floor", ""),
                "name": space.get("name", ""),
                "function": space.get("function", ""),
                "area_m2": area,
                "width_m": space.get("width_m", 0.0),
                "length_m": space.get("length_m", 0.0),
                "notes": space.get("notes", "")
            })

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "rows": rows,
            "total_area_m2": round(total_area, 2),
            "space_count": len(rows),
            "status": "ok"
        }
