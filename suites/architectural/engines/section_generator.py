from datetime import datetime


class SectionGeneratorEngine:
    MODULE_ID = "architectural.section_generator"
    VERSION = "1.1.0"

    def run(self, project, floorplan):
        floor_count = len(floorplan.get("floors", {}))
        if floor_count <= 0:
            floor_count = 1

        sections = [
            {
                "section_id": "A-A",
                "description": "schematische langsdoorsnede",
                "floor_count": floor_count,
                "floor_height_m": 3.2,
                "total_height_m": round(floor_count * 3.2 + 1.2, 2),
                "roof_type": "kap/plat dak nader te bepalen",
                "elements": [
                    "fundering indicatief",
                    "vloeren",
                    "wanden",
                    "dak",
                    "maatvoering"
                ]
            },
            {
                "section_id": "B-B",
                "description": "schematische dwarsdoorsnede",
                "floor_count": floor_count,
                "floor_height_m": 3.2,
                "total_height_m": round(floor_count * 3.2 + 1.2, 2),
                "roof_type": "kap/plat dak nader te bepalen",
                "elements": [
                    "vloerpeilen",
                    "vrije hoogte",
                    "dakopbouw",
                    "gevelhoogte"
                ]
            }
        ]

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "sections": sections,
            "status": "ok"
        }
