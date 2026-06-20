from baoees.project_analyzer.main import ProjectAnalyzer
from baoees.aaie.main import AAIEEngine
from baoees.variant_engine.main import VariantEngine
from baoees.digital_twin.main import DigitalTwin
from baoees.workflow_engine.main import WorkflowEngine
from baoees.stee.main import STEEEngine


class BAOEESCore:

    def __init__(self):
        print("BAOEES Core gestart")

        self.project_analyzer = ProjectAnalyzer()
        self.aaie = AAIEEngine()
        self.variant = VariantEngine()
        self.digital_twin = DigitalTwin()
        self.workflow = WorkflowEngine()
        self.stee = STEEEngine()

    def start_projectanalyse(self):

        print("\n=== START PROJECTANALYSE ===\n")

        project_result = self.project_analyzer.analyze(
            project_name="Plutostraat met BAOEES V3",
            project_description="Vrijstaande woning met fundering, constructie, geotechniek en SketchUp-integratie.",
            location="Plutostraat, Paramaribo",
            country="Suriname",
            project_type="Bouw"
        )

        print("Project Analyzer resultaat:")
        print(project_result)
        print("")

        aaie_result = self.aaie.infer_missing_parameters(project_result)

        print("AAIE resultaat:")
        print(aaie_result)
        print("")

        self.aaie.run()
        self.variant.run()
        self.digital_twin.run()
        self.workflow.run()
        self.stee.run()

        print("\n=== PROJECTANALYSE GEREED ===")


if __name__ == "__main__":
    core = BAOEESCore()
    core.start_projectanalyse()