"""
BAOEES STEE v1.0
Source Traceability & Evidence Engine

Doel:
- bronnen registreren
- doel van gebruik vastleggen
- koppelen aan projectanalyse, aannames en Digital Twin
"""

from datetime import datetime


class STEEEngine:

    def __init__(self):
        self.source_register = []

    def register_source(
        self,
        source,
        purpose="projectanalyse",
        linked_object=None,
        source_type="manual",
        reliability="ONBEKEND"
    ):
        record = {
            "source": source,
            "purpose": purpose,
            "linked_object": linked_object,
            "source_type": source_type,
            "reliability": reliability,
            "status": "GEREGISTREERD",
            "registered_at": datetime.now().isoformat(timespec="seconds")
        }

        self.source_register.append(record)
        return record

    def register_project_sources(self, project_result=None, aaie_result=None):
        self.register_source(
            source="Gebruiker/projectinvoer",
            purpose="Basisgegevens projectanalyse",
            linked_object="Project Analyzer",
            source_type="project_input",
            reliability="BEVESTIGD"
        )

        self.register_source(
            source="BAOEES AAIE standaard fallback grondwaterstand P = -0,50 m",
            purpose="Aanname grondwaterstand",
            linked_object="AAIE.groundwater_level",
            source_type="system_rule",
            reliability="AANNAME"
        )

        self.register_source(
            source="BAOEES funderingsmodule - vergelijking strokenfundering en paalfundering",
            purpose="Funderingsvergelijking",
            linked_object="AAIE.foundation_comparison",
            source_type="system_rule",
            reliability="TE_VERGELIJKEN"
        )

        return {
            "engine": "STEE",
            "status": "BRONREGISTER_AANGEMAAKT",
            "source_register": self.source_register
        }

    def get_source_register(self):
        return self.source_register

    def run(self):
        print("STEE Bronregistratie actief")
