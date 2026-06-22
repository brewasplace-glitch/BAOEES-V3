from datetime import datetime


class SpecificationEngine:

    def __init__(self):
        self.specification_result = {}

    def generate_specification(
        self,
        project_result=None,
        aaie_result=None,
        geo_result=None,
        structural_result=None,
        drainage_result=None,
        traffic_parking_result=None,
        quantity_result=None,
        drawing_result=None,
        cad_result=None,
        validation_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        drainage_result = drainage_result or {}
        traffic_parking_result = traffic_parking_result or {}
        quantity_result = quantity_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}
        validation_result = validation_result or {}

        project_basis = self.build_project_basis(project_result, aaie_result)

        chapters = [
            self.build_general_chapter(project_basis),
            self.build_earthworks_chapter(quantity_result),
            self.build_foundation_chapter(geo_result, quantity_result),
            self.build_structural_chapter(structural_result, quantity_result),
            self.build_drainage_chapter(drainage_result, quantity_result),
            self.build_siteworks_chapter(traffic_parking_result, quantity_result),
            self.build_drawings_chapter(drawing_result, cad_result),
            self.build_quality_chapter(validation_result),
            self.build_delivery_chapter()
        ]

        execution_requirements = self.build_execution_requirements(
            geo_result=geo_result,
            structural_result=structural_result,
            drainage_result=drainage_result,
            validation_result=validation_result
        )

        tender_notes = self.build_tender_notes(quantity_result, validation_result)

        self.specification_result = {
            "engine": "SpecificationEngine",
            "version": "1.0",
            "status": "SPECIFICATION_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "concept bestek en werkbeschrijving",
            "project_basis": project_basis,
            "chapters": chapters,
            "execution_requirements": execution_requirements,
            "tender_notes": tender_notes,
            "warnings": self.build_warnings(
                quantity_result=quantity_result,
                validation_result=validation_result
            ),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Specification Engine v1.0 maakt een concept-bestek. "
                "Voor aanbesteding of uitvoering moet het bestek worden gecontroleerd "
                "door een deskundige en worden aangevuld met projectspecifieke normen, "
                "details, contractvoorwaarden en definitieve tekeningen."
            )
        }

        return self.specification_result

    def build_project_basis(self, project_result, aaie_result):
        return {
            "project_name": project_result.get("project_name", "Onbekend project"),
            "project_type": project_result.get("project_type", "Bouw"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "description": project_result.get("project_description", ""),
            "contract_type": "concept traditioneel bestek / werkomschrijving",
            "status": "CONCEPT"
        }

    def build_general_chapter(self, project_basis):
        return {
            "chapter": "00",
            "title": "Algemene bepalingen",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "00.01",
                    "title": "Projectomschrijving",
                    "description": project_basis["description"],
                    "requirement": "Werk uitvoeren conform definitieve tekeningen, berekeningen en vergunningstukken."
                },
                {
                    "code": "00.02",
                    "title": "Uitgangspunten",
                    "description": "Alle maatvoering, peilen en projectgrenzen controleren vóór uitvoering.",
                    "requirement": "Afwijkingen direct melden aan opdrachtgever/adviseur."
                },
                {
                    "code": "00.03",
                    "title": "Veiligheid en omgeving",
                    "description": "Werkterrein veilig inrichten en hinder voor omgeving beperken.",
                    "requirement": "Voldoen aan geldende veiligheids- en uitvoeringsvoorschriften."
                }
            ]
        }

    def build_earthworks_chapter(self, quantity_result):
        earthworks = quantity_result.get("earthworks", {})

        return {
            "chapter": "10",
            "title": "Grondwerk",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "10.01",
                    "title": "Ontgraving",
                    "quantity": earthworks.get("excavation_volume_m3", 0),
                    "unit": "m3",
                    "description": "Ontgraven tot het vereiste aanlegniveau van fundering en leidingen.",
                    "requirement": "Ontgravingsdieptes controleren met peilmaatvoering en grondslag."
                },
                {
                    "code": "10.02",
                    "title": "Aanvullen en verdichten",
                    "quantity": earthworks.get("backfill_volume_m3", 0),
                    "unit": "m3",
                    "description": "Aanvullen met geschikt materiaal en laagsgewijs verdichten.",
                    "requirement": "Verdichting en materiaalkeuze afstemmen op fundering en terreinverharding."
                },
                {
                    "code": "10.03",
                    "title": "Afvoeren overtollige grond",
                    "quantity": earthworks.get("soil_disposal_volume_m3", 0),
                    "unit": "m3",
                    "description": "Afvoeren van overtollige of ongeschikte grond.",
                    "requirement": "Grondstromen registreren volgens lokale regels."
                }
            ]
        }

    def build_foundation_chapter(self, geo_result, quantity_result):
        foundations = quantity_result.get("foundations", {})
        selected_foundation = foundations.get(
            "recommended_foundation_type",
            geo_result.get("recommended_foundation", {}).get("selected_foundation_type", "onbekend")
        )

        return {
            "chapter": "20",
            "title": "Fundering",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "20.01",
                    "title": "Funderingstype",
                    "description": f"Indicatief funderingstype: {selected_foundation}.",
                    "requirement": "Definitief funderingsontwerp controleren met geotechnisch onderzoek."
                },
                {
                    "code": "20.02",
                    "title": "Strokenfundering / funderingsbalken",
                    "quantity": round(
                        foundations.get("strip_concrete_m3", 0)
                        + foundations.get("foundation_beam_concrete_m3", 0),
                        2
                    ),
                    "unit": "m3 beton",
                    "description": "Aanbrengen betonfundering conform definitieve funderingstekening.",
                    "requirement": "Betonkwaliteit, wapening en dekking volgens constructieve berekening."
                },
                {
                    "code": "20.03",
                    "title": "Wapening fundering",
                    "quantity": foundations.get("foundation_reinforcement_kg", 0),
                    "unit": "kg",
                    "description": "Leveren en aanbrengen wapening fundering.",
                    "requirement": "Wapeningsschema en details moeten vóór uitvoering definitief zijn."
                }
            ]
        }

    def build_structural_chapter(self, structural_result, quantity_result):
        concrete = quantity_result.get("concrete_structure", {})
        steel_timber = quantity_result.get("steel_and_timber", {})

        return {
            "chapter": "30",
            "title": "Constructie",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "30.01",
                    "title": "Betonconstructie bovenbouw",
                    "quantity": concrete.get("total_superstructure_concrete_m3", 0),
                    "unit": "m3 beton",
                    "description": "Vloeren, balken en kolommen conform constructief ontwerp.",
                    "requirement": "Definitieve constructieberekening en wapeningstekeningen vereist."
                },
                {
                    "code": "30.02",
                    "title": "Wapening bovenbouw",
                    "quantity": concrete.get("superstructure_reinforcement_kg", 0),
                    "unit": "kg",
                    "description": "Wapening voor vloeren, balken en kolommen.",
                    "requirement": "Uitvoeren volgens definitieve wapeningsstaat."
                },
                {
                    "code": "30.03",
                    "title": "Staalconstructie indicatief",
                    "quantity": steel_timber.get("indicative_structural_steel_kg", 0),
                    "unit": "kg",
                    "description": "Constructiestaal indien van toepassing.",
                    "requirement": "Profielen, verbindingen en conservering definitief uitwerken."
                },
                {
                    "code": "30.04",
                    "title": "Houtconstructie dak",
                    "quantity": steel_timber.get("roof_timber_m3", 0),
                    "unit": "m3",
                    "description": "Dakregels/gordingen en aanvullende houtconstructie.",
                    "requirement": "Afmetingen controleren op overspanning, belasting en doorbuiging."
                }
            ]
        }

    def build_drainage_chapter(self, drainage_result, quantity_result):
        drainage_quantities = quantity_result.get("drainage_and_sewerage", {})

        return {
            "chapter": "40",
            "title": "Riolering en afwatering",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "40.01",
                    "title": "HWA-leiding",
                    "quantity": drainage_quantities.get("hwa_pipe_length_m", 0),
                    "unit": "m",
                    "description": "Hemelwaterafvoerleiding aanbrengen.",
                    "requirement": "Diameter, afschot en aansluitpunt definitief controleren."
                },
                {
                    "code": "40.02",
                    "title": "DWA-leiding",
                    "quantity": drainage_quantities.get("dwa_pipe_length_m", 0),
                    "unit": "m",
                    "description": "Vuilwaterafvoerleiding aanbrengen.",
                    "requirement": "Aansluiten op gemeentelijk riool of lokale voorziening."
                },
                {
                    "code": "40.03",
                    "title": "Putten, kolken en inspectievoorzieningen",
                    "quantity": drainage_quantities.get("inspection_chambers", 0),
                    "unit": "st",
                    "description": "Inspectieputten en afwateringsvoorzieningen plaatsen.",
                    "requirement": "Posities vastleggen op rioleringstekening."
                },
                {
                    "code": "40.04",
                    "title": "Berging / infiltratie",
                    "quantity": drainage_quantities.get("infiltration_or_storage_m3", 0),
                    "unit": "m3",
                    "description": "Hemelwaterberging of infiltratievoorziening realiseren.",
                    "requirement": "Dimensionering afstemmen op lokale waternormen."
                }
            ]
        }

    def build_siteworks_chapter(self, traffic_parking_result, quantity_result):
        siteworks = quantity_result.get("siteworks", {})

        return {
            "chapter": "50",
            "title": "Terrein, verkeer en parkeren",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "50.01",
                    "title": "Terreinverharding",
                    "quantity": siteworks.get("general_paving_m2", 0),
                    "unit": "m2",
                    "description": "Aanbrengen terreinverharding en loop-/rijzones.",
                    "requirement": "Opbouw en afwatering afstemmen op gebruik en belasting."
                },
                {
                    "code": "50.02",
                    "title": "Parkeervoorzieningen",
                    "quantity": siteworks.get("parking_required_spaces", 0),
                    "unit": "pp",
                    "description": "Parkeerplaatsen indicatief volgens parkeeranalyse.",
                    "requirement": "Parkeerbalans en fysieke parkeerinventarisatie controleren."
                },
                {
                    "code": "50.03",
                    "title": "Markering en bebording",
                    "quantity": siteworks.get("site_marking_m", 0),
                    "unit": "m",
                    "description": "Markering, routing en bebording voor terrein en parkeren.",
                    "requirement": "Afstemmen op verkeerskundig advies en vergunning."
                }
            ]
        }

    def build_drawings_chapter(self, drawing_result, cad_result):
        return {
            "chapter": "60",
            "title": "Tekeningen en CAD/BIM",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "60.01",
                    "title": "Tekeningenregister",
                    "description": "Tekeningen conform Drawing Export Engine.",
                    "requirement": "Tekeningen maatvast, schaalvast en definitief controleren vóór uitvoering."
                },
                {
                    "code": "60.02",
                    "title": "CAD/DXF-bestanden",
                    "description": "CAD/DXF-export conform CAD Export Engine.",
                    "requirement": "DXF-lagen, geometrie en maatvoering controleren."
                },
                {
                    "code": "60.03",
                    "title": "Revisiegegevens",
                    "description": "Wijzigingen en revisies vastleggen.",
                    "requirement": "Laatste revisie is leidend voor uitvoering."
                }
            ]
        }

    def build_quality_chapter(self, validation_result):
        quality_score = validation_result.get("quality_score", {})
        go_no_go = validation_result.get("go_no_go_advice", {})

        return {
            "chapter": "70",
            "title": "Kwaliteit, controle en oplevering",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "70.01",
                    "title": "QA/QC-controle",
                    "description": f"Projectkwaliteitsscore: {quality_score.get('score', 'onbekend')}.",
                    "requirement": f"GO/NO-GO advies: {go_no_go.get('decision', 'onbekend')}."
                },
                {
                    "code": "70.02",
                    "title": "Controleplicht",
                    "description": "Alle output is conceptueel tot definitieve controle.",
                    "requirement": "Definitieve stukken laten controleren door bevoegde deskundigen."
                },
                {
                    "code": "70.03",
                    "title": "Oplevering",
                    "description": "Opleveren met revisietekeningen, rapporten en bewijsstukken.",
                    "requirement": "Projectdossier compleet maken inclusief bronnen en revisies."
                }
            ]
        }

    def build_delivery_chapter(self):
        return {
            "chapter": "80",
            "title": "Projectdossier en overdracht",
            "status": "CONCEPT",
            "items": [
                {
                    "code": "80.01",
                    "title": "Projectdossier",
                    "description": "Overdracht van rapporten, tekeningen, berekeningen, bronvermelding en exportbestanden.",
                    "requirement": "Dossier compleet en traceerbaar opleveren."
                },
                {
                    "code": "80.02",
                    "title": "Digital Twin",
                    "description": "Digital Twin bevat projectdata, objecten en engine-resultaten.",
                    "requirement": "Digital Twin actualiseren bij revisies."
                }
            ]
        }

    def build_execution_requirements(
        self,
        geo_result,
        structural_result,
        drainage_result,
        validation_result
    ):
        return {
            "status": "UITVOERINGSEISEN_CONCEPT",
            "requirements": [
                "controleer alle maatvoering op locatie",
                "controleer funderingsadvies met definitief grondonderzoek",
                "controleer constructie met definitieve berekeningen",
                "controleer riolering en afwatering met lokale aansluitvoorwaarden",
                "controleer vergunningvoorwaarden vóór start uitvoering",
                "werk volgens laatste revisie van tekeningen en rapporten",
                "leg afwijkingen en meerwerk schriftelijk vast"
            ],
            "geo_status": geo_result.get("status"),
            "structural_status": structural_result.get("status"),
            "drainage_status": drainage_result.get("status"),
            "validation_status": validation_result.get("status")
        }

    def build_tender_notes(self, quantity_result, validation_result):
        return {
            "status": "AANBESTEDINGSNOTITIES_CONCEPT",
            "notes": [
                "hoeveelheden zijn indicatief en moeten worden gecontroleerd",
                "inschrijver controleert tekeningen, maatvoering en uitvoerbaarheid",
                "stelposten opnemen voor onzekerheden in fundering, riolering en terrein",
                "prijsaanbieding baseren op definitieve hoeveelhedenstaat",
                "risico’s uit QA/QC-controle opnemen in aanbestedingsvragen"
            ],
            "quantity_status": quantity_result.get("status"),
            "validation_decision": validation_result.get("go_no_go_advice", {}).get("decision")
        }

    def build_warnings(self, quantity_result, validation_result):
        warnings = []

        quantity_warnings = quantity_result.get("warnings", [])
        warnings.extend(quantity_warnings)

        go_no_go = validation_result.get("go_no_go_advice", {}).get("decision", "")

        if go_no_go not in ["GO", "GO_MET_AANDACHTSPUNTEN", ""]:
            warnings.append("QA/QC geeft aan dat projectoutput eerst moet worden hersteld vóór formeel bestek.")

        if not warnings:
            warnings.append("Geen kritieke bestekwaarschuwingen op basis van deze conceptversie.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "BESTEK_ADVIES_CONCEPT",
            "advice": (
                "Gebruik dit concept-bestek als basis voor verdere aanbestedingsvoorbereiding. "
                "Koppel het bestek later aan definitieve tekeningen, hoeveelhedenstaat, berekeningen en contractvoorwaarden."
            ),
            "next_steps": [
                "bestekposten koppelen aan hoeveelhedenstaat",
                "technische eisen projectspecifiek maken",
                "normen en uitvoeringsvoorwaarden toevoegen",
                "aanbestedingsvorm bepalen",
                "contractvoorwaarden toevoegen",
                "definitief bestek laten controleren"
            ]
        }

    def get_specification_result(self):
        return self.specification_result

    def run(self):
        print("Specification / Bestek Engine actief")