from datetime import datetime


class ConstructionExecutionEngine:

    def __init__(self):
        self.execution_result = {}

    def prepare_execution_plan(
        self,
        project_result=None,
        planning_result=None,
        contract_result=None,
        specification_result=None,
        quantity_result=None,
        geo_result=None,
        structural_result=None,
        drainage_result=None,
        traffic_parking_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        planning_result = planning_result or {}
        contract_result = contract_result or {}
        specification_result = specification_result or {}
        quantity_result = quantity_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        drainage_result = drainage_result or {}
        traffic_parking_result = traffic_parking_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result)

        execution_phasing = self.build_execution_phasing(
            planning_result=planning_result,
            contract_result=contract_result
        )

        site_setup = self.build_site_setup(
            project_result=project_result,
            traffic_parking_result=traffic_parking_result
        )

        resources = self.build_resources(quantity_result)
        safety_plan = self.build_safety_plan(geo_result, structural_result, drainage_result)
        quality_controls = self.build_quality_controls(specification_result, validation_result)
        inspection_moments = self.build_inspection_moments()
        delivery_points = self.build_delivery_points(contract_result)
        execution_risks = self.build_execution_risks(
            geo_result=geo_result,
            structural_result=structural_result,
            drainage_result=drainage_result,
            validation_result=validation_result
        )

        self.execution_result = {
            "engine": "ConstructionExecutionEngine",
            "version": "1.0",
            "status": "EXECUTION_PLAN_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept uitvoerings- en bouwplaatsplan",
            "project_basis": project_basis,
            "execution_phasing": execution_phasing,
            "site_setup": site_setup,
            "resources": resources,
            "safety_plan": safety_plan,
            "quality_controls": quality_controls,
            "inspection_moments": inspection_moments,
            "delivery_points": delivery_points,
            "execution_risks": execution_risks,
            "warnings": self.build_warnings(validation_result, contract_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Construction Execution Engine v1.0 maakt een concept-uitvoeringsplan. "
                "Voor werkelijke uitvoering moeten bouwplaatsinrichting, veiligheid, planning, "
                "vergunningen, werkmethoden en uitvoeringsrisico’s door aannemer en deskundigen "
                "definitief worden gecontroleerd."
            )
        }

        return self.execution_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "execution_phase": "concept werkvoorbereiding",
            "status": "CONCEPT"
        }

    def build_execution_phasing(self, planning_result, contract_result):
        return {
            "status": "UITVOERINGSFASERING_CONCEPT",
            "linked_planning_status": planning_result.get("status", "onbekend"),
            "linked_contract_status": contract_result.get("status", "onbekend"),
            "phases": [
                {
                    "phase": "Fase 0",
                    "title": "Voorbereiding en mobilisatie",
                    "activities": [
                        "contractstukken controleren",
                        "werkplanning definitief maken",
                        "bouwplaatsinrichting voorbereiden",
                        "veiligheidsplan controleren",
                        "materialen en materieel reserveren"
                    ]
                },
                {
                    "phase": "Fase 1",
                    "title": "Uitzetten en grondwerk",
                    "activities": [
                        "peilen en assen uitzetten",
                        "bouwput en funderingssleuven ontgraven",
                        "grondslag controleren",
                        "overtollige grond afvoeren of hergebruiken"
                    ]
                },
                {
                    "phase": "Fase 2",
                    "title": "Fundering",
                    "activities": [
                        "werkvloer of voorbereidingslaag aanbrengen",
                        "bekisting en wapening plaatsen",
                        "controle wapening en maatvoering",
                        "beton storten fundering",
                        "nabehandeling beton"
                    ]
                },
                {
                    "phase": "Fase 3",
                    "title": "Constructie / ruwbouw",
                    "activities": [
                        "kolommen, balken en vloeren uitvoeren",
                        "staal- of houtconstructie plaatsen",
                        "constructieve controles uitvoeren",
                        "dakconstructie voorbereiden"
                    ]
                },
                {
                    "phase": "Fase 4",
                    "title": "Riolering, afwatering en terrein",
                    "activities": [
                        "DWA en HWA leidingen aanbrengen",
                        "putten en inspectievoorzieningen plaatsen",
                        "terreinprofilering uitvoeren",
                        "verharding en parkeerzones aanbrengen"
                    ]
                },
                {
                    "phase": "Fase 5",
                    "title": "Controle, herstel en oplevering",
                    "activities": [
                        "kwaliteitscontroles uitvoeren",
                        "opleverpunten registreren",
                        "revisiegegevens verzamelen",
                        "projectdossier afronden",
                        "Digital Twin bijwerken"
                    ]
                }
            ]
        }

    def build_site_setup(self, project_result, traffic_parking_result):
        parking_status = traffic_parking_result.get("status", "onbekend")
        parking_spaces = traffic_parking_result.get("parking_demand", {}).get("rounded_required_spaces", 0)

        return {
            "status": "BOUWPLAATSINRICHTING_CONCEPT",
            "location": project_result.get("location", "Onbekend"),
            "site_elements": [
                "bouwhek / afzetting",
                "toegangspoort en logistieke route",
                "materiaalopslag",
                "afvalinzamelpunt",
                "tijdelijke stroom- en watervoorziening",
                "veiligheidszone rond werkzaamheden",
                "tijdelijke parkeer- en laad-/loszone"
            ],
            "traffic_and_parking_status": parking_status,
            "indicative_parking_spaces_required": parking_spaces,
            "site_logistics_notes": [
                "houd aan- en afvoerroute vrij",
                "voorkom blokkeren van openbare weg",
                "stem transportmomenten af op omgeving",
                "registreer bouwplaatsrisico’s dagelijks"
            ]
        }

    def build_resources(self, quantity_result):
        boq_items = quantity_result.get("boq_summary", {}).get("main_quantities", [])

        return {
            "status": "MATERIEEL_PERSONEEL_CONCEPT",
            "linked_boq_items": boq_items,
            "indicative_personnel": [
                {
                    "role": "uitvoerder / voorman",
                    "quantity": 1
                },
                {
                    "role": "grondwerker",
                    "quantity": 2
                },
                {
                    "role": "beton-/wapeningsploeg",
                    "quantity": 3
                },
                {
                    "role": "timmerman / bekister",
                    "quantity": 2
                },
                {
                    "role": "installatie / riolering ploeg",
                    "quantity": 2
                }
            ],
            "indicative_equipment": [
                "minigraver of mobiele kraan",
                "verdichtingsplaat / stamper",
                "betonpomp of betonmixer",
                "handgereedschap bekisting en wapening",
                "meetapparatuur",
                "veiligheidsmiddelen"
            ]
        }

    def build_safety_plan(self, geo_result, structural_result, drainage_result):
        groundwater = geo_result.get("groundwater", {}).get("groundwater_level_m", "onbekend")

        return {
            "status": "VEILIGHEIDSPLAN_CONCEPT",
            "main_safety_topics": [
                "bouwput en sleuven beveiligen tegen instorten",
                "werken met hijsmiddelen en materieel controleren",
                "persoonlijke beschermingsmiddelen verplicht stellen",
                "valgevaar en randen beveiligen",
                "elektra en tijdelijke voorzieningen veilig aanleggen",
                "werkplek dagelijks controleren"
            ],
            "groundwater_level_m": groundwater,
            "geo_status": geo_result.get("status", "onbekend"),
            "structural_status": structural_result.get("status", "onbekend"),
            "drainage_status": drainage_result.get("status", "onbekend")
        }

    def build_quality_controls(self, specification_result, validation_result):
        return {
            "status": "KWALITEITSCONTROLES_CONCEPT",
            "linked_specification_status": specification_result.get("status", "onbekend"),
            "linked_validation_status": validation_result.get("status", "onbekend"),
            "controls": [
                {
                    "control": "maatvoering en peilen",
                    "moment": "voor start grondwerk"
                },
                {
                    "control": "grondslagcontrole",
                    "moment": "na ontgraving"
                },
                {
                    "control": "wapeningscontrole fundering",
                    "moment": "voor betonstort"
                },
                {
                    "control": "betonkwaliteit en stortregistratie",
                    "moment": "tijdens betonwerk"
                },
                {
                    "control": "constructieve verbindingen",
                    "moment": "tijdens ruwbouw"
                },
                {
                    "control": "riolering afschot en aansluitingen",
                    "moment": "voor aanvullen sleuven"
                },
                {
                    "control": "oplevercontrole en herstelpunten",
                    "moment": "voor eindoplevering"
                }
            ]
        }

    def build_inspection_moments(self):
        return {
            "status": "KEURINGSMOMENTEN_CONCEPT",
            "inspections": [
                "start werk / bouwplaatsinrichting",
                "uitzetten assen en peilen",
                "grondslag fundering",
                "wapening fundering",
                "betonstort fundering",
                "constructiecontrole ruwbouw",
                "riolering en afwatering vóór aanvullen",
                "terreinverharding vóór oplevering",
                "eindoplevering"
            ]
        }

    def build_delivery_points(self, contract_result):
        return {
            "status": "OPLEVERPUNTEN_CONCEPT",
            "linked_contract_status": contract_result.get("status", "onbekend"),
            "delivery_requirements": [
                "werk gereed volgens contract en laatste revisietekeningen",
                "opleverlijst met openstaande punten",
                "revisietekeningen en maatvoeringsgegevens",
                "foto’s en bewijsstukken van controles",
                "garanties en certificaten",
                "bijgewerkte Digital Twin",
                "compleet projectdossier"
            ]
        }

    def build_execution_risks(self, geo_result, structural_result, drainage_result, validation_result):
        risks = []

        qa_risks = validation_result.get("risk_check", {}).get("risks", [])
        risks.extend(qa_risks)

        if geo_result.get("status") != "GEOTECHNISCHE_ANALYSE_GEREED":
            risks.append("Geotechnische analyse is niet volledig gereed.")

        if structural_result.get("status") != "CONSTRUCTIEVE_ANALYSE_GEREED":
            risks.append("Constructieve analyse is niet volledig gereed.")

        if drainage_result.get("status") != "DRAINAGE_SEWERAGE_DESIGN_GEREED":
            risks.append("Riolering en afwatering moeten vóór uitvoering definitief worden gecontroleerd.")

        if not risks:
            risks.append("Geen kritieke uitvoeringsrisico’s op basis van deze conceptversie.")

        return {
            "status": "UITVOERINGSRISICO_ANALYSE_CONCEPT",
            "risks": risks,
            "mitigation": [
                "voor start uitvoering definitieve tekeningen controleren",
                "grondslag en waterstand op locatie controleren",
                "constructieve details en wapening laten goedkeuren",
                "rioleringstracé en aansluitpunten controleren",
                "dagelijkse bouwplaatscontrole uitvoeren",
                "afwijkingen vastleggen in logboek"
            ]
        }

    def build_warnings(self, validation_result, contract_result):
        warnings = []

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        contract_status = contract_result.get("status")

        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aan dat herstel nodig is vóór uitvoering.")

        if contract_status != "CONTRACT_PACKAGE_GEREED":
            warnings.append("Contractpakket is nog niet volledig gereed.")

        if not warnings:
            warnings.append("Geen kritieke uitvoeringswaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "UITVOERINGSADVIES_CONCEPT",
            "advice": (
                "Gebruik dit uitvoeringsplan als basis voor werkvoorbereiding. "
                "Laat de aannemer vóór start uitvoering planning, bouwplaatsinrichting, "
                "veiligheid, werkmethoden en keuringsmomenten definitief maken."
            ),
            "next_steps": [
                "definitieve werkplanning opstellen",
                "bouwplaatsinrichting uitwerken",
                "veiligheidsplan definitief maken",
                "keurings- en controleplan vaststellen",
                "materiaal- en materieelplanning maken",
                "startwerkbespreking houden",
                "bouwlogboek openen"
            ]
        }

    def get_execution_result(self):
        return self.execution_result

    def run(self):
        print("Construction Execution Engine actief")