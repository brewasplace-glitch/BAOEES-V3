class AeriusEngine:
    def run(self, project=None):
        return {
            "engine": "aerius_engine",
            "status": "READY",
            "project": project or {}
        }
