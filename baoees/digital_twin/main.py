"""
BAOEES Digital Twin v1.0

Doel:
- centrale projectdata opslaan
- Project Analyzer-resultaten koppelen aan AAIE-resultaten
- één digitale projectkern maken waar alle engines later op aansluiten
"""


class DigitalTwin:

    def __init__(self):
        self.project_data = {}

    def create_project_twin(self, project_result=None, aaie_result=None):
        self.project_data = {
            "digital_twin_version": "1.0",
            "status": "DIGITAL_TWIN_AANGEMAAKT",
            "project": project_result or {},
            "aaie": aaie_result or {},
            "objects": [],
            "assumptions": [],
            "sources": [],
            "reports": [],
            "drawings": [],
            "calculations": []
        }

        if aaie_result:
            assumptions = aaie_result.get("assumptions", {})
            for key, value in assumptions.items():
                self.project_data["assumptions"].append({
                    "parameter": key,
                    "value": value
                })

        return self.project_data

    def add_object(self, object_type, name, data=None):
        obj = {
            "object_type": object_type,
            "name": name,
            "data": data or {}
        }
        self.project_data.setdefault("objects", []).append(obj)
        return obj

    def add_source(self, source, purpose="projectanalyse"):
        src = {
            "source": source,
            "purpose": purpose,
            "status": "GEREGISTREERD"
        }
        self.project_data.setdefault("sources", []).append(src)
        return src

    def get_project_data(self):
        return self.project_data

    def run(self):
        print("Digital Twin actief")