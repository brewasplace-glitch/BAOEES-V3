from datetime import datetime


class StructuralEngine:

    def __init__(self):
        self.structural_result = {}

    def analyze_structure(self, project_result=None, geo_result=None, aaie_result=None):
        project_result = project_result or {}
        geo_result = geo_result or {}
        aaie_result = aaie_result or {}

        design_basis = self.build_design_basis(project_result, aaie_result)

        loads = self.calculate_loads(design_basis)
        load_combinations = self.calculate_load_combinations(loads)
        foundation_reactions = self.calculate_foundation_reactions(
            design_basis=design_basis,
            load_combinations=load_combinations
        )

        beam_check = self.check_reference_beam(
            design_basis=design_basis,
            load_combinations=load_combinations
        )

        column_check = self.check_reference_column(
            design_basis=design_basis,
            load_combinations=load_combinations
        )

        roof_check = self.check_roof_structure(
            design_basis=design_basis,
            load_combinations=load_combinations
        )

        foundation_assessment = self.assess_foundation_with_geo(
            geo_result=geo_result,
            foundation_reactions=foundation_reactions
        )

        recommendation = self.build_structural_recommendation(
            beam_check=beam_check,
            column_check=column_check,
            roof_check=roof_check,
            foundation_assessment=foundation_assessment
        )

        self.structural_result = {
            "engine": "StructuralEngine",
            "version": "1.1",
            "status": "STRUCTURAL_ANALYSE_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve constructieve basisberekening",
            "design_basis": design_basis,
            "loads": loads,
            "load_combinations": load_combinations,
            "foundation_reactions": foundation_reactions,
            "beam_check": beam_check,
            "column_check": column_check,
            "roof_check": roof_check,
            "foundation_assessment": foundation_assessment,
            "recommendation": recommendation,
            "warnings": self.build_warnings(
                beam_check=beam_check,
                column_check=column_check,
                roof_check=roof_check,
                foundation_assessment=foundation_assessment
            ),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Structural Engine v1.1 maakt een indicatieve constructieve basisberekening. "
                "Voor definitief ontwerp zijn projectspecifieke belastingen, materiaalgegevens, "
                "normtoetsing en controle door een bevoegd constructeur noodzakelijk."
            )
        }

        return self.structural_result

    def build_design_basis(self, project_result, aaie_result):
        return {
            "building_type": project_result.get("project_type", "Bouw"),
            "reference_width_m": 10.0,
            "reference_length_m": 20.0,
            "reference_floor_area_m2": 200.0,
            "number_of_storeys": 2,
            "storey_height_m": 3.0,
            "main_span_m": 5.0,
            "secondary_span_m": 4.0,
            "grid_spacing_m": 5.0,
            "roof_type": "plat dak / licht hellend dak",
            "structural_system": "kolommen, balken, vloeren en fundering",
            "material_concrete": "C25/30",
            "material_reinforcement": "B500B",
            "material_steel": "S235",
            "material_timber": "C24",
            "design_standard_status": "indicatief / normcontrole later",
            "source": "BAOEES default structural assumptions"
        }

    def calculate_loads(self, design_basis):
        floor_dead_load_kN_m2 = 4.0
        floor_live_load_kN_m2 = 2.0
        roof_dead_load_kN_m2 = 1.2
        roof_live_load_kN_m2 = 0.75
        wind_load_kN_m2 = 0.6

        facade_load_kN_m = 3.0
        partition_load_kN_m2 = 1.0

        total_floor_dead_load_kN_m2 = floor_dead_load_kN_m2 + partition_load_kN_m2

        return {
            "floor_dead_load_kN_m2": floor_dead_load_kN_m2,
            "partition_load_kN_m2": partition_load_kN_m2,
            "total_floor_dead_load_kN_m2": total_floor_dead_load_kN_m2,
            "floor_live_load_kN_m2": floor_live_load_kN_m2,
            "roof_dead_load_kN_m2": roof_dead_load_kN_m2,
            "roof_live_load_kN_m2": roof_live_load_kN_m2,
            "wind_load_kN_m2": wind_load_kN_m2,
            "facade_load_kN_m": facade_load_kN_m,
            "load_status": "AANNAME",
            "note": "Belastingen zijn indicatieve standaardwaarden en moeten projectspecifiek worden gecontroleerd."
        }

    def calculate_load_combinations(self, loads):
        g_floor = loads["total_floor_dead_load_kN_m2"]
        q_floor = loads["floor_live_load_kN_m2"]
        g_roof = loads["roof_dead_load_kN_m2"]
        q_roof = loads["roof_live_load_kN_m2"]
        wind = loads["wind_load_kN_m2"]

        uls_floor_kN_m2 = 1.35 * g_floor + 1.5 * q_floor
        sls_floor_kN_m2 = g_floor + q_floor

        uls_roof_kN_m2 = 1.35 * g_roof + 1.5 * q_roof
        sls_roof_kN_m2 = g_roof + q_roof

        uls_wind_kN_m2 = 1.35 * g_roof + 1.5 * wind

        return {
            "uls_floor_kN_m2": round(uls_floor_kN_m2, 2),
            "sls_floor_kN_m2": round(sls_floor_kN_m2, 2),
            "uls_roof_kN_m2": round(uls_roof_kN_m2, 2),
            "sls_roof_kN_m2": round(sls_roof_kN_m2, 2),
            "uls_wind_roof_kN_m2": round(uls_wind_kN_m2, 2),
            "combination_status": "INDICATIEF",
            "note": "ULS/SLS combinaties zijn vereenvoudigd voor v1.1."
        }

    def calculate_foundation_reactions(self, design_basis, load_combinations):
        tributary_width_m = design_basis["grid_spacing_m"]
        tributary_length_m = design_basis["grid_spacing_m"]
        tributary_area_m2 = tributary_width_m * tributary_length_m

        number_of_storeys = design_basis["number_of_storeys"]

        uls_floor_load = load_combinations["uls_floor_kN_m2"]
        uls_roof_load = load_combinations["uls_roof_kN_m2"]

        column_reaction_kN = (
            uls_floor_load * tributary_area_m2 * number_of_storeys
            + uls_roof_load * tributary_area_m2
        )

        line_load_kN_m = (
            uls_floor_load * tributary_width_m * number_of_storeys
            + uls_roof_load * tributary_width_m
        )

        return {
            "tributary_width_m": tributary_width_m,
            "tributary_length_m": tributary_length_m,
            "tributary_area_m2": tributary_area_m2,
            "reference_column_reaction_kN": round(column_reaction_kN, 1),
            "reference_wall_line_load_kN_m": round(line_load_kN_m, 1),
            "status": "FUNDERINGSREACTIES_BEREKEND_INDICATIEF"
        }

    def check_reference_beam(self, design_basis, load_combinations):
        span_m = design_basis["main_span_m"]
        beam_width_m = 0.30
        beam_height_m = 0.50

        line_load_kN_m = load_combinations["uls_floor_kN_m2"] * design_basis["secondary_span_m"]

        max_moment_kNm = line_load_kN_m * span_m ** 2 / 8
        max_shear_kN = line_load_kN_m * span_m / 2

        estimated_moment_capacity_kNm = beam_width_m * beam_height_m ** 2 * 2500
        estimated_shear_capacity_kN = beam_width_m * beam_height_m * 900

        moment_unity = max_moment_kNm / estimated_moment_capacity_kNm
        shear_unity = max_shear_kN / estimated_shear_capacity_kN
        governing_unity = max(moment_unity, shear_unity)

        if governing_unity <= 1.0:
            status = "VOLDOET_INDICATIEF"
        else:
            status = "VOLDOET_NIET_INDICATIEF"

        return {
            "element": "referentiebalk",
            "span_m": span_m,
            "beam_width_m": beam_width_m,
            "beam_height_m": beam_height_m,
            "line_load_kN_m": round(line_load_kN_m, 2),
            "max_moment_kNm": round(max_moment_kNm, 2),
            "max_shear_kN": round(max_shear_kN, 2),
            "estimated_moment_capacity_kNm": round(estimated_moment_capacity_kNm, 2),
            "estimated_shear_capacity_kN": round(estimated_shear_capacity_kN, 2),
            "moment_unity": round(moment_unity, 2),
            "shear_unity": round(shear_unity, 2),
            "governing_unity": round(governing_unity, 2),
            "status": status
        }

    def check_reference_column(self, design_basis, load_combinations):
        column_width_m = 0.30
        column_depth_m = 0.30
        column_area_m2 = column_width_m * column_depth_m

        concrete_design_strength_kPa = 12000.0

        tributary_area_m2 = design_basis["grid_spacing_m"] * design_basis["grid_spacing_m"]
        number_of_storeys = design_basis["number_of_storeys"]

        axial_load_kN = (
            load_combinations["uls_floor_kN_m2"] * tributary_area_m2 * number_of_storeys
            + load_combinations["uls_roof_kN_m2"] * tributary_area_m2
        )

        axial_capacity_kN = column_area_m2 * concrete_design_strength_kPa

        unity_check = axial_load_kN / axial_capacity_kN

        if unity_check <= 1.0:
            status = "VOLDOET_INDICATIEF"
        else:
            status = "VOLDOET_NIET_INDICATIEF"

        return {
            "element": "referentiekolom",
            "column_width_m": column_width_m,
            "column_depth_m": column_depth_m,
            "column_area_m2": round(column_area_m2, 3),
            "axial_load_kN": round(axial_load_kN, 1),
            "estimated_axial_capacity_kN": round(axial_capacity_kN, 1),
            "unity_check": round(unity_check, 2),
            "status": status
        }

    def check_roof_structure(self, design_basis, load_combinations):
        span_m = design_basis["main_span_m"]
        spacing_m = 1.0

        roof_line_load_kN_m = load_combinations["uls_roof_kN_m2"] * spacing_m

        max_moment_kNm = roof_line_load_kN_m * span_m ** 2 / 8
        max_shear_kN = roof_line_load_kN_m * span_m / 2

        timber_section_width_m = 0.075
        timber_section_height_m = 0.225

        estimated_moment_capacity_kNm = timber_section_width_m * timber_section_height_m ** 2 * 1800
        estimated_shear_capacity_kN = timber_section_width_m * timber_section_height_m * 350

        moment_unity = max_moment_kNm / estimated_moment_capacity_kNm
        shear_unity = max_shear_kN / estimated_shear_capacity_kN
        governing_unity = max(moment_unity, shear_unity)

        if governing_unity <= 1.0:
            status = "VOLDOET_INDICATIEF"
        else:
            status = "VOLDOET_NIET_INDICATIEF"

        return {
            "element": "referentie dakregel / gording",
            "span_m": span_m,
            "spacing_m": spacing_m,
            "roof_line_load_kN_m": round(roof_line_load_kN_m, 2),
            "timber_section_width_m": timber_section_width_m,
            "timber_section_height_m": timber_section_height_m,
            "max_moment_kNm": round(max_moment_kNm, 2),
            "max_shear_kN": round(max_shear_kN, 2),
            "estimated_moment_capacity_kNm": round(estimated_moment_capacity_kNm, 2),
            "estimated_shear_capacity_kN": round(estimated_shear_capacity_kN, 2),
            "moment_unity": round(moment_unity, 2),
            "shear_unity": round(shear_unity, 2),
            "governing_unity": round(governing_unity, 2),
            "status": status
        }

    def assess_foundation_with_geo(self, geo_result, foundation_reactions):
        geo_result = geo_result or {}

        strip_foundation = geo_result.get("strip_foundation", {})
        recommended_foundation = geo_result.get("recommended_foundation", {})

        allowable_pressure_kPa = strip_foundation.get("allowable_bearing_capacity_kPa", 0)
        wall_line_load_kN_m = foundation_reactions.get("reference_wall_line_load_kN_m", 0)

        assumed_strip_width_m = strip_foundation.get("foundation_width_m", 1.5)

        if assumed_strip_width_m <= 0:
            design_pressure_kPa = 9999
        else:
            design_pressure_kPa = wall_line_load_kN_m / assumed_strip_width_m

        if allowable_pressure_kPa > 0:
            unity_check = design_pressure_kPa / allowable_pressure_kPa
        else:
            unity_check = 9999

        if unity_check <= 1.0:
            status = "FUNDERING_VOLDOET_INDICATIEF"
        else:
            status = "FUNDERING_AANDACHTSPUNT"

        return {
            "geo_engine_status": geo_result.get("status", "onbekend"),
            "recommended_foundation_type": recommended_foundation.get(
                "selected_foundation_type",
                "onbekend"
            ),
            "assumed_strip_width_m": assumed_strip_width_m,
            "allowable_bearing_capacity_kPa": allowable_pressure_kPa,
            "structural_wall_line_load_kN_m": round(wall_line_load_kN_m, 1),
            "calculated_design_pressure_kPa": round(design_pressure_kPa, 1),
            "unity_check": round(unity_check, 2),
            "status": status
        }

    def build_structural_recommendation(
        self,
        beam_check,
        column_check,
        roof_check,
        foundation_assessment
    ):
        checks = [
            beam_check.get("status"),
            column_check.get("status"),
            roof_check.get("status"),
            foundation_assessment.get("status")
        ]

        if all(status in ["VOLDOET_INDICATIEF", "FUNDERING_VOLDOET_INDICATIEF"] for status in checks):
            advice = "Constructief concept voldoet indicatief."
            status = "POSITIEF_CONCEPTADVIES"
        else:
            advice = (
                "Er zijn constructieve aandachtspunten. "
                "Controleer afmetingen, overspanningen, belastingen en fundering in detail."
            )
            status = "AANDACHTSPUNTEN"

        return {
            "status": status,
            "advice": advice,
            "next_steps": [
                "definitieve belastingopgave vaststellen",
                "constructief schema modelleren",
                "beton-, staal- of houtberekening uitvoeren",
                "funderingsreacties definitief koppelen aan geotechniek",
                "wapening, profielen en details uitwerken"
            ]
        }

    def build_warnings(self, beam_check, column_check, roof_check, foundation_assessment):
        warnings = []

        if beam_check.get("status") != "VOLDOET_INDICATIEF":
            warnings.append("Referentiebalk voldoet indicatief niet of vraagt controle.")

        if column_check.get("status") != "VOLDOET_INDICATIEF":
            warnings.append("Referentiekolom voldoet indicatief niet of vraagt controle.")

        if roof_check.get("status") != "VOLDOET_INDICATIEF":
            warnings.append("Dakconstructie voldoet indicatief niet of vraagt controle.")

        if foundation_assessment.get("status") != "FUNDERING_VOLDOET_INDICATIEF":
            warnings.append("Fundering vraagt nadere controle op basis van Geo Engine-resultaten.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen op basis van deze indicatieve constructieve berekening.")

        return warnings

    def get_structural_result(self):
        return self.structural_result

    def run(self):
        print("Structural Engine actief")