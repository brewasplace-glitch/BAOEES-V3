"""
BAOEES Workflow Engine v1.0

Doel:
- automatische projectworkflow samenstellen
- benodigde engines in logische volgorde zetten
- workflow koppelen aan Digital Twin
"""


class WorkflowEngine:

    def __init__(self):
        self.workflow = []

    def create_workflow(self, project_result=None, aaie_result=None, variant_result=None, stee_result=None):
        project_result = project_result or {}
        required_engines = project_result.get("required_engines", [])

        base_order = [
            "project_analyzer",
            "aaie",
            "stee",
            "variant_engine",
            "digital_twin",
            "geo_engine",
            "structural_engine",
            "parking_engine",
            "drainage_engine",
            "aerius_engine",
            "participation_engine",
            "permit_engine",
            "reporting_engine",
            "qa_qc_engine",
            "learning_engine"
        ]

        workflow_steps = []

        for engine in base_order:
            if engine in required_engines or engine in [
                "project_analyzer",
                "aaie",
                "stee",
                "variant_engine",
                "digital_twin"
            ]:
                workflow_steps.append({
                    "step": len(workflow_steps) + 1,
                    "engine": engine,
                    "status": self.determine_step_status(engine),
                    "action": self.get_engine_action(engine)
                })

        self.workflow = workflow_steps

        return {
            "engine": "WorkflowEngine",
            "status": "WORKFLOW_AANGEMAAKT",
            "workflow_step_count": len(workflow_steps),
            "workflow_steps": workflow_steps,
            "note": "Workflow automatisch samengesteld op basis van Project Analyzer en AAIE."
        }

    def determine_step_status(self, engine):
        completed_engines = [
            "project_analyzer",
            "aaie",
            "stee",
            "variant_engine",
            "digital_twin"
        ]

        if engine in completed_engines:
            return "GEREED"

        return "GEPLAND"

    def get_engine_action(self, engine):
        actions = {
            "project_analyzer": "Projecttype, locatie, ontbrekende gegevens en benodigde engines bepalen.",
            "aaie": "Ontbrekende parameters aanvullen en aannames labelen.",
            "stee": "Bronnen registreren en koppelen aan projectdata.",
            "variant_engine": "Vijf ontwerpvarianten genereren.",
            "digital_twin": "Projectdata, aannames, bronnen en objecten centraal opslaan.",
            "geo_engine": "Geotechnische uitgangspunten en grondwaterstand verwerken.",
            "structural_engine": "Constructieve analyse en funderingskeuze voorbereiden.",
            "parking_engine": "Parkeerbalans en parkeerdruk analyseren.",
            "drainage_engine": "Riolering, hemelwater en afwatering ontwerpen.",
            "aerius_engine": "Stikstof/AERIUS-analyse voorbereiden.",
            "participation_engine": "Participatieproces en verslag voorbereiden.",
            "permit_engine": "Vergunningstrategie, BOPA/ETFAL en ruimtelijke onderbouwing voorbereiden.",
            "reporting_engine": "Rapporten, bijlagen en exportbestanden genereren.",
            "qa_qc_engine": "Automatische kwaliteitscontrole uitvoeren.",
            "learning_engine": "Projectkennis opslaan voor toekomstige optimalisatie."
        }

        return actions.get(engine, "Engine uitvoeren volgens BAOEES workflow.")

    def get_workflow(self):
        return self.workflow

    def run(self):
        print("Workflow Engine actief")