"""
BAOEES Project Analyzer v1.0

Doel:
- projectomschrijving lezen
- projecttype bepalen
- ontbrekende gegevens signaleren
- benodigde BAOEES-engines selecteren
"""


class ProjectAnalyzer:

    def analyze(
        self,
        project_name="Nieuw project",
        project_description="",
        location=None,
        country=None,
        project_type=None
    ):
        text = project_description.lower()

        detected_project_type = project_type or self.detect_project_type(text)

        missing_data = []

        if not location:
            missing_data.append("Projectlocatie ontbreekt")

        if not country:
            missing_data.append("Land ontbreekt")

        if not project_description:
            missing_data.append("Projectomschrijving ontbreekt")

        required_engines = self.select_required_engines(text, detected_project_type)

        return {
            "project_name": project_name,
            "project_type": detected_project_type,
            "location": location,
            "country": country,
            "missing_data": missing_data,
            "required_engines": required_engines,
            "status": "PROJECT_ANALYSE_GEREED"
        }

    def detect_project_type(self, text):
        if any(word in text for word in ["woning", "gebouw", "moskee", "fundering", "constructie"]):
            return "Bouw"

        if any(word in text for word in ["brug", "kade", "waterbouw", "civiel"]):
            return "Civiel"

        if any(word in text for word in ["weg", "parking", "parkeer", "riolering", "infra"]):
            return "Infra"

        return "Onbekend"

    def select_required_engines(self, text, project_type):
        engines = [
            "aaie",
            "stee",
            "digital_twin",
            "workflow_engine",
            "variant_engine"
        ]

        if project_type == "Bouw":
            engines.extend([
                "geo_engine",
                "structural_engine",
                "permit_engine",
                "reporting_engine"
            ])

        if "parkeren" in text or "parkeer" in text:
            engines.append("parking_engine")

        if "riolering" in text or "afwatering" in text or "hemelwater" in text:
            engines.append("drainage_engine")

        if "aerius" in text or "stikstof" in text:
            engines.append("aerius_engine")

        if "participatie" in text:
            engines.append("participation_engine")

        return engines

    def run(self):
        print("Project Analyzer actief")