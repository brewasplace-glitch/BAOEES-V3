"""
BAOEES Workflow Engine v1.0

Doel:
- centrale projectworkflow aansturen
- benodigde engines in logische volgorde activeren
"""


class WorkflowEngine:

    def create_workflow(self, project_result=None, aaie_result=None):
        return {
            "engine": "WorkflowEngine",
            "status": "WORKFLOW_AANGEMAAKT",
            "workflow_steps": [
                "Project Analyzer",
                "AAIE",
                "STEE",
                "Digital Twin",
                "Variant Engine",
                "Geo Engine",
                "Structural Engine",
                "Permit Engine",
                "Reporting Engine"
            ]
        }

    def run(self):
        print("Workflow Engine actief")