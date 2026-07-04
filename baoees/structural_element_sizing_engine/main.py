from datetime import datetime


class StructuralElementSizingEngine:

    def __init__(self):
        self.structural_element_sizing_result = {}

    def create_structural_element_sizing(
        self,
        project_result=None,
        structural_load_result=None,
        element_load_result=None,
        foundation_design_result=None,
        foundation_verification_result=None,
        building_technical_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        structural_load_result = structural_load_result or {}
        element_load_result = element_load_result or {}
        foundation_design_result = foundation_design_result or {}
        foundation_verification_result = foundation_verification_result or {}
        building_technical_result = building_technical_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        area = self.safe_number(
            project_result.get(
                "gross_floor_area_m2",
                element_load_result.get("gross_floor_area_m2", 100)
            ),
            100
        )
        if area <= 0:
            area = 100.0

        floors = int(max(self.safe_number(
            project_result.get(
                "number_of_floors",
                element_load_result.get("number_of_floors", 1)
            ),
            1
        ), 1))

        span_m = self.safe_number(project_result.get("main_span_m", 5.0), 5.0)
        grid_spacing_m = self.safe_number(project_result.get("grid_spacing_m", 5.0), 5.0)

        floor_loads = element_load_result.get("floor_loads", [])
        if floor_loads:
            uls_floor_load = self.safe_number(
                floor_loads[0].get("uls_floor_load_kN_m2", 10.0),
                10.0
            )
        else:
            uls_floor_load = self.safe_number(
                structural_load_result.get("load_combinations", {}).get("uls_gravity_kN_m2", 10.0),
                10.0
            )

        column_loads = element_load_result.get("column_loads", {})
        uls_column_load = self.safe_number(
            column_loads.get("uls_load_per_column_kN", 450.0),
            450.0
        )

        foundation_line_load = self.safe_number(
            element_load_result.get("foundation_line_loads", {}).get(
                "combined_foundation_line_load_kN_m",
                45.0
            ),
            45.0
        )

        slab_design = self.build_slab_design(
            span_m=span_m,
            uls_floor_load=uls_floor_load
        )

        beam_design = self.build_beam_design(
            span_m=span_m,
            tributary_width_m=grid_spacing_m,
            uls_floor_load=uls_floor_load
        )

        column_design = self.build_column_design(
            floors=floors,
            uls_column_load=uls_column_load
        )

        wall_design = self.build_wall_design(
            floors=floors,
            foundation_line_load=foundation_line_load
        )

        foundation_element_design = self.build_foundation_element_design(
            foundation_design_result=foundation_design_result,
            foundation_verification_result=foundation_verification_result,
            foundation_line_load=foundation_line_load
        )

        sizing_summary = self.build_sizing_summary(
            slab_design=slab_design,
            beam_design=beam_design,
            column_design=column_design,
            wall_design=wall_design,
            foundation_element_design=foundation_element_design
        )

        self.structural_element_sizing_result = {
            "engine": "StructuralElementSizingEngine",
            "version": "1.0",
            "status": "STRUCTURAL_ELEMENT_SIZING_GEREED",
            "calculation_level": "voorlopige elementdimensionering",
            "project_id": project_id,
            "project_name": project_name,
            "gross_floor_area_m2": area,
            "number_of_floors": floors,
            "input_summary": {
                "main_span_m": span_m,
                "grid_spacing_m": grid_spacing_m,
                "uls_floor_load_kN_m2": uls_floor_load,
                "uls_column_load_kN": uls_column_load,
                "foundation_line_load_kN_m": foundation_line_load
            },
            "slab_design": slab_design,
            "beam_design": beam_design,
            "column_design": column_design,
            "wall_design": wall_design,
            "foundation_element_design": foundation_element_design,
            "sizing_summary": sizing_summary,
            "qa_qc_checks": self.build_qa_qc_checks(
                slab_design=slab_design,
                beam_design=beam_design,
                column_design=column_design,
                foundation_element_design=foundation_element_design
            ),
            "digital_twin_update": {
                "digital_twin_node": "structural_element_sizing",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "slab_design": slab_design,
                    "beam_design": beam_design,
                    "column_design": column_design,
                    "wall_design": wall_design,
                    "foundation_element_design": foundation_element_design,
                    "sizing_summary": sizing_summary
                }
            },
            "warnings": self.build_warnings(
                span_m=span_m,
                uls_floor_load=uls_floor_load,
                uls_column_load=uls_column_load,
                foundation_line_load=foundation_line_load
            ),
            "recommendation": {
                "status": "STRUCTURAL_ELEMENT_SIZING_ADVIES",
                "advice": (
                    "Gebruik deze voorlopige elementdimensionering als basis voor "
                    "normatieve beton-, staal-, hout- en funderingsberekeningen."
                ),
                "next_steps": [
                    "materiaalkeuze per element vastleggen",
                    "overspanningen uit constructiemodel bepalen",
                    "wapeningsvoorstellen genereren",
                    "doorbuiging en scheurwijdte toetsen",
                    "definitieve normberekening per element uitvoeren"
                ]
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.structural_element_sizing_result

    def build_slab_design(self, span_m, uls_floor_load):
        thickness_mm = max(160, min(350, int(round(span_m * 35))))
        moment_kNm_m = uls_floor_load * span_m * span_m / 8.0
        reinforcement_note = "basiswapening nader te bepalen"

        if moment_kNm_m > 35:
            reinforcement_note = "verhoogde hoofdwapening verwacht"

        return {
            "element": "vloerplaat",
            "recommended_thickness_mm": thickness_mm,
            "span_m": round(span_m, 2),
            "uls_floor_load_kN_m2": round(uls_floor_load, 2),
            "indicative_moment_kNm_per_m": round(moment_kNm_m, 2),
            "reinforcement_note": reinforcement_note,
            "status": "VOORLOPIG"
        }

    def build_beam_design(self, span_m, tributary_width_m, uls_floor_load):
        line_load_kN_m = uls_floor_load * tributary_width_m
        moment_kNm = line_load_kN_m * span_m * span_m / 8.0
        beam_height_mm = max(300, min(800, int(round(span_m * 100))))
        beam_width_mm = max(250, int(round(beam_height_mm * 0.45)))

        return {
            "element": "funderingsvrije_ligger_of_vloerbalk",
            "recommended_width_mm": beam_width_mm,
            "recommended_height_mm": beam_height_mm,
            "span_m": round(span_m, 2),
            "tributary_width_m": round(tributary_width_m, 2),
            "line_load_kN_m": round(line_load_kN_m, 2),
            "indicative_moment_kNm": round(moment_kNm, 2),
            "status": "VOORLOPIG"
        }

    def build_column_design(self, floors, uls_column_load):
        base_size_mm = 250

        if uls_column_load > 600:
            base_size_mm = 300
        if uls_column_load > 1000:
            base_size_mm = 350
        if floors >= 4:
            base_size_mm += 50

        return {
            "element": "kolom",
            "recommended_square_size_mm": base_size_mm,
            "uls_column_load_kN": round(uls_column_load, 2),
            "number_of_floors": floors,
            "status": "VOORLOPIG"
        }

    def build_wall_design(self, floors, foundation_line_load):
        wall_thickness_mm = 150

        if foundation_line_load > 80:
            wall_thickness_mm = 200
        if floors >= 3:
            wall_thickness_mm = max(wall_thickness_mm, 200)

        return {
            "element": "dragende_wand",
            "recommended_thickness_mm": wall_thickness_mm,
            "foundation_line_load_kN_m": round(foundation_line_load, 2),
            "number_of_floors": floors,
            "status": "VOORLOPIG"
        }

    def build_foundation_element_design(
        self,
        foundation_design_result,
        foundation_verification_result,
        foundation_line_load
    ):
        design = foundation_design_result.get("recommended_foundation", {})
        verification_status = foundation_verification_result.get("status", "NIET_GEGEVEN")

        strip_width_mm = self.safe_number(
            design.get("strip_width_mm", 1500),
            1500
        )
        beam_width_mm = self.safe_number(
            design.get("foundation_beam_width_mm", 500),
            500
        )
        beam_height_mm = self.safe_number(
            design.get("foundation_beam_height_mm", 600),
            600
        )

        if foundation_line_load > 90:
            strip_width_mm = max(strip_width_mm, 1800)
            beam_height_mm = max(beam_height_mm, 700)

        if foundation_line_load > 130:
            strip_width_mm = max(strip_width_mm, 2200)
            beam_height_mm = max(beam_height_mm, 800)

        return {
            "element": "funderingsstrook_en_funderingsbalk",
            "recommended_strip_width_mm": int(strip_width_mm),
            "recommended_foundation_beam_width_mm": int(beam_width_mm),
            "recommended_foundation_beam_height_mm": int(beam_height_mm),
            "foundation_line_load_kN_m": round(foundation_line_load, 2),
            "source_foundation_design_status": design.get("status", "VOORLOPIG"),
            "source_foundation_verification_status": verification_status,
            "status": "VOORLOPIG"
        }

    def build_sizing_summary(
        self,
        slab_design,
        beam_design,
        column_design,
        wall_design,
        foundation_element_design
    ):
        return {
            "recommended_slab_thickness_mm": slab_design["recommended_thickness_mm"],
            "recommended_beam_size_mm": (
                f"{beam_design['recommended_width_mm']}x"
                f"{beam_design['recommended_height_mm']}"
            ),
            "recommended_column_size_mm": column_design["recommended_square_size_mm"],
            "recommended_wall_thickness_mm": wall_design["recommended_thickness_mm"],
            "recommended_foundation_strip_width_mm": foundation_element_design[
                "recommended_strip_width_mm"
            ],
            "status": "VOORLOPIG"
        }

    def build_qa_qc_checks(
        self,
        slab_design,
        beam_design,
        column_design,
        foundation_element_design
    ):
        return [
            {
                "check": "vloer_dikte_bepaald",
                "status": "OK" if slab_design.get("recommended_thickness_mm", 0) > 0 else "AANDACHT"
            },
            {
                "check": "balk_afmeting_bepaald",
                "status": "OK" if beam_design.get("recommended_height_mm", 0) > 0 else "AANDACHT"
            },
            {
                "check": "kolom_afmeting_bepaald",
                "status": "OK" if column_design.get("recommended_square_size_mm", 0) > 0 else "AANDACHT"
            },
            {
                "check": "funderingselement_bepaald",
                "status": "OK" if foundation_element_design.get("recommended_strip_width_mm", 0) > 0 else "AANDACHT"
            }
        ]

    def build_warnings(self, span_m, uls_floor_load, uls_column_load, foundation_line_load):
        warnings = []

        if span_m > 7.0:
            warnings.append("Grote overspanning; doorbuiging en trilling moeten expliciet worden gecontroleerd.")

        if uls_floor_load > 12.0:
            warnings.append("Hoge vloerbelasting; elementdimensionering moet normatief worden verdiept.")

        if uls_column_load > 1000:
            warnings.append("Hoge kolomlast; kolomdoorsnede en fundering extra controleren.")

        if foundation_line_load > 130:
            warnings.append("Zeer hoge funderingslijnlast; paaloptie of bredere funderingsstrook onderzoeken.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de voorlopige elementdimensionering.")

        return warnings

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_structural_element_sizing_result(self):
        return self.structural_element_sizing_result

    def create_sizing(self, *args, **kwargs):
        return self.create_structural_element_sizing(*args, **kwargs)

    def create_element_sizing(self, *args, **kwargs):
        return self.create_structural_element_sizing(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_element_sizing(*args, **kwargs)
