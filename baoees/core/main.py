from baoees.aaie.main import AAIEEngine
from baoees.variant_engine.main import VariantEngine
from baoees.digital_twin.main import DigitalTwin
from baoees.workflow_engine.main import WorkflowEngine
from baoees.stee.main import STEEEngine


class BAOEESCore:

    def __init__(self):
        print("BAOEES Core gestart")

        self.aaie = AAIEEngine()
        self.variant = VariantEngine()
        self.digital_twin = DigitalTwin()
        self.workflow = WorkflowEngine()
        self.stee = STEEEngine()

    def start_projectanalyse(self):

        print("\n=== START PROJECTANALYSE ===\n")

        self.aaie.run()
        self.variant.run()
        self.digital_twin.run()
        self.workflow.run()
        self.stee.run()

        print("\n=== PROJECTANALYSE GEREED ===")


if __name__ == "__main__":
    core = BAOEESCore()
    core.start_projectanalyse()