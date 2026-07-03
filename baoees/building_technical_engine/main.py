from datetime import datetime


class BuildingTechnicalEngine:

    def __init__(self):
        self.building_technical_result = {}

    def create_building_technical_analysis(
        self,
        project_result=None,
        geo_result=None,
        structural_result=None,
        permit_result=None,
        digital_twin_result=None,
        assumptions_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        permit_result = permit_result or {}
        digital_twin_result = digital_twin_result or {}
        assumptions_result = assumptions_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))
        project_type = self.detect_project_type(project_result)
        building_function = self.detect_building_function(project_result)

        building_profile = self.build_building_profile(
            project_result=project_result,
            project_type=project_type,
            building_function=building_function
        )

        load_profile = self.build_load_profile(
            building_profile=building_profile
        )

        structural_system = self.build_structural_system(
            project_result=project_result,
            structural_result=structural_result,
            building_profile=building_profile
        )

        foundation_profile = self.build_foundation_profile(
            project_result=project_result,
            geo_result=geo_result,
            assumptions_result=assumptions_result
        )

        drawing_requirements = self.build_drawing_requirements()

        self.building_technical_result = {
            "engine": "BuildingTechnicalEngine",
            "version": "1.0",
            "status": "BUILDING_TECHNICAL_ANALYSIS_GEREED",
            "calculation_level": "bouwtechnische basisanalyse",
            "project_id": project_id,
            "project_name": project_name,
            "project_type": project_type,
            "building_function": building_function,
            "building_profile": building_profile,
            "load_profile": load_profile,
            "structural_system": structural_system,
            "foundation_profile": foundation_profile,
            "drawing_requirements": drawing_requirements,
            "report_sections": self.build_report_sections(
                project_name=project_name,
                project_id=project_id,
                structural_system=structural_system,
                foundation_profile=foundation_profile,
                load_profile=load_profile
            ),
            "qa_qc_checks": self.build_qa_qc_checks(
                building_profile=building_profile,
                load_profile=load_profile,
                structural_system=structural_system,
                foundation_profile=foundation_profile
            ),
            "digital_twin_update": {
                "digital_twin_node": "building_technical",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {}
            },
            "warnings": self.build_warnings(
                building_profile=building_profile,
                load_profile=load_profile,
                foundation_profile=foundation_profile
            ),
            "recommendation": self.build_recommendation(
                project_type=project_type,
                building_function=building_function,
                foundation_profile=foundation_profile
            ),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        self.building_technical_result["digital_twin_update"]["data"] = {
            "building_profile": building_profile,
            "load_profile": load_profile,
            "structural_system": structural_system,
            "foundation_profile": foundation_profile
        }

        return self.building_technical_result

    def detect_project_type(self, project_result):
        text = self.combined_project_text(project_result)

        if "moskee" in text or "gebed" in text or "religie" in text:
            return "maatschappelijk_religieus_gebouw"

        if "woning" in text or "huis" in text:
            return "woningbouw"

        if "kantoor" in text:
            return "utiliteitsbouw_kantoor"

        if "waterfront" in text or "masterplan" in text or "gebied" in text:
            return "gebiedsontwikkeling"

        if "industrie" in text or "loods" in text or "bedrijfshal" in text:
            return "industriebouw"

        return project_result.get("project_type", "algemeen_bouwproject")

    def detect_building_function(self, project_result):
        text = self.combined_project_text(project_result)

        if "moskee" in text:
            return "gebedsfunctie_met_bijeenkomstfunctie"

        if "woning" in text or "huis" in text:
            return "woonfunctie"

        if "kantoor" in text:
            return "kantoorfunctie"

        if "auditorium" in text:
            return "bijeenkomstfunctie"

        if "waterfront" in text or "masterplan" in text:
            return "stedelijke_gebiedsfunctie"

        return project_result.get("building_function", "algemene_bouwfunctie")

    def build_building_profile(self, project_result, project_type, building_function):
        floors = self.safe_number(
            project_result.get("number_of_floors", project_result.get("floors", 1)),
            default_value=1
        )

        gross_floor_area_m2 = self.safe_number(
            project_result.get("gross_floor_area_m2", project_result.get("area_m2", 0)),
            default_value=0
        )

        extension_area_m2 = self.safe_number(
            project_result.get("extension_area_m2", project_result.get("uitbreiding_m2", 0)),
            default_value=0
        )

        return {
            "project_type": project_type,
            "building_function": building_function,
            "number_of_floors": floors,
            "gross_floor_area_m2": gross_floor_area_m2,
            "extension_area_m2": extension_area_m2,
            "roof_type": project_result.get("roof_type", "nog_te_bepalen"),
            "main_material": project_result.get("main_material", "nog_te_bepalen"),
            "building_complexity": self.estimate_building_complexity(
                project_type=project_type,
                floors=floors,
                gross_floor_area_m2=gross_floor_area_m2
            )
        }

    def build_load_profile(self, building_profile):
        building_function = building_profile.get("building_function", "")

        imposed_load_category = "nader_te_bepalen"
        imposed_load_note = "Gebruiksbelasting moet projectspecifiek worden vastgesteld."

        if building_function == "woonfunctie":
            imposed_load_category = "woonfunctie"
            imposed_load_note = "Indicatief: woonfunctie met normale vloerbelasting."

        elif building_function == "kantoorfunctie":
            imposed_load_category = "kantoorfunctie"
            imposed_load_note = "Indicatief: kantoorfunctie met hogere veranderlijke belasting."

        elif "bijeenkomst" in building_function or "gebed" in building_function:
            imposed_load_category = "bijeenkomstfunctie"
            imposed_load_note = "Indicatief: bijeenkomst-/gebedsfunctie met hoge bezettingsgraad."

        return {
            "load_level": "basis",
            "imposed_load_category": imposed_load_category,
            "imposed_load_note": imposed_load_note,
            "dead_load_note": "Eigen gewicht bepalen op basis van vloer-, wand-, dak- en gevelopbouw.",
            "wind_load_note": "Windbelasting projectspecifiek bepalen op basis van locatie en gebouwhoogte.",
            "roof_load_note": "Dakbelasting bepalen op basis van daktype, dakopbouw en onderhoudsbelasting.",
            "load_combinations_note": "Belastingcombinaties worden in een volgende engine verdiept."
        }

    def build_structural_system(self, project_result, structural_result, building_profile):
        preferred_system = project_result.get(
            "preferred_structural_system",
            structural_result.get("structural_system", "nog_te_bepalen")
        )

        project_type = building_profile.get("project_type", "")
        floors = building_profile.get("number_of_floors", 1)

        if preferred_system == "nog_te_bepalen":
            if project_type == "woningbouw":
                preferred_system = "traditionele_metselwerk_of_betonconstructie"
            elif project_type == "maatschappelijk_religieus_gebouw":
                preferred_system = "staal_beton_of_gemengde_draagconstructie"
            elif floors >= 3:
                preferred_system = "beton_of_staalconstructie_met_stabiliteitskern"
            else:
                preferred_system = "gemengde_draagconstructie"

        return {
            "preferred_structural_system": preferred_system,
            "stability_system": self.estimate_stability_system(project_type, floors),
            "main_structural_elements": [
                "fundering",
                "funderingsbalken",
                "dragende wanden",
                "kolommen",
                "liggers",
                "vloeren",
                "dakconstructie"
            ],
            "next_engine_required": "StructuralCalculationEngine_v2"
        }

    def build_foundation_profile(self, project_result, geo_result, assumptions_result):
        requested_foundation = project_result.get(
            "foundation_type",
            project_result.get("preferred_foundation_type", "")
        )

        geo_foundation_advice = geo_result.get(
            "foundation_advice",
            geo_result.get("recommended_foundation_type", "")
        )

        recommended_foundation = requested_foundation or geo_foundation_advice

        if not recommended_foundation:
            recommended_foundation = "strokenfundering_of_paalfundering_nader_te_toetsen"

        return {
            "recommended_foundation_type": recommended_foundation,
            "groundwater_level": assumptions_result.get(
                "groundwater_level",
                project_result.get("groundwater_level", "P = -0,50 m")
            ),
            "foundation_depth": project_result.get(
                "foundation_depth",
                project_result.get("funderingsdiepte", "nader_te_bepalen")
            ),
            "strip_foundation_standard": {
                "strip_width_cm": 150,
                "strip_height_cm": 40,
                "foundation_beam_width_cm": 50,
                "foundation_beam_height_cm": 60,
                "note": (
                    "Standaard BEOS/BAOEES-uitgangspunt: strook 150 cm breed en 40 cm hoog "
                    "met funderingsbalk 50 x 60 cm in het hart van de strook."
                )
            },
            "foundation_checks_required": [
                "draagkracht ondergrond",
                "zetting",
                "grondwaterinvloed",
                "belastingafdracht",
                "stroken versus palen"
            ]
        }

    def build_drawing_requirements(self):
        return {
            "required_drawings": [
                "situatietekening",
                "plattegronden",
                "geveltekeningen",
                "doorsneden",
                "funderingsplan",
                "constructieve opzet",
                "dakplan"
            ],
            "drawing_quality_requirements": [
                "op schaal",
                "maatvoering",
                "noordpijl",
                "legenda",
                "peilen",
                "ruimtebenamingen",
                "bestaand en nieuw onderscheiden"
            ]
        }

    def build_report_sections(
        self,
        project_name,
        project_id,
        structural_system,
        foundation_profile,
        load_profile
    ):
        return [
            {
                "section_id": "bouwtechnische_samenvatting",
                "title": "Bouwtechnische samenvatting",
                "content": (
                    f"Voor project {project_name} ({project_id}) is een bouwtechnische "
                    "basisanalyse uitgevoerd."
                )
            },
            {
                "section_id": "constructieve_uitgangspunten",
                "title": "Constructieve uitgangspunten",
                "content": (
                    "Voorlopige draagstructuur: "
                    f"{structural_system.get('preferred_structural_system')}."
                )
            },
            {
                "section_id": "funderingsuitgangspunten",
                "title": "Funderingsuitgangspunten",
                "content": (
                    "Voorlopige fundering: "
                    f"{foundation_profile.get('recommended_foundation_type')}."
                )
            },
            {
                "section_id": "belastinguitgangspunten",
                "title": "Belastinguitgangspunten",
                "content": load_profile.get("imposed_load_note", "")
            }
        ]

    def build_qa_qc_checks(
        self,
        building_profile,
        load_profile,
        structural_system,
        foundation_profile
    ):
        return [
            {
                "check": "gebouwfunctie_bepaald",
                "status": "OK" if building_profile.get("building_function") else "AANDACHT"
            },
            {
                "check": "belastingcategorie_bepaald",
                "status": "OK" if load_profile.get("imposed_load_category") != "nader_te_bepalen" else "AANDACHT"
            },
            {
                "check": "draagstructuur_bepaald",
                "status": "OK" if structural_system.get("preferred_structural_system") else "AANDACHT"
            },
            {
                "check": "funderingstype_bepaald",
                "status": "OK" if foundation_profile.get("recommended_foundation_type") else "AANDACHT"
            }
        ]

    def build_warnings(self, building_profile, load_profile, foundation_profile):
        warnings = []

        if building_profile.get("gross_floor_area_m2", 0) == 0:
            warnings.append("BVO/oppervlakte ontbreekt nog.")

        if load_profile.get("imposed_load_category") == "nader_te_bepalen":
            warnings.append("Gebruiksbelastingcategorie moet nog projectspecifiek worden vastgesteld.")

        if foundation_profile.get("foundation_depth") == "nader_te_bepalen":
            warnings.append("Funderingsdiepte ontbreekt nog.")

        if not warnings:
            warnings.append("Geen kritieke bouwtechnische basiswaarschuwingen.")

        return warnings

    def build_recommendation(self, project_type, building_function, foundation_profile):
        return {
            "status": "BUILDING_TECHNICAL_ADVIES",
            "project_type": project_type,
            "building_function": building_function,
            "foundation_advice": foundation_profile.get("recommended_foundation_type"),
            "advice": (
                "Gebruik deze bouwtechnische basisanalyse als startpunt voor constructie, "
                "fundering, geotechniek, tekeningen en vergunningstukken."
            )
        }

    def estimate_building_complexity(self, project_type, floors, gross_floor_area_m2):
        if project_type == "gebiedsontwikkeling":
            return "hoog"

        if floors >= 3:
            return "middel_hoog"

        if gross_floor_area_m2 and gross_floor_area_m2 > 1000:
            return "middel_hoog"

        if project_type in ["maatschappelijk_religieus_gebouw", "utiliteitsbouw_kantoor"]:
            return "middel"

        return "basis"

    def estimate_stability_system(self, project_type, floors):
        if floors >= 3:
            return "stabiliteitskern_of_schijven"

        if project_type == "industriebouw":
            return "windverbanden_en_portalen"

        if project_type == "woningbouw":
            return "dragende_wanden_en_schijfwerking"

        return "wanden_kernen_of_portalen_nader_te_bepalen"

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def combined_project_text(self, project_result):
        parts = []

        for key, value in project_result.items():
            if isinstance(value, (str, int, float)):
                parts.append(str(value))

        return " ".join(parts).lower()

    def get_building_technical_result(self):
        return self.building_technical_result

    def run(self, *args, **kwargs):
        return self.create_building_technical_analysis(*args, **kwargs)