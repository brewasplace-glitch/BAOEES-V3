from datetime import datetime


class FloorplanGeneratorEngine:
    MODULE_ID = "architectural.floorplan_generator"
    VERSION = "1.0.0"

    def run(self, project, space_schedule):
        floors = {}
        x_cursor_by_floor = {}

        for row in space_schedule.get("rows", []):
            floor = row.get("floor", "begane grond")
            floors.setdefault(floor, [])
            x = x_cursor_by_floor.get(floor, 0.0)

            width = float(row.get("width_m") or 4.0)
            length = float(row.get("length_m") or 4.0)

            if width <= 0:
                width = 4.0
            if length <= 0:
                length = 4.0

            room_rect = {
                "space": row.get("name", ""),
                "function": row.get("function", ""),
                "x": round(x, 2),
                "y": 0.0,
                "width_m": round(width, 2),
                "length_m": round(length, 2),
                "area_m2": row.get("area_m2", 0.0)
            }

            floors[floor].append(room_rect)
            x_cursor_by_floor[floor] = x + width

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "drawing_type": "schematic_floorplan",
            "floors": floors,
            "exports_prepared": ["json", "pdf_next", "dxf_next", "ifc_next", "skp_next"],
            "status": "ok"
        }
