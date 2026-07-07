from datetime import datetime


class ProgramOfRequirementsEngine:
    MODULE_ID = "architectural.program_of_requirements"
    VERSION = "1.0.0"

    def run(self, project):
        spaces = project.get("spaces", [])
        requirements = {
            "functional_requirements": [],
            "spatial_requirements": [],
            "technical_requirements": [],
            "permit_requirements": []
        }

        for space in spaces:
            requirements["spatial_requirements"].append({
                "space": space.get("name", ""),
                "function": space.get("function", ""),
                "floor": space.get("floor", ""),
                "target_area_m2": space.get("area_m2", 0.0)
            })

        requirements["technical_requirements"].extend([
            "maatvoering controleren",
            "bestaand en nieuw onderscheiden",
            "koppeling met Digital Twin voorbereiden",
            "export naar PDF/DXF/IFC/SKP voorbereiden"
        ])

        requirements["permit_requirements"].extend([
            "situatie bestaand/nieuw",
            "plattegronden bestaand/nieuw",
            "gevels bestaand/nieuw",
            "doorsneden",
            "ruimtestaat",
            "projectomschrijving"
        ])

        return {
            "module_id": self.MODULE_ID,
            "version": self.VERSION,
            "ran_at": datetime.now().isoformat(timespec="seconds"),
            "requirements": requirements,
            "status": "ok"
        }
