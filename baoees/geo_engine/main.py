class GeoEngine:
    def run(self, project=None):
        return {
            "engine": "geo_engine",
            "status": "READY",
            "project": project or {}
        }
