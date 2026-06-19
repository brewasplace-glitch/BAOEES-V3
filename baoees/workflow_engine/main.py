from baoees.aaie.main import AAIE
from baoees.variant_engine.main import VariantEngine
from baoees.digital_twin.main import DigitalTwin

class WorkflowEngine:
    def start_projectanalyse(self, project=None):
        return {
            "status": "PROJECTANALYSE_GESTART",
            "aaie": AAIE().infer_missing_parameters(project),
            "variants": VariantEngine().generate(),
            "digital_twin": DigitalTwin().create(project),
            "next_steps": [
                "GeoTwin",
                "Structural Twin",
                "MEP Twin",
                "Parking",
                "Drainage",
                "AERIUS",
                "Permit",
                "Reporting",
                "QA/QC"
            ]
        }
