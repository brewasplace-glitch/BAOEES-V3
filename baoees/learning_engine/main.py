from datetime import datetime


class LearningEngine:

    def __init__(self):
        self.learning_result = {}

    def analyze_project_learning(
        self,
        project_result=None,
        aaie_result=None,
        validation_result=None,
        codes_result=None,
        stee_result=None,
        digital_twin_data=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        validation_result = validation_result or {}
        codes_result = codes_result or {}
        stee_result = stee_result or {}
        digital_twin_data = digital_twin_data or {}

        project_basis = self.build_project_basis(project_result)

        assumptions_log = self.build_assumptions_log(aaie_result)
        warnings_log = self.build_warnings_log(validation_result, codes_result)
        source_learning = self.build_source_learning(stee_result)
        digital_twin_learning = self.build_digital_twin_learning(digital_twin_data)
        improvement_suggestions = self.build_improvement_suggestions(
            validation_result=validation_result,
            codes_result=codes_result
        )
        reusable_knowledge = self.build_reusable_knowledge(project_result)

        self.learning_result = {
            "engine": "LearningEngine",
            "version": "1.0",
            "status": "PROJECT_LEARNING_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept projectleren en kennisopbouw",
            "project_basis": project_basis,
            "assumptions_log": assumptions_log,
            "warnings_log": warnings_log,
            "source_learning": source_learning,
            "digital_twin_learning": digital_twin_learning,
            "improvement_suggestions": improvement_suggestions,
            "reusable_knowledge": reusable_knowledge,
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Learning Engine v1.0 maakt een conceptuele projectleeranalyse. "
                "Werkelijke autonome verbetering vereist gecontroleerde opslag, validatie, "
                "versiebeheer en menselijke goedkeuring van leerregels."
            )
        }

        return self.learning_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "learning_phase": "concept kennisopbouw",
            "status": "CONCEPT"
        }

    def build_assumptions_log(self, aaie_result):
        assumptions = []

        for key, value in aaie_result.items():
            if isinstance(value, dict):
                status = value.get("status", "")
                if status in ["AANNAME", "GEACTUALISEERD", "BEVESTIGD"]:
                    assumptions.append({
                        "parameter": key,
                        "value": value,
                        "status": status
                    })

        if not assumptions:
            assumptions.append({
                "parameter": "algemeen",
                "value": "geen expliciete aannames gevonden of aannames niet in standaardformaat",
                "status": "TE_CONTROLEREN"
            })

        return {
            "status": "AANNAMES_LOG_GEREED",
            "assumptions": assumptions
        }

    def build_warnings_log(self, validation_result, codes_result):
        warnings = []

        warnings.extend(validation_result.get("warnings", []))
        warnings.extend(codes_result.get("warnings", []))

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen geregistreerd.")

        return {
            "status": "WAARSCHUWINGEN_LOG_GEREED",
            "warnings": warnings
        }

    def build_source_learning(self, stee_result):
        sources = stee_result.get("source_register", [])

        return {
            "status": "BRONNEN_LEERLOG_GEREED",
            "source_count": len(sources),
            "source_types": list(set([source.get("source_type", "onbekend") for source in sources])),
            "lesson": "Projectbronnen moeten per discipline traceerbaar blijven."
        }

    def build_digital_twin_learning(self, digital_twin_data):
        objects = digital_twin_data.get("objects", [])
        sources = digital_twin_data.get("sources", [])

        return {
            "status": "DIGITAL_TWIN_LEERLOG_GEREED",
            "object_count": len(objects),
            "source_count": len(sources),
            "lesson": "Alle engine-resultaten moeten als object in de Digital Twin worden opgeslagen."
        }

    def build_improvement_suggestions(self, validation_result, codes_result):
        suggestions = []

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        compliance_status = codes_result.get("compliance_check", {}).get("overall_compliance_status")

        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            suggestions.append("Verbeter projectkwaliteit vóór vervolgfase.")

        if compliance_status == "CONCEPT_NOG_TE_CONTROLEREN":
            suggestions.append("Maak normen- en regelgevingstoets projectspecifieker.")

        suggestions.extend([
            "koppel aannames explicieter aan bronnen",
            "maak output per engine exporteerbaar",
            "voeg projectspecifieke invoer toe in plaats van vaste voorbeeldwaarden",
            "breid Digital Twin uit met revisiehistorie",
            "voeg automatische rapportage van leerpunten toe"
        ])

        return {
            "status": "VERBETERADVIEZEN_GEREED",
            "suggestions": suggestions
        }

    def build_reusable_knowledge(self, project_result):
        return {
            "status": "HERBRUIKBARE_KENNIS_CONCEPT",
            "knowledge_items": [
                {
                    "topic": "projecttype",
                    "value": project_result.get("project_type", "Bouw"),
                    "reuse": "gebruik als referentie voor vergelijkbare projecten"
                },
                {
                    "topic": "locatie",
                    "value": project_result.get("location", "Onbekend"),
                    "reuse": "gebruik voor regionale aannames en jurisdictie"
                },
                {
                    "topic": "workflow",
                    "value": "volledige BAOEES V3 projectketen",
                    "reuse": "standaardketen voor ontwerp tot beheer"
                }
            ]
        }

    def build_recommendation(self):
        return {
            "status": "LEERADVIES_CONCEPT",
            "advice": (
                "Gebruik deze leeranalyse om BAOEES per project te verbeteren. "
                "Bewaar aannames, waarschuwingen, bronnen, kwaliteitschecks en revisies "
                "zodat volgende projecten sneller en betrouwbaarder kunnen worden opgezet."
            ),
            "next_steps": [
                "leerpunten exporteren naar projectdossier",
                "aannames koppelen aan bronvermelding",
                "kwaliteitsscore per project bewaren",
                "herbruikbare projecttemplates maken",
                "fouten en waarschuwingen omzetten naar verbeterregels",
                "menselijke controle toevoegen voordat leerregels definitief worden"
            ]
        }

    def get_learning_result(self):
        return self.learning_result

    def run(self):
        print("Autonomous Learning / Knowledge Engine actief")