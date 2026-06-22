from datetime import datetime


class SustainabilityEngine:

    def __init__(self):
        self.sustainability_result = {}

    def analyze_sustainability(
        self,
        project_result=None,
        aaie_result=None,
        drainage_result=None,
        aerius_result=None,
        asset_result=None,
        quantity_result=None,
        cost_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        drainage_result = drainage_result or {}
        aerius_result = aerius_result or {}
        asset_result = asset_result or {}
        quantity_result = quantity_result or {}
        cost_result = cost_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result)

        sustainability_scan = self.build_sustainability_scan(
            project_result=project_result,
            quantity_result=quantity_result
        )

        climate_adaptation = self.build_climate_adaptation(
            drainage_result=drainage_result,
            project_result=project_result
        )

        water_strategy = self.build_water_strategy(drainage_result)
        material_impact = self.build_material_impact(quantity_result)
        energy_indication = self.build_energy_indication(project_result, aaie_result)
        circularity = self.build_circularity_strategy(quantity_result)
        co2_attention_points = self.build_co2_attention_points(aerius_result, quantity_result)
        lifecycle_sustainability = self.build_lifecycle_sustainability(asset_result)
        sustainability_score = self.build_sustainability_score(
            climate_adaptation=climate_adaptation,
            material_impact=material_impact,
            energy_indication=energy_indication,
            circularity=circularity
        )

        self.sustainability_result = {
            "engine": "SustainabilityEngine",
            "version": "1.0",
            "status": "SUSTAINABILITY_ANALYSIS_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept duurzaamheid en klimaatadaptatie",
            "project_basis": project_basis,
            "sustainability_scan": sustainability_scan,
            "climate_adaptation": climate_adaptation,
            "water_strategy": water_strategy,
            "material_impact": material_impact,
            "energy_indication": energy_indication,
            "circularity": circularity,
            "co2_attention_points": co2_attention_points,
            "lifecycle_sustainability": lifecycle_sustainability,
            "sustainability_score": sustainability_score,
            "warnings": self.build_warnings(drainage_result, validation_result),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Sustainability Engine v1.0 maakt een conceptuele duurzaamheids- "
                "en klimaatadaptatiescan. Voor formele beoordeling zijn projectspecifieke "
                "energiegegevens, materiaaldata, MPG-/LCA-berekeningen, waternormen en "
                "lokale klimaatdata noodzakelijk."
            )
        }

        return self.sustainability_result

    def build_project_basis(self, project_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "sustainability_phase": "concept ontwerp, uitvoering en beheer",
            "status": "CONCEPT"
        }

    def build_sustainability_scan(self, project_result, quantity_result):
        gross_floor_area = quantity_result.get("project_basis", {}).get("gross_floor_area_m2", 0)

        return {
            "status": "DUURZAAMHEIDSSCAN_CONCEPT",
            "gross_floor_area_m2": gross_floor_area,
            "themes": [
                "energie",
                "water",
                "materiaalgebruik",
                "circulariteit",
                "klimaatadaptatie",
                "CO2 en emissies",
                "beheer en onderhoud"
            ],
            "project_opportunities": [
                "toepassen van energiezuinige installaties",
                "beperken van verhard oppervlak",
                "hemelwater lokaal bergen of infiltreren",
                "gebruik van herbruikbare of lage-impact materialen",
                "onderhoudsvriendelijk detailleren",
                "Digital Twin inzetten voor beheer en monitoring"
            ]
        }

    def build_climate_adaptation(self, drainage_result, project_result):
        storage = drainage_result.get("storage_and_infiltration", {})
        required_storage = storage.get("required_storage_m3", 0)

        return {
            "status": "KLIMAATADAPTATIE_CONCEPT",
            "themes": [
                {
                    "theme": "wateroverlast",
                    "measure": "hemelwaterberging, infiltratie of vertraagde afvoer",
                    "current_basis": f"benodigde berging indicatief: {required_storage} m3"
                },
                {
                    "theme": "hittestress",
                    "measure": "groen oppervlak, schaduw, lichte verharding en beperkte verharding",
                    "current_basis": "conceptueel te beoordelen op terreinontwerp"
                },
                {
                    "theme": "droogte",
                    "measure": "water vasthouden waar mogelijk en groen robuust ontwerpen",
                    "current_basis": "nader uitwerken met landschaps-/waterontwerp"
                },
                {
                    "theme": "extreme neerslag",
                    "measure": "overlooproutes en noodafvoer opnemen",
                    "current_basis": "koppeling met Drainage & Sewerage Engine"
                }
            ]
        }

    def build_water_strategy(self, drainage_result):
        hwa_status = drainage_result.get("status", "onbekend")
        storage = drainage_result.get("storage_and_infiltration", {})

        return {
            "status": "WATERSTRATEGIE_CONCEPT",
            "linked_drainage_status": hwa_status,
            "required_storage_m3": storage.get("required_storage_m3", 0),
            "strategy": [
                "hemelwater zo veel mogelijk scheiden van vuilwater",
                "water lokaal bergen waar mogelijk",
                "infiltratie toepassen indien bodem en grondwater dit toelaten",
                "noodoverloop en afstromingsroutes controleren",
                "riolering en waterhuishouding koppelen aan beheerplan"
            ]
        }

    def build_material_impact(self, quantity_result):
        concrete_m3 = 0
        reinforcement_kg = 0
        steel_kg = 0
        timber_m3 = 0

        foundations = quantity_result.get("foundations", {})
        concrete = quantity_result.get("concrete_structure", {})
        steel_timber = quantity_result.get("steel_and_timber", {})

        concrete_m3 += foundations.get("strip_concrete_m3", 0)
        concrete_m3 += foundations.get("foundation_beam_concrete_m3", 0)
        concrete_m3 += foundations.get("pile_concrete_m3", 0)
        concrete_m3 += concrete.get("total_superstructure_concrete_m3", 0)

        reinforcement_kg += foundations.get("foundation_reinforcement_kg", 0)
        reinforcement_kg += concrete.get("superstructure_reinforcement_kg", 0)

        steel_kg += steel_timber.get("indicative_structural_steel_kg", 0)
        timber_m3 += steel_timber.get("roof_timber_m3", 0)

        return {
            "status": "MATERIAALIMPACT_INDICATIEF",
            "main_materials": {
                "concrete_m3": round(concrete_m3, 2),
                "reinforcement_kg": round(reinforcement_kg, 1),
                "structural_steel_kg": round(steel_kg, 1),
                "timber_m3": round(timber_m3, 2)
            },
            "improvement_options": [
                "betonvolume optimaliseren",
                "lage-CO2 betonmengsels onderzoeken",
                "wapening en staal optimaliseren",
                "houtconstructie waar mogelijk toepassen",
                "materiaalverlies tijdens uitvoering beperken",
                "hergebruik en demontabel bouwen onderzoeken"
            ]
        }

    def build_energy_indication(self, project_result, aaie_result):
        project_type = project_result.get("project_type", "Bouw")
        gross_floor_area = aaie_result.get("gross_floor_area_m2", 200)

        try:
            gross_floor_area = float(gross_floor_area)
        except ValueError:
            gross_floor_area = 200

        indicative_energy_kwh_year = gross_floor_area * 45

        return {
            "status": "ENERGIE_INDICATIE_CONCEPT",
            "project_type": project_type,
            "gross_floor_area_m2": gross_floor_area,
            "indicative_energy_demand_kwh_year": round(indicative_energy_kwh_year, 1),
            "measures": [
                "goede isolatie en kierdichting",
                "energiezuinige installaties",
                "LED-verlichting",
                "zonwering en natuurlijke ventilatie onderzoeken",
                "PV-panelen onderzoeken",
                "energieprestatie later projectspecifiek berekenen"
            ]
        }

    def build_circularity_strategy(self, quantity_result):
        return {
            "status": "CIRCULARITEIT_CONCEPT",
            "principles": [
                "materiaalgebruik beperken",
                "losmaakbaar en onderhoudsvriendelijk detailleren",
                "herbruikbare materialen overwegen",
                "afvalstromen tijdens bouw scheiden",
                "revisie- en materiaalinformatie opnemen in Digital Twin",
                "onderdelen registreren in assetregister"
            ],
            "linked_quantity_status": quantity_result.get("status", "onbekend")
        }

    def build_co2_attention_points(self, aerius_result, quantity_result):
        return {
            "status": "CO2_AANDACHTSPUNTEN_CONCEPT",
            "linked_aerius_status": aerius_result.get("status", "onbekend"),
            "attention_points": [
                "transportbewegingen beperken",
                "materieel elektrisch of emissiearm onderzoeken",
                "materiaalhoeveelheden optimaliseren",
                "beton en staal als grootste CO2-aandachtspunten controleren",
                "bouwlogistiek combineren waar mogelijk",
                "CO2-berekening later koppelen aan LCA/MPG-module"
            ]
        }

    def build_lifecycle_sustainability(self, asset_result):
        return {
            "status": "LIFECYCLE_DUURZAAMHEID_CONCEPT",
            "linked_asset_status": asset_result.get("status", "onbekend"),
            "measures": [
                "onderhoudsplan gebruiken om levensduur te verlengen",
                "periodieke inspecties vastleggen",
                "garanties en certificaten borgen",
                "beheerlogboek koppelen aan Digital Twin",
                "onderhoudskosten en vervangingen monitoren",
                "duurzame vervanging van onderdelen stimuleren"
            ]
        }

    def build_sustainability_score(
        self,
        climate_adaptation,
        material_impact,
        energy_indication,
        circularity
    ):
        score = 70

        if climate_adaptation.get("status") == "KLIMAATADAPTATIE_CONCEPT":
            score += 5

        if material_impact.get("status") == "MATERIAALIMPACT_INDICATIEF":
            score += 5

        if energy_indication.get("status") == "ENERGIE_INDICATIE_CONCEPT":
            score += 5

        if circularity.get("status") == "CIRCULARITEIT_CONCEPT":
            score += 5

        if score > 100:
            score = 100

        return {
            "status": "DUURZAAMHEIDSSCORE_CONCEPT",
            "score": score,
            "label": self.score_label(score)
        }

    def score_label(self, score):
        if score >= 85:
            return "GOED"
        if score >= 70:
            return "VOLDOENDE_CONCEPT"
        if score >= 55:
            return "AANDACHT_NODIG"
        return "ONVOLDOENDE_CONCEPT"

    def build_warnings(self, drainage_result, validation_result):
        warnings = []

        if drainage_result.get("status") != "DRAINAGE_SEWERAGE_DESIGN_GEREED":
            warnings.append("Water- en klimaatadaptatiescan is beperkt omdat drainageontwerp niet volledig gereed is.")

        qa_decision = validation_result.get("go_no_go_advice", {}).get("decision")
        if qa_decision not in ["GO", "GO_MET_AANDACHTSPUNTEN", None]:
            warnings.append("QA/QC geeft aandachtspunten die duurzaamheidsscore kunnen beïnvloeden.")

        if not warnings:
            warnings.append("Geen kritieke duurzaamheidswaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "DUURZAAMHEIDSADVIES_CONCEPT",
            "advice": (
                "Gebruik deze analyse als eerste duurzaamheids- en klimaatscan. "
                "Werk deze later uit met projectspecifieke energie-, materiaal-, water- "
                "en CO2-berekeningen."
            ),
            "next_steps": [
                "energieprestatie projectspecifiek berekenen",
                "materiaalimpact / LCA toevoegen",
                "MPG of vergelijkbare milieuprestatie toevoegen",
                "waterberging en infiltratie definitief toetsen",
                "klimaatadaptieve maatregelen op tekening zetten",
                "duurzaamheidsmaatregelen koppelen aan kostenraming",
                "beheerfase koppelen aan Digital Twin"
            ]
        }

    def get_sustainability_result(self):
        return self.sustainability_result

    def run(self):
        print("Sustainability / Climate Engine actief")