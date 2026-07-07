from datetime import datetime


class FacadeGeneratorEngine:
    MODULE_ID = "architectural.facade_generator"
    VERSION = "1.1.0"

    def run(self, project, floorplan):
        facades = []

        for floor_name, rooms in floorplan.get("floors", {}).items():
            total_width = sum(float(room.get("width_m", 0.0)) for room in rooms)
            max_depth = max([float(room.get("length_m", 0.0)) for room in rooms] or [0.0])

            facades.append({
                "floor": floor_name,
                "facade": "voor",
                "width_m": round(total_width, 2),
                "height_m": 3.2,
                "openings": self._generate_openings(rooms, "voor")
            })
            facades.append({
                "floor": floor_name,
                "facade": "achter",
                "width_m": round(total_width, 2),
                "height_m": 3.2,
                "openings": self._generate_openings(rooms, "achter")
            })
            facades.append({
                "floor": floor_name,
                "facade": "links",
                "width_m": round(max_depth, 2),
                "height_m": 3.2,
                "openings": []
            })
            facades.append({
                "floor": floor_name,
                "facade": "rechts",
                "width_m": round(max_depth, 2),
                "height_m": 3.2,
                "openings": []
            })

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "facades": facades,
            "status": "ok"
        }

    def _generate_openings(self, rooms, side):
        openings = []
        x = 1.0
        for room in rooms:
            openings.append({
                "room": room.get("space", ""),
                "type": "window",
                "x_m": round(x, 2),
                "sill_height_m": 0.9,
                "width_m": 1.2,
                "height_m": 1.4
            })
            x += 2.5
        return openings
