from pathlib import Path

ROOT = Path(__file__).resolve().parent

ENGINE_CLASSES = {
    "aaie": "AAIE",
    "stee": "STEE",
    "digital_twin": "DigitalTwin",
    "workflow_engine": "WorkflowEngine",
    "variant_engine": "VariantEngine",
    "geo_engine": "GeoEngine",
    "structural_engine": "StructuralEngine",
    "permit_engine": "PermitEngine",
    "reporting_engine": "ReportingEngine",
    "parking_engine": "ParkingEngine",
    "drainage_engine": "DrainageEngine",
    "aerius_engine": "AeriusEngine",
    "participation_engine": "ParticipationEngine",
    "learning_engine": "LearningEngine",
    "qa_qc_engine": "QAQCEngine",
}

MAIN_TEMPLATES = {
    'aaie': 'class AAIE:\n    def infer_missing_parameters(self, project=None):\n        return {\n            "status": "COMPLEET",\n            "message": "Ontbrekende gegevens aangevuld met aannames.",\n            "parameter_status": "AANNAME"\n        }\n\n    def generate_groundwater_level(self):\n        return {\n            "groundwater_level": -0.50,\n            "unit": "m t.o.v. P",\n            "status": "AANNAME"\n        }\n\n    def compare_foundations(self):\n        return {\n            "foundation_types": ["strokenfundering", "paalfundering"],\n            "status": "TE_VERGELIJKEN"\n        }\n',
    'stee': 'class STEE:\n    def register_source(self, source, purpose="projectanalyse"):\n        return {\n            "source": source,\n            "purpose": purpose,\n            "status": "GEREGISTREERD"\n        }\n',
    'digital_twin': 'class DigitalTwin:\n    def create(self, project=None):\n        return {\n            "digital_twin": True,\n            "status": "CONCEPT",\n            "project": project or {}\n        }\n',
    'variant_engine': 'class VariantEngine:\n    def generate(self):\n        return [\n            {"code": "A", "name": "Laagste kosten"},\n            {"code": "B", "name": "Hoogste vergunningkans"},\n            {"code": "C", "name": "Duurzaamste oplossing"},\n            {"code": "D", "name": "Hoogste opbrengst"},\n            {"code": "E", "name": "Beste ruimtelijke kwaliteit"}\n        ]\n',
    'workflow_engine': 'from baoees.aaie.main import AAIE\nfrom baoees.variant_engine.main import VariantEngine\nfrom baoees.digital_twin.main import DigitalTwin\n\nclass WorkflowEngine:\n    def start_projectanalyse(self, project=None):\n        return {\n            "status": "PROJECTANALYSE_GESTART",\n            "aaie": AAIE().infer_missing_parameters(project),\n            "variants": VariantEngine().generate(),\n            "digital_twin": DigitalTwin().create(project),\n            "next_steps": [\n                "GeoTwin",\n                "Structural Twin",\n                "MEP Twin",\n                "Parking",\n                "Drainage",\n                "AERIUS",\n                "Permit",\n                "Reporting",\n                "QA/QC"\n            ]\n        }\n',
}

CONFIG_TEMPLATES = {
    'aaie': 'GROUNDWATER_DEFAULT = -0.50\nFOUNDATION_TYPES = ["strokenfundering", "paalfundering"]\n',
    'stee': 'SOURCE_FOLDER = "Bronvermelding_van_dit_project"\n',
    'digital_twin': 'TWIN_STATUS = "CONCEPT"\n',
    'variant_engine': 'VARIANT_COUNT = 5\n',
    'workflow_engine': 'WORKFLOW_NAME = "START PROJECTANALYSE"\n',
}

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def main():
    baoees = ROOT / "baoees"
    baoees.mkdir(exist_ok=True)
    write(baoees / "__init__.py", "# BAOEES V3 package\n")

    for folder, class_name in ENGINE_CLASSES.items():
        engine_dir = baoees / folder
        engine_dir.mkdir(parents=True, exist_ok=True)

        main_content = MAIN_TEMPLATES.get(folder)
        if main_content is None:
            main_content = (
                "class " + class_name + ":\n"
                "    def run(self, project=None):\n"
                "        return {\n"
                f'            "engine": "{folder}",\n'
                '            "status": "READY",\n'
                '            "project": project or {}\n'
                "        }\n"
            )

        config_content = CONFIG_TEMPLATES.get(folder, f'ENGINE_NAME = "{folder}"\n')

        write(engine_dir / "main.py", main_content)
        write(engine_dir / "config.py", config_content)
        write(engine_dir / "__init__.py", f"from .main import {class_name}\n")

    ui = ROOT / "ui"
    for folder in ["dashboard", "project_wizard", "digital_twin_viewer", "reports"]:
        d = ui / folder
        d.mkdir(parents=True, exist_ok=True)
        write(d / "README.md", f"# BAOEES V3 UI - {folder}\n")

    print("KLAAR: BAOEES V3 engine framework aangemaakt.")
    print("Aangemaakt: __init__.py, main.py en config.py in alle engine-mappen.")
    print("Commit daarna met: feat: initialize BAOEES V3 engine framework")

if __name__ == "__main__":
    main()
