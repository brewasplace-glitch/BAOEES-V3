class DrainageEngine:
    def run(self, project=None):
        return {
            "engine": "drainage_engine",
            "status": "READY",
            "project": project or {}
        }
