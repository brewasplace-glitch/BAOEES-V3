class DigitalTwin:
    def create(self, project=None):
        return {
            "digital_twin": True,
            "status": "CONCEPT",
            "project": project or {}
        }

class DigitalTwin:

    def run(self):
        print("Digital Twin actief")