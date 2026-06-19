class PermitEngine:
    def run(self, project=None):
        return {
            "engine": "permit_engine",
            "status": "READY",
            "project": project or {}
        }
