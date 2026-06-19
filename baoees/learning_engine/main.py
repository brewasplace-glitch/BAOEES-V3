class LearningEngine:
    def run(self, project=None):
        return {
            "engine": "learning_engine",
            "status": "READY",
            "project": project or {}
        }
