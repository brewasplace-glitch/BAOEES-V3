from datetime import datetime


class QuantityEngine:

    def __init__(self):
        self.quantity_result = {}

    def generate_quantities(
        self,
        project_result=None,
        aaie_result=None,
        geo_result=None,
        structural_result=None,
        drainage_result=None,
        traffic_parking_result=None,
        drawing_result=None,
        cad_result=None
    ):
        project_result = project_result or {}
        aaie_result = aaie_result or {}
        geo_result = geo_result or {}
        structural_result = structural_result or {}
        drainage_result = drainage_result or {}
        traffic_parking_result = traffic_parking_result or {}
        drawing_result = drawing_result or {}
        cad_result = cad_result or {}

        project_basis = self.build_project_basis(project_result, aaie_result)

        earthwork_quantities = self.calculate_earthworks(
            project_basis=project_basis,
            geo_result=geo_result
        )

        foundation_quantities = self.calculate_foundations(
            project_basis=project_basis,
            geo_result=geo_result
        )

        concrete_quantities = self.calculate_concrete_structure(
            project_basis=project_basis,
            structural_result=structural_result
        )

        steel_timber_quantities = self.calculate_steel_and_timber(
            project_basis=project_basis,
            structural_result=structural_result
        )

        drainage_quantities = self.calculate_drainage_quantities(
            project_basis=project_basis,
            drainage_result=drainage_result
        )

        sitework_quantities = self.calculate_siteworks(
            project_basis=project_basis,
            traffic_parking_result=traffic_parking_result
        )

        boq_summary = self.build_boq_summary(
            earthwork_quantities=earthwork_quantities,
            foundation_quantities=foundation_quantities,
            concrete_quantities=concrete_quantities,
            steel_timber_quantities=steel_timber_quantities,
            drainage_quantities=drainage_quantities,
            sitework_quantities=sitework_quantities
        )

        self.quantity_result = {
            "engine": "QuantityEngine",
            "version": "1.0",
            "status": "QUANTITY_TAKEOFF_GEREED",
            "project_name": project_result.get("project_name", "Onbekend project"),
            "location": project_result.get("location", "Onbekend"),
            "country": project_result.get("country", "Onbekend"),
            "calculation_level": "indicatieve hoeveelhedenstaat",
            "project_basis": project_basis,
            "earthworks": earthwork_quantities,
            "foundations": foundation_quantities,
            "concrete_structure": concrete_quantities,
            "steel_and_timber": steel_timber_quantities,
            "drainage_and_sewerage": drainage_quantities,
            "siteworks": sitework_quantities,
            "boq_summary": boq_summary,
            "warnings": self.build_warnings(
                project_basis=project_basis,
                geo_result=geo_result,
                structural_result=structural_result,
                drainage_result=drainage_result
            ),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Quantity Engine v1.0 maakt een indicatieve hoeveelhedenstaat. "
                "Voor bestek, aanbesteding of uitvoering zijn maatvaste tekeningen, "
                "definitieve constructieberekeningen en projectspecifieke hoeveelheden noodzakelijk."
            )
        }

        return self.quantity_result

    def build_project_basis(self, project_result, aaie_result):
        gross_floor_area_m2 = project_result.get("gross_floor_area_m2")

        if gross_floor_area_m2 is None:
            gross_floor_area_m2 = aaie_result.get("gross_floor_area_m2", 200.0)

        try:
            gross_floor_area_m2 = float(gross_floor_area_m2)
        except ValueError:
            gross_floor_area_m2 = 200.0

        if gross_floor_area_m2 <= 0:
            gross_floor_area_m2 = 200.0

        building_length_m = 20.0
        building_width_m = 10.0
        storeys = 2

        footprint_m2 = building_length_m * building_width_m
        perimeter_m = 2 * (building_length_m + building_width_m)

        return {
            "gross_floor_area_m2": gross_floor_area_m2,
            "building_length_m": building_length_m,
            "building_width_m": building_width_m,
            "footprint_m2": footprint_m2,
            "perimeter_m": perimeter_m,
            "number_of_storeys": storeys,
            "project_type": project_result.get("project_type", "Bouw"),
            "country": project_result.get("country", "Onbekend"),
            "status": "AANNAME"
        }

    def calculate_earthworks(self, project_basis, geo_result):
        footprint = project_basis["footprint_m2"]

        excavation_depth_m = 0.60
        working_space_factor = 1.20

        excavation_volume_m3 = footprint * excavation_depth_m * working_space_factor
        backfill_volume_m3 = excavation_volume_m3 * 0.55
        disposal_volume_m3 = excavation_volume_m3 - backfill_volume_m3

        return {
            "status": "GRONDWERK_HOEVEELHEDEN_GEREED",
            "excavation_depth_m": excavation_depth_m,
            "excavation_volume_m3": round(excavation_volume_m3, 2),
            "backfill_volume_m3": round(backfill_volume_m3, 2),
            "soil_disposal_volume_m3": round(disposal_volume_m3, 2),
            "note": "Grondwerk indicatief op basis van footprint en funderingsdiepte."
        }

    def calculate_foundations(self, project_basis, geo_result):
        perimeter = project_basis["perimeter_m"]
        footprint = project_basis["footprint_m2"]

        recommended_foundation = geo_result.get("recommended_foundation", {}).get(
            "selected_foundation_type",
            "strokenfundering"
        )

        strip_width_m = 1.50
        strip_height_m = 0.40
        foundation_beam_width_m = 0.50
        foundation_beam_height_m = 0.60

        strip_concrete_m3 = perimeter * strip_width_m * strip_height_m
        beam_concrete_m3 = perimeter * foundation_beam_width_m * foundation_beam_height_m

        pile_count = 0
        pile_concrete_m3 = 0.0

        if recommended_foundation == "paalfundering":
            pile_count = max(8, round(footprint / 20))
            pile_diameter_m = 0.30
            pile_length_m = 6.00
            pile_concrete_m3 = pile_count * 3.14159 * (pile_diameter_m / 2) ** 2 * pile_length_m
        else:
            pile_diameter_m = 0.0
            pile_length_m = 0.0

        reinforcement_kg = (strip_concrete_m3 + beam_concrete_m3 + pile_concrete_m3) * 95

        return {
            "status": "FUNDERING_HOEVEELHEDEN_GEREED",
            "recommended_foundation_type": recommended_foundation,
            "strip_foundation_length_m": round(perimeter, 2),
            "strip_width_m": strip_width_m,
            "strip_height_m": strip_height_m,
            "strip_concrete_m3": round(strip_concrete_m3, 2),
            "foundation_beam_length_m": round(perimeter, 2),
            "foundation_beam_concrete_m3": round(beam_concrete_m3, 2),
            "pile_count": pile_count,
            "pile_diameter_m": pile_diameter_m,
            "pile_length_m": pile_length_m,
            "pile_concrete_m3": round(pile_concrete_m3, 2),
            "foundation_reinforcement_kg": round(reinforcement_kg, 1)
        }

    def calculate_concrete_structure(self, project_basis, structural_result):
        footprint = project_basis["footprint_m2"]
        gross_floor_area = project_basis["gross_floor_area_m2"]
        storeys = project_basis["number_of_storeys"]

        floor_thickness_m = 0.15
        slab_concrete_m3 = gross_floor_area * floor_thickness_m

        column_count = max(6, round(footprint / 25))
        column_width_m = 0.30
        column_depth_m = 0.30
        column_height_m = storeys * 3.0
        column_concrete_m3 = column_count * column_width_m * column_depth_m * column_height_m

        beam_length_m = project_basis["perimeter_m"] + (project_basis["building_length_m"] * 2)
        beam_width_m = 0.30
        beam_height_m = 0.50
        beam_concrete_m3 = beam_length_m * beam_width_m * beam_height_m

        total_concrete_m3 = slab_concrete_m3 + column_concrete_m3 + beam_concrete_m3
        reinforcement_kg = total_concrete_m3 * 110

        return {
            "status": "BETONCONSTRUCTIE_HOEVEELHEDEN_GEREED",
            "floor_slab_concrete_m3": round(slab_concrete_m3, 2),
            "column_count": column_count,
            "column_concrete_m3": round(column_concrete_m3, 2),
            "beam_length_m": round(beam_length_m, 2),
            "beam_concrete_m3": round(beam_concrete_m3, 2),
            "total_superstructure_concrete_m3": round(total_concrete_m3, 2),
            "superstructure_reinforcement_kg": round(reinforcement_kg, 1)
        }

    def calculate_steel_and_timber(self, project_basis, structural_result):
        roof_area_m2 = project_basis["footprint_m2"]
        roof_timber_m3 = roof_area_m2 * 0.035
        structural_steel_kg = project_basis["gross_floor_area_m2"] * 18.0

        roof_check = structural_result.get("roof_check", {})
        roof_status = roof_check.get("status", "onbekend")

        return {
            "status": "STAAL_HOUT_HOEVEELHEDEN_GEREED",
            "roof_area_m2": round(roof_area_m2, 2),
            "roof_timber_m3": round(roof_timber_m3, 2),
            "indicative_structural_steel_kg": round(structural_steel_kg, 1),
            "roof_check_status": roof_status,
            "note": "Staal en hout zijn indicatieve hoeveelheden op basis van vloeroppervlak en dakoppervlak."
        }

    def calculate_drainage_quantities(self, project_basis, drainage_result):
        drainage_layout = drainage_result.get("drainage_layout", {})
        pipe_design = drainage_result.get("pipe_design", {})

        hwa_length_m = project_basis["perimeter_m"] * 0.75
        dwa_length_m = project_basis["building_length_m"] * 0.80
        infiltration_volume_m3 = drainage_result.get("storage_and_infiltration", {}).get(
            "required_storage_m3",
            0
        )

        return {
            "status": "RIOLERING_HOEVEELHEDEN_GEREED",
            "hwa_pipe_length_m": round(hwa_length_m, 2),
            "hwa_pipe_diameter_mm": pipe_design.get("hwa_pipe_diameter_mm", 125),
            "dwa_pipe_length_m": round(dwa_length_m, 2),
            "dwa_pipe_diameter_mm": pipe_design.get("dwa_pipe_diameter_mm", 110),
            "roof_downpipes": drainage_layout.get("roof_downpipes", 2),
            "yard_drains_or_gullies": drainage_layout.get("yard_drains_or_gullies", 1),
            "inspection_chambers": drainage_layout.get("inspection_chambers", 2),
            "infiltration_or_storage_m3": round(float(infiltration_volume_m3), 2)
        }

    def calculate_siteworks(self, project_basis, traffic_parking_result):
        paved_area_m2 = project_basis["gross_floor_area_m2"] * 0.45
        green_area_m2 = project_basis["gross_floor_area_m2"] * 0.30

        parking_required = traffic_parking_result.get("parking_demand", {}).get(
            "rounded_required_spaces",
            0
        )

        parking_paving_m2 = parking_required * 25.0

        return {
            "status": "TERREIN_HOEVEELHEDEN_GEREED",
            "general_paving_m2": round(paved_area_m2, 2),
            "green_area_m2": round(green_area_m2, 2),
            "parking_required_spaces": parking_required,
            "parking_paving_m2": round(parking_paving_m2, 2),
            "site_marking_m": round(parking_required * 5.0, 2)
        }

    def build_boq_summary(
        self,
        earthwork_quantities,
        foundation_quantities,
        concrete_quantities,
        steel_timber_quantities,
        drainage_quantities,
        sitework_quantities
    ):
        return {
            "status": "BOQ_SAMENVATTING_GEREED",
            "main_quantities": [
                {
                    "code": "GW-001",
                    "description": "Ontgraving",
                    "quantity": earthwork_quantities["excavation_volume_m3"],
                    "unit": "m3"
                },
                {
                    "code": "FUN-001",
                    "description": "Beton fundering totaal",
                    "quantity": round(
                        foundation_quantities["strip_concrete_m3"]
                        + foundation_quantities["foundation_beam_concrete_m3"]
                        + foundation_quantities["pile_concrete_m3"],
                        2
                    ),
                    "unit": "m3"
                },
                {
                    "code": "BET-001",
                    "description": "Beton bovenbouw totaal",
                    "quantity": concrete_quantities["total_superstructure_concrete_m3"],
                    "unit": "m3"
                },
                {
                    "code": "WAP-001",
                    "description": "Wapening totaal indicatief",
                    "quantity": round(
                        foundation_quantities["foundation_reinforcement_kg"]
                        + concrete_quantities["superstructure_reinforcement_kg"],
                        1
                    ),
                    "unit": "kg"
                },
                {
                    "code": "HOUT-001",
                    "description": "Dak-/houtconstructie indicatief",
                    "quantity": steel_timber_quantities["roof_timber_m3"],
                    "unit": "m3"
                },
                {
                    "code": "STAAL-001",
                    "description": "Constructiestaal indicatief",
                    "quantity": steel_timber_quantities["indicative_structural_steel_kg"],
                    "unit": "kg"
                },
                {
                    "code": "RIO-001",
                    "description": "HWA leiding",
                    "quantity": drainage_quantities["hwa_pipe_length_m"],
                    "unit": "m"
                },
                {
                    "code": "RIO-002",
                    "description": "DWA leiding",
                    "quantity": drainage_quantities["dwa_pipe_length_m"],
                    "unit": "m"
                },
                {
                    "code": "TER-001",
                    "description": "Terreinverharding",
                    "quantity": sitework_quantities["general_paving_m2"],
                    "unit": "m2"
                }
            ]
        }

    def build_warnings(self, project_basis, geo_result, structural_result, drainage_result):
        warnings = []

        if project_basis["status"] == "AANNAME":
            warnings.append("Hoeveelheden zijn gebaseerd op aannames voor gebouwmaat en oppervlak.")

        if geo_result.get("recommended_foundation", {}).get("selected_foundation_type") == "nader_geotechnisch_onderzoek":
            warnings.append("Funderingshoeveelheden onzeker door ontbrekend definitief geotechnisch advies.")

        if structural_result.get("recommendation", {}).get("status") == "AANDACHTSPUNTEN":
            warnings.append("Constructieve hoeveelheden kunnen wijzigen na definitieve berekening.")

        if drainage_result.get("storage_and_infiltration", {}).get("status", "").endswith("GRONDWATER_HOOG"):
            warnings.append("Bergings- en infiltratiehoeveelheden zijn onzeker door hoge grondwaterstand.")

        if not warnings:
            warnings.append("Geen kritieke hoeveelhedenwaarschuwingen op basis van deze indicatieve raming.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "HOEVEELHEDEN_ADVIES_CONCEPT",
            "advice": (
                "Gebruik deze hoeveelhedenstaat als eerste basis voor kostenraming en bestek. "
                "Werk hoeveelheden later bij op basis van maatvaste tekeningen, definitieve berekeningen en CAD/BIM-model."
            ),
            "next_steps": [
                "maatvaste plattegronden koppelen",
                "funderingsdetails definitief maken",
                "constructieve hoeveelheden koppelen aan berekening",
                "rioleringstracé op tekening zetten",
                "hoeveelheden exporteren naar kostenraming",
                "bestekposten genereren"
            ]
        }

    def get_quantity_result(self):
        return self.quantity_result

    def run(self):
        print("Quantity / BOQ Engine actief")