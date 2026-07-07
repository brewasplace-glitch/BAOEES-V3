from datetime import datetime


class DimensioningEngine:
    MODULE_ID = "architectural.dimensioning"
    VERSION = "1.1.0"

    def run(self, floorplan):
        dimensions = []

        for floor, rooms in floorplan.get("floors", {}).items():
            total_width = sum(float(room.get("width_m", 0.0)) for room in rooms)
            max_depth = max([float(room.get("length_m", 0.0)) for room in rooms] or [0.0])

            dimensions.append({
                "floor": floor,
                "type": "overall_width",
                "value_m": round(total_width, 2)
            })
            dimensions.append({
                "floor": floor,
                "type": "overall_depth",
                "value_m": round(max_depth, 2)
            })

            for room in rooms:
                dimensions.append({
                    "floor": floor,
                    "type": "room_dimension",
                    "space": room.get("space", ""),
                    "width_m": room.get("width_m", 0.0),
                    "length_m": room.get("length_m", 0.0)
                })

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "dimensions": dimensions,
            "status": "ok"
        }
