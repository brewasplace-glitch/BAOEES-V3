"""
BAOEES Permit Engine v1.0

Doel:
- vergunningstrategie voorbereiden
- BOPA / ETFAL / ruimtelijke onderbouwing structureren
- benodigde vergunningonderdelen bepalen
- koppelen aan Digital Twin en STEE
"""


class PermitEngine:

    def __init__(self):
        self.permit_result = {}

    def prepare_permit_strategy(
        self,
        project_result=None,
        aaie_result=None,
        geo_result=None,
        structural_result=None,
        variant_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        variant_result = variant_result or {}

        self.permit_result = {
            "engine": "PermitEngine",
            "status": "VERGUNNINGSTRATEGIE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Onbekend"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "permit_route": {
                "main_route": "Omgevingsvergunning / BOPA / ETFAL",
                "status": "VOORLOPIG",
                "note": "Definitieve route moet worden bevestigd op basis van locatie, planregels en bevoegd gezag."
            },
            "required_documents": self.get_required_documents(),
            "required_studies": self.get_required_studies(project_result),
            "spatial_assessment": self.create_spatial_assessment(project_result),
            "risk_assessment": self.create_risk_assessment(
                geo_result=geo_result,
                structural_result=structural_result
            ),
            "variant_permit_notes": self.assess_variants_for_permit(variant_result),
            "next_steps": [
                "controleer omgevingsplan / bestemmingsplan",
                "controleer bouwregels en gebruiksregels",
                "controleer participatieplicht",
                "controleer stikstof/AERIUS noodzaak",
                "controleer parkeren en verkeer",
                "controleer waterhuishouding en riolering",
                "stel ruimtelijke onderbouwing / ETFAL / BOPA op",
                "stel definitieve indieningsstukken samen"
            ]
        }

        return self.permit_result

    def get_required_documents(self):
        return [
            {
                "document": "projectomschrijving",
                "status": "VEREIST",
                "purpose": "basis voor vergunningaanvraag"
            },
            {
                "document": "situatietekening",
                "status": "VEREIST",
                "purpose": "ligging project en omgeving"
            },
            {
                "document": "plattegronden bestaand en nieuw",
                "status": "VEREIST",
                "purpose": "bouwkundige beoordeling"
            },
            {
                "document": "geveltekeningen",
                "status": "VEREIST",
                "purpose": "welstand / ruimtelijke beoordeling"
            },
            {
                "document": "doorsneden",
                "status": "VEREIST",
                "purpose": "hoogtes, constructie en ruimtelijke inpassing"
            },
            {
                "document": "constructieve uitgangspunten",
                "status": "VEREIST",
                "purpose": "constructieve veiligheid"
            },
            {
                "document": "ruimtelijke onderbouwing / ETFAL / BOPA",
                "status": "VEREIST",
                "purpose": "motivering evenwichtige toedeling van functies aan locaties"
            }
        ]

    def get_required_studies(self, project_result=None):
        return [
            {
                "study": "parkeren en verkeer",
                "status": "TE_CONTROLEREN",
                "purpose": "parkeerbalans, verkeersgeneratie en parkeerdruk"
            },
            {
                "study": "AERIUS / stikstof",
                "status": "TE_CONTROLEREN",
                "purpose": "effect op Natura 2000-gebieden"
            },
            {
                "study": "water en riolering",
                "status": "TE_CONTROLEREN",
                "purpose": "hemelwater, vuilwater, infiltratie en berging"
            },
            {
                "study": "geluid",
                "status": "TE_CONTROLEREN",
                "purpose": "milieuzonering en woon-/leefklimaat"
            },
            {
                "study": "bodem / geotechniek",
                "status": "TE_CONTROLEREN",
                "purpose": "bodemkwaliteit, draagkracht en fundering"
            },
            {
                "study": "participatie",
                "status": "TE_CONTROLEREN",
                "purpose": "omgeving betrekken en verslaglegging"
            }
        ]

    def create_spatial_assessment(self, project_result=None):
        return {
            "status": "CONCEPT",
            "chapters": [
                "aanleiding en doel",
                "projectlocatie",
                "bestaande situatie",
                "nieuwe situatie",
                "planologische toets",
                "ruimtelijke inpassing",
                "verkeer en parkeren",
                "water en riolering",
                "milieu en stikstof",
                "participatie",
                "uitvoerbaarheid",
                "conclusie ETFAL / BOPA"
            ],
            "conclusion": "Conceptmatig voorbereiden; definitieve beoordeling volgt na controle van lokale regels en projectgegevens."
        }

    def create_risk_assessment(self, geo_result=None, structural_result=None):
        return {
            "status": "CONCEPT",
            "risks": [
                {
                    "risk": "onvoldoende geotechnische gegevens",
                    "level": "MIDDEL",
                    "mitigation": "sondering, boring of open geo-data koppelen"
                },
                {
                    "risk": "funderingskeuze nog voorlopig",
                    "level": "MIDDEL",
                    "mitigation": "strokenfundering en paalfundering constructief en geotechnisch vergelijken"
                },
                {
                    "risk": "AERIUS/stikstof nog niet beoordeeld",
                    "level": "TE_CONTROLEREN",
                    "mitigation": "AERIUS-module uitvoeren"
                },
                {
                    "risk": "parkeren/verkeer nog niet onderbouwd",
                    "level": "TE_CONTROLEREN",
                    "mitigation": "parkeerbalans en verkeersanalyse uitvoeren"
                }
            ]
        }

    def assess_variants_for_permit(self, variant_result=None):
        variant_result = variant_result or {}
        variants = variant_result.get("variants", [])

        notes = []

        for variant in variants:
            notes.append({
                "variant": variant.get("variant"),
                "name": variant.get("name"),
                "permit_note": self.get_variant_permit_note(variant)
            })

        return notes

    def get_variant_permit_note(self, variant):
        name = variant.get("name", "")

        if name == "Hoogste vergunningkans":
            return "Deze variant krijgt vergunningstechnisch prioriteit."
        if name == "Laagste kosten":
            return "Controleer of kostenoptimalisatie niet ten koste gaat van ruimtelijke kwaliteit."
        if name == "Duurzaamste":
            return "Positief voor klimaat, water en milieumotivering."
        if name == "Hoogste opbrengst":
            return "Controleer ruimtelijke aanvaardbaarheid en mogelijke intensivering."
        if name == "Beste ruimtelijke kwaliteit":
            return "Sterk voor ruimtelijke onderbouwing en welstand."

        return "Vergunningstechnisch nader beoordelen."

    def get_permit_result(self):
        return self.permit_result

    def run(self):
        print("Permit Engine actief")