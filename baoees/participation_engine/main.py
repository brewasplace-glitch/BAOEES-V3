class ParticipationEngine:
    def run(self, project=None):
        return {
            "engine": "participation_engine",
            "status": "READY",
            "project": project or {}
        }
