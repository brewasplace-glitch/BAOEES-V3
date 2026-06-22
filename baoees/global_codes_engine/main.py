from datetime import datetime


class GlobalCodesEngine:

    def __init__(self):
        self.codes_result = {}

    def analyze_codes_and_standards(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        drainage_result=None,
        traffic_parking_result=None,
        sustainability_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        drainage_result = drainage_result or {}
        traffic_parking_result = traffic_parking_result or {}
        sustainability_result = sustainability_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result)

        jurisdiction = self.determine_jurisdiction(project_result)

        codes_register = self.build_codes_register(
            project_result=project_result,
            jurisdiction=jurisdiction
        )

        discipline_matrix = self.build_discipline_matrix(
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result,
            drainage_result=drainage_result,
            traffic_parking_result=traffic_parking_result,
            sustainability_result=sustainability_result
        )

        compliance_check = self.build_compliance_check(
            codes_register=codes_register,
            validation_result=validation_result
        )

        missing_information = self.build_missing_information(
            geo_result=geo_result,
            structural_result=structural_result,
            permit_result=permit_result
        )

        self.codes_result = {
            "engine": "GlobalCodesEngine",
            "version": "1.0",
            "status": "GLOBAL_CODES_ANALYSIS_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept normen- en regelgevingstoets",
            "project_basis": project_basis,
            "jurisdiction": jurisdiction,
            "codes_register": codes_register,
            "discipline_matrix": discipline_matrix,
            "compliance_check": compliance_check,
            "missing_information": missing_information,
            "warnings": self.build_warnings(jurisdiction, validation_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Global Codes Engine v1.0 maakt een conceptueel normen- en regelgevingsregister. "
                "Voor formele toetsing moeten actuele wetgeving, lokale bouwregels, normen, "
                "vergunningseisen en projectspecifieke voorwaarden door bevoegde deskundigen worden gecontroleerd."
            )
        }

        return self.codes_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "codes_phase": "concept normen en regelgeving",
            "status": "CONCEPT"
        }

    def determine_jurisdiction(self, project_result):
        country = project_result.get("country", "").lower()
        location = project_result.get("location", "").lower()

        if "nederland" in country or "netherlands" in country or "bunschoten" in location:
            return {
                "status": "JURISDICTIE_BEPAALD",
                "country": "Nederland",
                "primary_framework": "Omgevingswet / Bbl / lokale omgevingsplanregels",
                "language": "Nederlands",
                "authority_level": "gemeente / omgevingsdienst / waterschap"
            }

        if "suriname" in country or "paramaribo" in location:
            return {
                "status": "JURISDICTIE_BEPAALD",
                "country": "Suriname",
                "primary_framework": "lokale bouwregelgeving Suriname / projectspecifieke vergunningseisen",
                "language": "Nederlands",
                "authority_level": "lokale overheid / vergunningverlenende instantie"
            }

        return {
            "status": "JURISDICTIE_ONZEKER",
            "country": project_result.get("country", "Onbekend"),
            "primary_framework": "nader te bepalen",
            "language": "nader te bepalen",
            "authority_level": "nader te bepalen"
        }

    def build_codes_register(self, project_result, jurisdiction):
        country = jurisdiction.get("country", "Onbekend")

        general_codes = [
            {
                "code_area": "algemeen bouwen",
                "framework": jurisdiction.get("primary_framework"),
                "status": "TE_CONTROLEREN"
            },
            {
                "code_area": "vergunningen",
                "framework": "lokale vergunningseisen en ruimtelijke regels",
                "status": "TE_CONTROLEREN"
            },
            {
                "code_area": "veiligheid",
                "framework": "bouwplaatsveiligheid en arbeidsveiligheid",
                "status": "TE_CONTROLEREN"
            }
        ]

        if country == "Nederland":
            country_specific = [
                {
                    "code_area": "omgevingsrecht",
                    "framework": "Omgevingswet, Bbl, omgevingsplan, Regels op de kaart",
                    "status": "TE_CONTROLEREN"
                },
                {
                    "code_area": "constructie",
                    "framework": "Eurocodes / NEN-EN normen / nationale bijlagen",
                    "status": "TE_CONTROLEREN"
                },
                {
                    "code_area": "parkeren",
                    "framework": "gemeentelijke parkeernota / CROW-richtlijnen",
                    "status": "TE_CONTROLEREN"
                },
                {
                    "code_area": "stikstof",
                    "framework": "AERIUS Calculator / Natura 2000 toetsing",
                    "status": "TE_CONTROLEREN"
                }
            ]
        elif country == "Suriname":
            country_specific = [
                {
                    "code_area": "lokale bouwvergunning",
                    "framework": "Surinaamse bouw- en vergunningseisen",
                    "status": "TE_CONTROLEREN"
                },
                {
                    "code_area": "constructie",
                    "framework": "toe te passen constructieve normenset projectspecifiek vastleggen",
                    "status": "TE_CONTROLEREN"
                },
                {
                    "code_area": "water en terrein",
                    "framework": "lokale waterhuishouding en aansluitingseisen",
                    "status": "TE_CONTROLEREN"
                }
            ]
        else:
            country_specific = [
                {
                    "code_area": "lokale regelgeving",
                    "framework": "nader te bepalen",
                    "status": "TE_CONTROLEREN"
                }
            ]

        return {
            "status": "NORMENREGISTER_CONCEPT",
            "country": country,
            "codes": general_codes + country_specific
        }

    def build_discipline_matrix(
        self,
        geo_result,
        structural_result,
        permit_result,
        drainage_result,
        traffic_parking_result,
        sustainability_result
    ):
        return {
            "status": "DISCIPLINE_TOETSINGSMATRIX_CONCEPT",
            "disciplines": [
                {
                    "discipline": "geotechniek",
                    "linked_engine_status": geo_result.get("status", "onbekend"),
                    "required_code_check": "grondonderzoek, draagkracht, zetting, grondwater en funderingsadvies"
                },
                {
                    "discipline": "constructie",
                    "linked_engine_status": structural_result.get("status", "onbekend"),
                    "required_code_check": "belastingen, stabiliteit, sterkte, bruikbaarheid en detaillering"
                },
                {
                    "discipline": "vergunning",
                    "linked_engine_status": permit_result.get("status", "onbekend"),
                    "required_code_check": "ruimtelijke regels, vergunningplicht, procedure en indieningsvereisten"
                },
                {
                    "discipline": "riolering en afwatering",
                    "linked_engine_status": drainage_result.get("status", "onbekend"),
                    "required_code_check": "HWA, DWA, berging, infiltratie, aansluitvoorwaarden en lozing"
                },
                {
                    "discipline": "verkeer en parkeren",
                    "linked_engine_status": traffic_parking_result.get("status", "onbekend"),
                    "required_code_check": "parkeerbalans, verkeersveiligheid, bereikbaarheid en lokale parkeernorm"
                },
                {
                    "discipline": "duurzaamheid en klimaat",
                    "linked_engine_status": sustainability_result.get("status", "onbekend"),
                    "required_code_check": "energie, water, materiaalimpact, circulariteit en klimaatadaptatie"
                }
            ]
        }

    def build_compliance_check(self, codes_register, validation_result):
        code_items = codes_register.get("codes", [])
        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision", "onbekend")

        open_checks = []

        for item in code_items:
            open_checks.append({
                "code_area": item.get("code_area"),
                "framework": item.get("framework"),
                "check_status": "OPEN",
                "responsible": "nader te bepalen"
            })

        return {
            "status": "COMPLIANCE_CHECK_CONCEPT",
            "qa_qc_decision": qa_decision,
            "open_code_checks": open_checks,
            "overall_compliance_status": "CONCEPT_NOG_TE_CONTROLEREN"
        }

    def build_missing_information(self, geo_result, structural_result, permit_result):
        missing = []

        if geo_result.get("status") != "GEOTECHNISCHE_ANALYSE_GEREED":
            missing.append("definitieve geotechnische analyse / grondonderzoek")

        if structural_result.get("status") != "CONSTRUCTIEVE_ANALYSE_GEREED":
            missing.append("definitieve constructieve berekening")

        if permit_result.get("status") != "PERMIT_STRATEGY_GEREED":
            missing.append("definitieve vergunningstrategie")

        if not missing:
            missing.append("geen kritieke ontbrekende hoofdgegevens op basis van huidige engine-statussen")

        return {
            "status": "ONTBREKENDE_INFORMATIE_GEREGISTREERD",
            "missing_items": missing
        }

    def build_warnings(self, jurisdiction, validation_result):
        warnings = []

        if jurisdiction.get("status") == "JURISDICTIE_ONZEKER":
            warnings.append("Jurisdictie is onzeker; lokale regelgeving moet handmatig worden vastgesteld.")

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aandachtspunten die normtoetsing kunnen beïnvloeden.")

        if not warnings:
            warnings.append("Geen kritieke normenwaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "NORMENADVIES_CONCEPT",
            "advice": (
                "Gebruik dit normenregister als basis voor projecttoetsing. "
                "Vul het later aan met actuele wetgeving, normversies, lokale voorschriften "
                "en projectspecifieke vergunningvoorwaarden."
            ),
            "next_steps": [
                "jurisdictie definitief bevestigen",
                "actuele normen en wetgeving koppelen",
                "vergunningvoorwaarden toevoegen",
                "constructieve normenset vastleggen",
                "lokale parkeernorm en waterregels toevoegen",
                "compliance matrix per discipline afronden",
                "QA/QC laten hercontroleren"
            ]
        }

    def get_codes_result(self):
        return self.codes_result

    def run(self):
        print("Global Codes / Standards Engine actief")