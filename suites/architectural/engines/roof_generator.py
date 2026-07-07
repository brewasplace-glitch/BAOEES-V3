from datetime import datetime


class RoofGeneratorEngine:
    MODULE_ID = "architectural.roof_generator"
    VERSION = "1.1.0"

    def run(self, project, floorplan):
        footprint_width = 0.0
        footprint_depth = 0.0

        for rooms in floorplan.get("floors", {}).values():
            width = sum(float(room.get("width_m", 0.0)) for room in rooms)
            depth = max([float(room.get("length_m", 0.0)) for room in rooms] or [0.0])
            footprint_width = max(footprint_width, width)
            footprint_depth = max(footprint_depth, depth)

        roof = {
            "roof_type": "conceptueel plat dak / kap optioneel",
            "footprint_width_m": round(footprint_width, 2),
            "footprint_depth_m": round(footprint_depth, 2),
            "roof_area_m2": round(footprint_width * footprint_depth, 2),
            "drainage": "HWA nader uitwerken in MEP/riolering module",
            "notes": [
                "Dakvorm wordt later projectafhankelijk geoptimaliseerd.",
                "Voor moskeeproject kan koepel/minaret als architectonisch element worden toegevoegd."
            ]
        }

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "roof": roof,
            "status": "ok"
        }
