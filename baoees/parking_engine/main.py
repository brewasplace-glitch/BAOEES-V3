class ParkingEngine:
    def run(self, project=None):
        return {
            "engine": "parking_engine",
            "status": "READY",
            "project": project or {}
        }
