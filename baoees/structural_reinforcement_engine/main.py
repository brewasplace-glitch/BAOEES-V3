from datetime import datetime


class StructuralReinforcementEngine:

    def __init__(self):
        self.structural_reinforcement_result = {}

    def create_structural_reinforcement_design(
        self,
        project_result=None,
        structural_sizing_result=None,
        foundation_design_result=None,
        foundation_verification_result=None,
        element_load_result=None,
        structural_load_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        structural_sizing_result = structural_sizing_result or {}
        foundation_design_result = foundation_design_result or {}
        foundation_verification_result = foundation_verification_result or {}
        element_load_result = element_load_result or {}
        structural_load_result = structural_load_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        floor_loads = element_load_result.get("floor_loads", [])
        if not floor_loads:
            floor_loads = [{"floor_number": 1, "uls_floor_load_kN_m2": 12.0}]

        foundation_line_loads = element_load_result.get("foundation_line_loads", {})
        foundation_design = foundation_design_result.get("recommended_foundation_system", {})
        foundation_verification = foundation_verification_result.get("verification_summary", {})

        slab_thickness_mm = self.get_nested_number(
            structural_sizing_result,
            ["slab_sizing", "recommended_slab_thickness_mm"],
            180
        )

        beam_width_mm = self.get_nested_number(
            structural_sizing_result,
            ["beam_sizing", "recommended_beam_width_mm"],
            250
        )

        beam_height_mm = self.get_nested_number(
            structural_sizing_result,
            ["beam_sizing", "recommended_beam_height_mm"],
            500
        )

        column_width_mm = self.get_nested_number(
            structural_sizing_result,
            ["column_sizing", "recommended_column_width_mm"],
            300
        )

        column_depth_mm = self.get_nested_number(
            structural_sizing_result,
            ["column_sizing", "recommended_column_depth_mm"],
            300
        )

        wall_thickness_mm = self.get_nested_number(
            structural_sizing_result,
            ["wall_sizing", "recommended_wall_thickness_mm"],
            200
        )

        strip_width_mm = self.get_nested_number(
            foundation_design_result,
            ["strip_foundation", "recommended_width_mm"],
            1500
        )

        strip_height_mm = self.get_nested_number(
            foundation_design_result,
            ["strip_foundation", "recommended_height_mm"],
            400
        )

        foundation_beam_width_mm = self.get_nested_number(
            foundation_design_result,
            ["foundation_beam", "recommended_width_mm"],
            500
        )

        foundation_beam_height_mm = self.get_nested_number(
            foundation_design_result,
            ["foundation_beam", "recommended_height_mm"],
            600
        )

        line_load_kN_m = self.safe_number(
            foundation_line_loads.get(
                "combined_foundation_line_load_kN_m",
                foundation_design.get("governing_line_load_kN_m", 60.0)
            ),
            60.0
        )

        slab_reinforcement = self.build_slab_reinforcement(
            floor_loads=floor_loads,
            slab_thickness_mm=slab_thickness_mm
        )

        beam_reinforcement = self.build_beam_reinforcement(
            beam_width_mm=beam_width_mm,
            beam_height_mm=beam_height_mm
        )

        column_reinforcement = self.build_column_reinforcement(
            column_width_mm=column_width_mm,
            column_depth_mm=column_depth_mm
        )

        wall_reinforcement = self.build_wall_reinforcement(
            wall_thickness_mm=wall_thickness_mm
        )

        strip_foundation_reinforcement = self.build_strip_foundation_reinforcement(
            strip_width_mm=strip_width_mm,
            strip_height_mm=strip_height_mm,
            line_load_kN_m=line_load_kN_m
        )

        foundation_beam_reinforcement = self.build_foundation_beam_reinforcement(
            foundation_beam_width_mm=foundation_beam_width_mm,
            foundation_beam_height_mm=foundation_beam_height_mm,
            line_load_kN_m=line_load_kN_m
        )

        pad_reinforcement = self.build_pad_reinforcement(
            foundation_design_result=foundation_design_result
        )

        qa_qc_checks = self.build_qa_qc_checks(
            slab_reinforcement=slab_reinforcement,
            beam_reinforcement=beam_reinforcement,
            column_reinforcement=column_reinforcement,
            strip_foundation_reinforcement=strip_foundation_reinforcement,
            foundation_verification=foundation_verification
        )

        reinforcement_summary = self.build_reinforcement_summary(
            slab_reinforcement=slab_reinforcement,
            beam_reinforcement=beam_reinforcement,
            column_reinforcement=column_reinforcement,
            wall_reinforcement=wall_reinforcement,
            strip_foundation_reinforcement=strip_foundation_reinforcement,
            foundation_beam_reinforcement=foundation_beam_reinforcement,
            pad_reinforcement=pad_reinforcement
        )

        self.structural_reinforcement_result = {
            "engine": "StructuralReinforcementEngine",
            "version": "1.0",
            "status": "STRUCTURAL_REINFORCEMENT_DESIGN_GEREED",
            "calculation_level": "indicatieve wapeningsvoorstellen",
            "project_id": project_id,
            "project_name": project_name,
            "slab_reinforcement": slab_reinforcement,
            "beam_reinforcement": beam_reinforcement,
            "column_reinforcement": column_reinforcement,
            "wall_reinforcement": wall_reinforcement,
            "strip_foundation_reinforcement": strip_foundation_reinforcement,
            "foundation_beam_reinforcement": foundation_beam_reinforcement,
            "pad_reinforcement": pad_reinforcement,
            "reinforcement_summary": reinforcement_summary,
            "qa_qc_checks": qa_qc_checks,
            "report_sections": self.build_report_sections(
                project_name=project_name,
                project_id=project_id,
                reinforcement_summary=reinforcement_summary
            ),
            "digital_twin_update": {
                "digital_twin_node": "structural_reinforcement",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "slab_reinforcement": slab_reinforcement,
                    "beam_reinforcement": beam_reinforcement,
                    "column_reinforcement": column_reinforcement,
                    "wall_reinforcement": wall_reinforcement,
                    "strip_foundation_reinforcement": strip_foundation_reinforcement,
                    "foundation_beam_reinforcement": foundation_beam_reinforcement,
                    "pad_reinforcement": pad_reinforcement,
                    "reinforcement_summary": reinforcement_summary
                }
            },
            "warnings": self.build_warnings(
                qa_qc_checks=qa_qc_checks,
                line_load_kN_m=line_load_kN_m
            ),
            "recommendation": {
                "status": "REINFORCEMENT_ADVIES",
                "advice": (
                    "Gebruik deze indicatieve wapening als startpunt voor normatieve "
                    "betonberekening, detailengineering en wapeningstekeningen."
                ),
                "next_steps": [
                    "definitieve overspanningen en steunpunten vastleggen",
                    "momenten, dwarskrachten en normaalkrachten berekenen",
                    "scheurwijdte en doorbuiging controleren",
                    "verankerings- en overlaplengtes bepalen",
                    "wapeningstekeningen genereren"
                ]
            },
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze engine maakt voorlopige wapeningsvoorstellen. "
                "Dit is geen definitieve normatieve wapeningberekening."
            )
        }

        return self.structural_reinforcement_result

    def build_slab_reinforcement(self, floor_loads, slab_thickness_mm):
        governing_uls_load = 0.0

        for floor_load in floor_loads:
            governing_uls_load = max(
                governing_uls_load,
                self.safe_number(floor_load.get("uls_floor_load_kN_m2", 0), 0)
            )

        if slab_thickness_mm <= 180 and governing_uls_load <= 12:
            bottom = "D8-150"
            top = "D8-200"
        elif slab_thickness_mm <= 220 and governing_uls_load <= 18:
            bottom = "D10-150"
            top = "D8-150"
        else:
            bottom = "D12-150"
            top = "D10-150"

        return {
            "element": "vloerplaat",
            "slab_thickness_mm": round(slab_thickness_mm, 0),
            "governing_uls_load_kN_m2": round(governing_uls_load, 2),
            "bottom_reinforcement": bottom,
            "top_reinforcement": top,
            "edge_reinforcement": "2D12 randwapening",
            "mesh_note": "wapening indicatief per hoofd- en dwarsrichting",
            "status": "INDICATIEF"
        }

    def build_beam_reinforcement(self, beam_width_mm, beam_height_mm):
        if beam_height_mm <= 450:
            bottom_bars = "2D16"
            top_bars = "2D12"
            stirrups = "D8-200"
        elif beam_height_mm <= 650:
            bottom_bars = "3D16"
            top_bars = "2D16"
            stirrups = "D8-150"
        else:
            bottom_bars = "4D20"
            top_bars = "2D16"
            stirrups = "D10-150"

        return {
            "element": "balk",
            "beam_width_mm": round(beam_width_mm, 0),
            "beam_height_mm": round(beam_height_mm, 0),
            "bottom_bars": bottom_bars,
            "top_bars": top_bars,
            "stirrups": stirrups,
            "support_extra_reinforcement": "extra bovenwapening boven steunpunten",
            "status": "INDICATIEF"
        }

    def build_column_reinforcement(self, column_width_mm, column_depth_mm):
        area_mm2 = column_width_mm * column_depth_mm

        if area_mm2 <= 90000:
            vertical_bars = "4D16"
            ties = "D8-150"
        elif area_mm2 <= 160000:
            vertical_bars = "6D16"
            ties = "D8-150"
        else:
            vertical_bars = "8D20"
            ties = "D10-150"

        return {
            "element": "kolom",
            "column_width_mm": round(column_width_mm, 0),
            "column_depth_mm": round(column_depth_mm, 0),
            "vertical_bars": vertical_bars,
            "ties": ties,
            "starter_bars": vertical_bars,
            "status": "INDICATIEF"
        }

    def build_wall_reinforcement(self, wall_thickness_mm):
        if wall_thickness_mm <= 180:
            vertical = "D8-200"
            horizontal = "D8-200"
        elif wall_thickness_mm <= 250:
            vertical = "D10-200"
            horizontal = "D8-200"
        else:
            vertical = "D12-200"
            horizontal = "D10-200"

        return {
            "element": "constructieve_wand",
            "wall_thickness_mm": round(wall_thickness_mm, 0),
            "vertical_reinforcement": vertical,
            "horizontal_reinforcement": horizontal,
            "edge_zone_reinforcement": "randzones nader bepalen",
            "status": "INDICATIEF"
        }

    def build_strip_foundation_reinforcement(
        self,
        strip_width_mm,
        strip_height_mm,
        line_load_kN_m
    ):
        if line_load_kN_m <= 80:
            bottom = "5D12 langswapening"
            transverse = "D8-200 dwarswapening"
        elif line_load_kN_m <= 150:
            bottom = "6D16 langswapening"
            transverse = "D10-200 dwarswapening"
        else:
            bottom = "8D16 langswapening"
            transverse = "D10-150 dwarswapening"

        return {
            "element": "strokenfundering",
            "strip_width_mm": round(strip_width_mm, 0),
            "strip_height_mm": round(strip_height_mm, 0),
            "governing_line_load_kN_m": round(line_load_kN_m, 2),
            "bottom_reinforcement": bottom,
            "top_reinforcement": "constructieve bovenwapening nader bepalen",
            "transverse_reinforcement": transverse,
            "status": "INDICATIEF"
        }

    def build_foundation_beam_reinforcement(
        self,
        foundation_beam_width_mm,
        foundation_beam_height_mm,
        line_load_kN_m
    ):
        if line_load_kN_m <= 80:
            bottom_bars = "3D16"
            top_bars = "2D12"
            stirrups = "D8-200"
        elif line_load_kN_m <= 150:
            bottom_bars = "4D16"
            top_bars = "2D16"
            stirrups = "D8-150"
        else:
            bottom_bars = "5D20"
            top_bars = "3D16"
            stirrups = "D10-150"

        return {
            "element": "funderingsbalk",
            "foundation_beam_width_mm": round(foundation_beam_width_mm, 0),
            "foundation_beam_height_mm": round(foundation_beam_height_mm, 0),
            "bottom_bars": bottom_bars,
            "top_bars": top_bars,
            "stirrups": stirrups,
            "status": "INDICATIEF"
        }

    def build_pad_reinforcement(self, foundation_design_result):
        pad_width = self.get_nested_number(
            foundation_design_result,
            ["pad_foundation", "recommended_width_mm"],
            1200
        )

        pad_length = self.get_nested_number(
            foundation_design_result,
            ["pad_foundation", "recommended_length_mm"],
            1200
        )

        pad_height = self.get_nested_number(
            foundation_design_result,
            ["pad_foundation", "recommended_height_mm"],
            400
        )

        return {
            "element": "poer",
            "pad_width_mm": round(pad_width, 0),
            "pad_length_mm": round(pad_length, 0),
            "pad_height_mm": round(pad_height, 0),
            "bottom_reinforcement_x": "D12-150",
            "bottom_reinforcement_y": "D12-150",
            "top_reinforcement": "constructief net D8-200",
            "punching_shear_note": "ponscontrole normatief uitvoeren",
            "status": "INDICATIEF"
        }

    def build_reinforcement_summary(
        self,
        slab_reinforcement,
        beam_reinforcement,
        column_reinforcement,
        wall_reinforcement,
        strip_foundation_reinforcement,
        foundation_beam_reinforcement,
        pad_reinforcement
    ):
        return {
            "status": "INDICATIEVE_WAPENING_SAMENVATTING",
            "slab": slab_reinforcement.get("bottom_reinforcement"),
            "beam": beam_reinforcement.get("bottom_bars"),
            "column": column_reinforcement.get("vertical_bars"),
            "wall": wall_reinforcement.get("vertical_reinforcement"),
            "strip_foundation": strip_foundation_reinforcement.get("bottom_reinforcement"),
            "foundation_beam": foundation_beam_reinforcement.get("bottom_bars"),
            "pad": pad_reinforcement.get("bottom_reinforcement_x")
        }

    def build_qa_qc_checks(
        self,
        slab_reinforcement,
        beam_reinforcement,
        column_reinforcement,
        strip_foundation_reinforcement,
        foundation_verification
    ):
        return [
            {
                "check": "vloerwapening_gegenereerd",
                "status": "OK" if slab_reinforcement.get("bottom_reinforcement") else "AANDACHT"
            },
            {
                "check": "balkwapening_gegenereerd",
                "status": "OK" if beam_reinforcement.get("bottom_bars") else "AANDACHT"
            },
            {
                "check": "kolomwapening_gegenereerd",
                "status": "OK" if column_reinforcement.get("vertical_bars") else "AANDACHT"
            },
            {
                "check": "funderingswapening_gegenereerd",
                "status": "OK" if strip_foundation_reinforcement.get("bottom_reinforcement") else "AANDACHT"
            },
            {
                "check": "funderingscontrole_beschikbaar",
                "status": "OK" if foundation_verification else "AANDACHT"
            }
        ]

    def build_report_sections(
        self,
        project_name,
        project_id,
        reinforcement_summary
    ):
        return [
            {
                "section_id": "wapening_samenvatting",
                "title": "Indicatieve wapening samenvatting",
                "content": (
                    f"Voor project {project_name} ({project_id}) zijn voorlopige "
                    "wapeningsvoorstellen opgesteld voor vloer, balken, kolommen, "
                    "wanden en fundering."
                )
            },
            {
                "section_id": "funderingswapening",
                "title": "Funderingswapening",
                "content": (
                    "Voorlopige strokenfunderingwapening: "
                    f"{reinforcement_summary.get('strip_foundation')}."
                )
            }
        ]

    def build_warnings(self, qa_qc_checks, line_load_kN_m):
        warnings = []

        if line_load_kN_m > 150:
            warnings.append("Hoge funderingslijnlast; wapening en fundering normatief verdiepen.")

        for check in qa_qc_checks:
            if check.get("status") != "OK":
                warnings.append(f"Aandachtspunt: {check.get('check')}.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de indicatieve wapeningsvoorstellen.")

        return warnings

    def get_nested_number(self, data, path, default_value):
        current = data

        for item in path:
            if not isinstance(current, dict):
                return default_value

            current = current.get(item)

        return self.safe_number(current, default_value)

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_structural_reinforcement_result(self):
        return self.structural_reinforcement_result

    def create_reinforcement_design(self, *args, **kwargs):
        return self.create_structural_reinforcement_design(*args, **kwargs)

    def generate_structural_reinforcement_design(self, *args, **kwargs):
        return self.create_structural_reinforcement_design(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_reinforcement_design(*args, **kwargs)
