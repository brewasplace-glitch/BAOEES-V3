class StructuralEngine:
    def run(self, project=None):
        return {
            "engine": "structural_engine",
            "status": "READY",
            "project": project or {}
        }
