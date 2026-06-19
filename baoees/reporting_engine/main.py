class ReportingEngine:
    def run(self, project=None):
        return {
            "engine": "reporting_engine",
            "status": "READY",
            "project": project or {}
        }
