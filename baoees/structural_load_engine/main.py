from datetime import datetime


class StructuralLoadEngine:

    def __init__(self):
        self.structural_load_result = {}

    def create_structural_load_analysis(
        self,
        project_result=None,
        building_technical_result=None,
        geo_result=None,
        structural_result=None,
        assumptions_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        building_technical_result = building_technical_result or {}
        assumptions_result = assumptions_result or {}

        building_profile = building_technical_result.get("building_profile", {})

        project_id = project_result.get(
            "project_id",
            project_result.get("id", "unknown_project")
        )

        project_name = project_result.get(
            "project_name",
            project_result.get("name", "Onbekend project")
        )

        building_function = building_technical_result.get(
            "building_function",
            building_profile.get(
                "building_function",
                project_result.get("building_function", "algemene_bouwfunctie")
            )
        )

        gross_floor_area_m2 = self.safe_number(
            project_result.get(
                "gross_floor_area_m2",
                building_profile.get("gross_floor_area_m2", 0)
            ),
            default_value=0
        )

        number_of_floors = self.safe_number(
            project_result.get(
                "number_of_floors",
                building_profile.get("number_of_floors", 1)
            ),
            default_value=1
        )

        permanent_loads = self.build_permanent_loads(
            project_result=project_result,
            gross_floor_area_m2=gross_floor_area_m2,
            number_of_floors=number_of_floors
        )

        imposed_loads = self.build_imposed_loads(
            project_result=project_result,
            building_function=building_function,
            gross_floor_area_m2=gross_floor_area_m2
        )

        roof_loads = self.build_roof_loads(
            project_result=project_result,
            building_profile=building_profile
        )

        wind_loads = self.build_wind_loads(
            project_result=project_result,
            assumptions_result=assumptions_result
        )

        foundation_load_precheck = self.build_foundation_load_precheck(
            gross_floor_area_m2=gross_floor_area_m2,
            permanent_loads=permanent_loads,
            imposed_loads=imposed_loads,
            roof_loads=roof_loads
        )

        load_combinations = self.build_load_combinations(
            permanent_loads=permanent_loads,
            imposed_loads=imposed_loads,
            roof_loads=roof_loads,
            wind_loads=wind_loads
        )

        qa_qc_checks = self.build_qa_qc_checks(
            gross_floor_area_m2=gross_floor_area_m2,
            permanent_loads=permanent_loads,
            imposed_loads=imposed_loads,
            roof_loads=roof_loads,
            wind_loads=wind_loads,
            foundation_load_precheck=foundation_load_precheck
        )

        report_sections = self.build_report_sections(
            project_name=project_name,
            project_id=project_id,
            building_function=building_function,
            permanent_loads=permanent_loads,
            imposed_loads=imposed_loads,
            load_combinations=load_combinations
        )

        self.structural_load_result = {
            "engine": "StructuralLoadEngine",
            "version": "1.0",
            "status": "STRUCTURAL_LOAD_ANALYSIS_GEREED",
            "calculation_level": "indicatieve belastinganalyse",
            "project_id": project_id,
            "project_name": project_name,
            "building_function": building_function,
            "gross_floor_area_m2": gross_floor_area_m2,
            "number_of_floors": number_of_floors,
            "permanent_loads": permanent_loads,
            "imposed_loads": imposed_loads,
            "roof_loads": roof_loads,
            "wind_loads": wind_loads,
            "foundation_load_precheck": foundation_load_precheck,
            "load_combinations": load_combinations,
            "qa_qc_checks": qa_qc_checks,
            "report_sections": report_sections,
            "digital_twin_update": {
                "digital_twin_node": "structural_loads",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "permanent_loads": permanent_loads,
                    "imposed_loads": imposed_loads,
                    "roof_loads": roof_loads,
                    "wind_loads": wind_loads,
                    "foundation_load_precheck": foundation_load_precheck,
                    "load_combinations": load_combinations
                }
            },
            "warnings": self.build_warnings(
                gross_floor_area_m2=gross_floor_area_m2,
                imposed_loads=imposed_loads,
                wind_loads=wind_loads
            ),
            "recommendation": self.build_recommendation(
                building_function=building_function,
                foundation_load_precheck=foundation_load_precheck
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Structural Load Engine v1.0 maakt een indicatieve "
                "belastinganalyse voor verdere constructieve verdieping."
            )
        }

        return self.structural_load_result

    def build_permanent_loads(
        self,
        project_result,
        gross_floor_area_m2,
        number_of_floors
    ):
        floor_dead_load = self.safe_number(
            project_result.get("floor_dead_load_kN_m2", 3.50),
            default_value=3.50
        )

        wall_dead_load = self.safe_number(
            project_result.get("wall_dead_load_kN_m2", 1.00),
            default_value=1.00
        )

        finish_dead_load = self.safe_number(
            project_result.get("finish_dead_load_kN_m2", 0.75),
            default_value=0.75
        )

        installation_dead_load = self.safe_number(
            project_result.get("installation_dead_load_kN_m2", 0.35),
            default_value=0.35
        )

        area_for_estimate = gross_floor_area_m2

        if area_for_estimate <= 0:
            area_for_estimate = 100.0

        total_dead_load_kN_m2 = (
            floor_dead_load
            + wall_dead_load
            + finish_dead_load
            + installation_dead_load
        )

        total_dead_load_kN = (
            total_dead_load_kN_m2
            * area_for_estimate
            * max(number_of_floors, 1)
        )

        return {
            "load_type": "permanent",
            "total_dead_load_kN_m2": round(total_dead_load_kN_m2, 2),
            "total_dead_load_kN": round(total_dead_load_kN, 2),
            "status": "INDICATIEF"
        }

    def build_imposed_loads(
        self,
        project_result,
        building_function,
        gross_floor_area_m2
    ):
        custom_imposed_load = project_result.get("imposed_load_kN_m2")

        if custom_imposed_load is not None:
            imposed_load = self.safe_number(custom_imposed_load, default_value=2.50)
            category = "projectspecifiek"

        elif building_function == "woonfunctie":
            imposed_load = 1.75
            category = "woonfunctie"

        elif building_function == "kantoorfunctie":
            imposed_load = 3.00
            category = "kantoorfunctie"

        elif "bijeenkomst" in building_function or "gebed" in building_function:
            imposed_load = 5.00
            category = "bijeenkomstfunctie"

        else:
            imposed_load = 2.50
            category = "algemene_bouwfunctie"

        area_for_estimate = gross_floor_area_m2

        if area_for_estimate <= 0:
            area_for_estimate = 100.0

        return {
            "load_type": "variable",
            "category": category,
            "main_imposed_load_kN_m2": round(imposed_load, 2),
            "total_imposed_load_kN": round(imposed_load * area_for_estimate, 2),
            "status": "INDICATIEF"
        }

    def build_roof_loads(self, project_result, building_profile):
        roof_type = building_profile.get(
            "roof_type",
            project_result.get("roof_type", "nog_te_bepalen")
        )

        roof_dead_load = self.safe_number(
            project_result.get("roof_dead_load_kN_m2", 0.85),
            default_value=0.85
        )

        roof_live_load = self.safe_number(
            project_result.get("roof_live_load_kN_m2", 0.75),
            default_value=0.75
        )

        return {
            "load_type": "roof",
            "roof_type": roof_type,
            "roof_dead_load_kN_m2": round(roof_dead_load, 2),
            "roof_live_load_kN_m2": round(roof_live_load, 2),
            "status": "INDICATIEF"
        }

    def build_wind_loads(self, project_result, assumptions_result):
        country = str(project_result.get("country", "")).lower()

        reference_wind_pressure = self.safe_number(
            assumptions_result.get(
                "reference_wind_pressure_kN_m2",
                project_result.get("reference_wind_pressure_kN_m2", 0.65)
            ),
            default_value=0.65
        )

        if "suriname" in country:
            reference_wind_pressure = self.safe_number(
                project_result.get("reference_wind_pressure_kN_m2", 0.85),
                default_value=0.85
            )

        return {
            "load_type": "wind",
            "reference_wind_pressure_kN_m2": round(reference_wind_pressure, 2),
            "status": "VOORLOPIG_NIET_NORMATIEF"
        }

    def build_foundation_load_precheck(
        self,
        gross_floor_area_m2,
        permanent_loads,
        imposed_loads,
        roof_loads
    ):
        area_for_estimate = gross_floor_area_m2

        if area_for_estimate <= 0:
            area_for_estimate = 100.0

        estimated_perimeter_m = (area_for_estimate ** 0.5) * 4.0

        roof_total = (
            roof_loads.get("roof_dead_load_kN_m2", 0)
            + roof_loads.get("roof_live_load_kN_m2", 0)
        ) * area_for_estimate

        total_vertical_load_kN = (
            permanent_loads.get("total_dead_load_kN", 0)
            + imposed_loads.get("total_imposed_load_kN", 0)
            + roof_total
        )

        estimated_line_load_kN_m = total_vertical_load_kN / max(
            estimated_perimeter_m,
            1
        )

        return {
            "status": "VOORCONTROLE",
            "total_vertical_load_kN": round(total_vertical_load_kN, 2),
            "estimated_line_load_kN_m": round(estimated_line_load_kN_m, 2)
        }

    def build_load_combinations(
        self,
        permanent_loads,
        imposed_loads,
        roof_loads,
        wind_loads
    ):
        g_k = permanent_loads.get("total_dead_load_kN_m2", 0)
        q_k = imposed_loads.get("main_imposed_load_kN_m2", 0)
        r_k = (
            roof_loads.get("roof_dead_load_kN_m2", 0)
            + roof_loads.get("roof_live_load_kN_m2", 0)
        )
        w_k = wind_loads.get("reference_wind_pressure_kN_m2", 0)

        return {
            "status": "COMBINATIES_VOORBEREID",
            "uls_gravity_kN_m2": round(1.35 * g_k + 1.50 * q_k, 2),
            "uls_roof_kN_m2": round(1.35 * g_k + 1.50 * r_k, 2),
            "uls_wind_kN_m2": round(1.35 * g_k + 1.50 * w_k, 2),
            "sls_characteristic_kN_m2": round(g_k + q_k, 2)
        }

    def build_report_sections(
        self,
        project_name,
        project_id,
        building_function,
        permanent_loads,
        imposed_loads,
        load_combinations
    ):
        return [
            {
                "section_id": "belastinganalyse_samenvatting",
                "title": "Belastinganalyse samenvatting",
                "content": (
                    f"Voor project {project_name} ({project_id}) is een indicatieve "
                    f"belastinganalyse opgesteld voor gebouwfunctie {building_function}."
                )
            },
            {
                "section_id": "belastingcombinaties",
                "title": "Belastingcombinaties",
                "content": (
                    "Indicatieve ULS zwaartekrachtcombinatie: "
                    f"{load_combinations.get('uls_gravity_kN_m2')} kN/m²."
                )
            }
        ]

    def build_qa_qc_checks(
        self,
        gross_floor_area_m2,
        permanent_loads,
        imposed_loads,
        roof_loads,
        wind_loads,
        foundation_load_precheck
    ):
        return [
            {
                "check": "oppervlakte_beschikbaar",
                "status": "OK" if gross_floor_area_m2 > 0 else "AANDACHT"
            },
            {
                "check": "permanente_belasting_bepaald",
                "status": "OK" if permanent_loads.get("total_dead_load_kN_m2", 0) > 0 else "AANDACHT"
            },
            {
                "check": "veranderlijke_belasting_bepaald",
                "status": "OK" if imposed_loads.get("main_imposed_load_kN_m2", 0) > 0 else "AANDACHT"
            },
            {
                "check": "dakbelasting_bepaald",
                "status": "OK" if roof_loads.get("roof_dead_load_kN_m2", 0) > 0 else "AANDACHT"
            },
            {
                "check": "windbelasting_voorlopig",
                "status": "AANDACHT"
            },
            {
                "check": "funderingsbelasting_voorcontrole",
                "status": "OK" if foundation_load_precheck.get("estimated_line_load_kN_m", 0) > 0 else "AANDACHT"
            }
        ]

    def build_warnings(
        self,
        gross_floor_area_m2,
        imposed_loads,
        wind_loads
    ):
        warnings = []

        if gross_floor_area_m2 <= 0:
            warnings.append(
                "BVO/oppervlakte ontbreekt; engine gebruikt 100 m2 als tijdelijke rekenwaarde."
            )

        if imposed_loads.get("category") == "algemene_bouwfunctie":
            warnings.append(
                "Gebouwfunctie is algemeen; veranderlijke belasting moet projectspecifiek worden gecontroleerd."
            )

        if wind_loads.get("status") == "VOORLOPIG_NIET_NORMATIEF":
            warnings.append(
                "Windbelasting is voorlopig en nog niet normatief berekend."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke waarschuwingen in de indicatieve belastinganalyse."
            )

        return warnings

    def build_recommendation(
        self,
        building_function,
        foundation_load_precheck
    ):
        return {
            "status": "STRUCTURAL_LOAD_ADVIES",
            "building_function": building_function,
            "estimated_line_load_kN_m": foundation_load_precheck.get(
                "estimated_line_load_kN_m"
            ),
            "advice": (
                "Gebruik deze belastinganalyse als invoer voor constructieve "
                "elementberekening, funderingsberekening, dakcontrole en "
                "normatieve belastingcombinaties."
            )
        }

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_structural_load_result(self):
        return self.structural_load_result

    def create_load_analysis(self, *args, **kwargs):
        return self.create_structural_load_analysis(*args, **kwargs)

    def generate_structural_load_analysis(self, *args, **kwargs):
        return self.create_structural_load_analysis(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_load_analysis(*args, **kwargs)
