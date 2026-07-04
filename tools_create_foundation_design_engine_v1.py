from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/foundation_design_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import FoundationDesignEngine\n"

MAIN_CONTENT = r'''from datetime import datetime


class FoundationDesignEngine:

    def __init__(self):
        self.foundation_design_result = {}

    def create_foundation_design(
        self,
        project_result=None,
        foundation_load_transfer_result=None,
        geo_result=None,
        assumptions_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        foundation_load_transfer_result = foundation_load_transfer_result or {}
        geo_result = geo_result or {}
        assumptions_result = assumptions_result or {}

        project_id = project_result.get(
            "project_id",
            project_result.get("id", "unknown_project")
        )

        project_name = project_result.get(
            "project_name",
            project_result.get("name", "Onbekend project")
        )

        foundation_type_preference = project_result.get(
            "foundation_type_preference",
            assumptions_result.get("foundation_type_preference", "strokenfundering")
        )

        combined_line_load = self.get_combined_line_load(
            project_result=project_result,
            foundation_load_transfer_result=foundation_load_transfer_result
        )

        point_load = self.get_point_load(
            project_result=project_result,
            foundation_load_transfer_result=foundation_load_transfer_result
        )

        bearing_capacity = self.get_bearing_capacity(
            project_result=project_result,
            geo_result=geo_result,
            assumptions_result=assumptions_result
        )

        groundwater_level = self.get_groundwater_level(
            project_result=project_result,
            geo_result=geo_result,
            assumptions_result=assumptions_result
        )

        strip_foundation = self.build_strip_foundation_design(
            combined_line_load_kN_m=combined_line_load,
            bearing_capacity_kN_m2=bearing_capacity,
            groundwater_level_m=groundwater_level,
            project_result=project_result
        )

        foundation_beams = self.build_foundation_beam_design(
            combined_line_load_kN_m=combined_line_load,
            strip_foundation=strip_foundation,
            project_result=project_result
        )

        pad_footings = self.build_pad_footing_design(
            point_load_kN=point_load,
            bearing_capacity_kN_m2=bearing_capacity,
            project_result=project_result
        )

        pile_option = self.build_preliminary_pile_option(
            point_load_kN=point_load,
            combined_line_load_kN_m=combined_line_load,
            bearing_capacity_kN_m2=bearing_capacity,
            project_result=project_result,
            geo_result=geo_result
        )

        foundation_zones = self.build_foundation_zones(
            combined_line_load_kN_m=combined_line_load,
            strip_foundation=strip_foundation,
            pad_footings=pad_footings,
            pile_option=pile_option
        )

        selected_concept = self.select_foundation_concept(
            foundation_type_preference=foundation_type_preference,
            strip_foundation=strip_foundation,
            pad_footings=pad_footings,
            pile_option=pile_option,
            combined_line_load_kN_m=combined_line_load
        )

        qa_qc_checks = self.build_qa_qc_checks(
            combined_line_load_kN_m=combined_line_load,
            point_load_kN=point_load,
            bearing_capacity_kN_m2=bearing_capacity,
            selected_concept=selected_concept
        )

        self.foundation_design_result = {
            "engine": "FoundationDesignEngine",
            "version": "1.0",
            "status": "FOUNDATION_DESIGN_GEREED",
            "calculation_level": "indicatief funderingsconcept en basisafmetingen",
            "project_id": project_id,
            "project_name": project_name,
            "foundation_type_preference": foundation_type_preference,
            "input_loads": {
                "combined_line_load_kN_m": round(combined_line_load, 2),
                "point_load_kN": round(point_load, 2),
                "bearing_capacity_kN_m2": round(bearing_capacity, 2),
                "groundwater_level_m": round(groundwater_level, 2)
            },
            "strip_foundation": strip_foundation,
            "foundation_beams": foundation_beams,
            "pad_footings": pad_footings,
            "preliminary_pile_option": pile_option,
            "foundation_zones": foundation_zones,
            "selected_concept": selected_concept,
            "qa_qc_checks": qa_qc_checks,
            "report_sections": self.build_report_sections(
                project_name=project_name,
                project_id=project_id,
                selected_concept=selected_concept,
                strip_foundation=strip_foundation,
                pad_footings=pad_footings,
                pile_option=pile_option
            ),
            "digital_twin_update": {
                "digital_twin_node": "foundation_design",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "input_loads": {
                        "combined_line_load_kN_m": round(combined_line_load, 2),
                        "point_load_kN": round(point_load, 2),
                        "bearing_capacity_kN_m2": round(bearing_capacity, 2),
                        "groundwater_level_m": round(groundwater_level, 2)
                    },
                    "strip_foundation": strip_foundation,
                    "foundation_beams": foundation_beams,
                    "pad_footings": pad_footings,
                    "preliminary_pile_option": pile_option,
                    "foundation_zones": foundation_zones,
                    "selected_concept": selected_concept
                }
            },
            "warnings": self.build_warnings(
                combined_line_load_kN_m=combined_line_load,
                bearing_capacity_kN_m2=bearing_capacity,
                groundwater_level_m=groundwater_level,
                selected_concept=selected_concept
            ),
            "recommendation": self.build_recommendation(selected_concept),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Foundation Design Engine v1.0 maakt een indicatief funderingsconcept. "
                "Definitieve funderingsafmetingen moeten normatief worden gecontroleerd."
            )
        }

        return self.foundation_design_result

    def get_combined_line_load(self, project_result, foundation_load_transfer_result):
        value = project_result.get("combined_foundation_line_load_kN_m")

        if value is None:
            value = foundation_load_transfer_result.get(
                "foundation_line_loads",
                {}
            ).get("combined_foundation_line_load_kN_m")

        if value is None:
            value = foundation_load_transfer_result.get(
                "load_transfer_summary",
                {}
            ).get("max_foundation_line_load_kN_m")

        return self.safe_number(value, 75.0)

    def get_point_load(self, project_result, foundation_load_transfer_result):
        value = project_result.get("foundation_point_load_kN")

        if value is None:
            value = foundation_load_transfer_result.get(
                "foundation_point_loads",
                {}
            ).get("max_point_load_kN")

        if value is None:
            value = foundation_load_transfer_result.get(
                "load_transfer_summary",
                {}
            ).get("max_point_load_kN")

        return self.safe_number(value, 250.0)

    def get_bearing_capacity(self, project_result, geo_result, assumptions_result):
        value = project_result.get("allowable_bearing_capacity_kN_m2")

        if value is None:
            value = geo_result.get("allowable_bearing_capacity_kN_m2")

        if value is None:
            value = assumptions_result.get("allowable_bearing_capacity_kN_m2")

        return self.safe_number(value, 100.0)

    def get_groundwater_level(self, project_result, geo_result, assumptions_result):
        value = project_result.get("groundwater_level_m")

        if value is None:
            value = geo_result.get("groundwater_level_m")

        if value is None:
            value = assumptions_result.get("groundwater_level_m", -0.50)

        return self.safe_number(value, -0.50)

    def build_strip_foundation_design(
        self,
        combined_line_load_kN_m,
        bearing_capacity_kN_m2,
        groundwater_level_m,
        project_result
    ):
        preferred_width = self.safe_number(
            project_result.get("strip_foundation_width_m", 1.50),
            1.50
        )

        preferred_height = self.safe_number(
            project_result.get("strip_foundation_height_m", 0.40),
            0.40
        )

        required_width = combined_line_load_kN_m / max(bearing_capacity_kN_m2, 1)
        required_width_with_margin = required_width * 1.25
        proposed_width = max(preferred_width, required_width_with_margin)

        status = "INDICATIEF_OK"

        if proposed_width > 2.50:
            status = "AANDACHT_HOGE_LIJNLAST"

        if groundwater_level_m >= -0.75:
            groundwater_note = "grondwaterstand vraagt aandacht bij ontgraving en uitvoering"
        else:
            groundwater_note = "geen direct grondwateralarm op basis van indicatieve invoer"

        return {
            "foundation_type": "strokenfundering",
            "combined_line_load_kN_m": round(combined_line_load_kN_m, 2),
            "bearing_capacity_kN_m2": round(bearing_capacity_kN_m2, 2),
            "required_width_m": round(required_width, 2),
            "required_width_with_margin_m": round(required_width_with_margin, 2),
            "proposed_width_m": round(proposed_width, 2),
            "proposed_height_m": round(preferred_height, 2),
            "standard_reference": "BAOEES standaard: strook 1,50 m breed en 0,40 m hoog tenzij berekening anders vereist",
            "groundwater_note": groundwater_note,
            "status": status
        }

    def build_foundation_beam_design(self, combined_line_load_kN_m, strip_foundation, project_result):
        beam_width = self.safe_number(
            project_result.get("foundation_beam_width_m", 0.50),
            0.50
        )

        beam_height = self.safe_number(
            project_result.get("foundation_beam_height_m", 0.60),
            0.60
        )

        if combined_line_load_kN_m > 150:
            beam_height = max(beam_height, 0.70)

        if combined_line_load_kN_m > 250:
            beam_height = max(beam_height, 0.80)
            beam_width = max(beam_width, 0.60)

        return {
            "foundation_beam_type": "gewapende funderingsbalk in hart strook",
            "beam_width_m": round(beam_width, 2),
            "beam_height_m": round(beam_height, 2),
            "position": "hart van strokenfundering",
            "related_strip_width_m": strip_foundation.get("proposed_width_m"),
            "status": "INDICATIEF"
        }

    def build_pad_footing_design(self, point_load_kN, bearing_capacity_kN_m2, project_result):
        required_area = point_load_kN / max(bearing_capacity_kN_m2, 1)
        required_area_with_margin = required_area * 1.25
        side_length = required_area_with_margin ** 0.5

        minimum_side = self.safe_number(project_result.get("minimum_pad_side_m", 1.20), 1.20)
        proposed_side = max(minimum_side, side_length)

        proposed_height = self.safe_number(project_result.get("pad_footing_height_m", 0.40), 0.40)

        if point_load_kN > 400:
            proposed_height = max(proposed_height, 0.50)

        if point_load_kN > 800:
            proposed_height = max(proposed_height, 0.65)

        return {
            "foundation_type": "poerfundering",
            "point_load_kN": round(point_load_kN, 2),
            "bearing_capacity_kN_m2": round(bearing_capacity_kN_m2, 2),
            "required_area_m2": round(required_area, 2),
            "required_area_with_margin_m2": round(required_area_with_margin, 2),
            "proposed_side_m": round(proposed_side, 2),
            "proposed_height_m": round(proposed_height, 2),
            "status": "INDICATIEF"
        }

    def build_preliminary_pile_option(
        self,
        point_load_kN,
        combined_line_load_kN_m,
        bearing_capacity_kN_m2,
        project_result,
        geo_result
    ):
        pile_capacity = self.safe_number(
            project_result.get(
                "preliminary_pile_capacity_kN",
                geo_result.get("preliminary_pile_capacity_kN", 350)
            ),
            350
        )

        piles_per_point = int(max(round(point_load_kN / max(pile_capacity, 1) + 0.49), 1))
        pile_need_score = "laag"

        if bearing_capacity_kN_m2 < 75 or combined_line_load_kN_m > 200:
            pile_need_score = "middel"

        if bearing_capacity_kN_m2 < 50 or combined_line_load_kN_m > 300:
            pile_need_score = "hoog"

        return {
            "foundation_type": "paaloptie_voorlopig",
            "preliminary_pile_capacity_kN": round(pile_capacity, 2),
            "point_load_kN": round(point_load_kN, 2),
            "estimated_piles_per_point": piles_per_point,
            "pile_need_score": pile_need_score,
            "status": "VOORLOPIG_ALTERNATIEF"
        }

    def build_foundation_zones(self, combined_line_load_kN_m, strip_foundation, pad_footings, pile_option):
        if combined_line_load_kN_m <= 100:
            load_zone = "lichte_funderingszone"
        elif combined_line_load_kN_m <= 200:
            load_zone = "middelzware_funderingszone"
        else:
            load_zone = "zware_funderingszone"

        return [
            {
                "zone_id": "FZ-01",
                "zone_type": load_zone,
                "line_load_kN_m": round(combined_line_load_kN_m, 2),
                "preferred_solution": strip_foundation.get("foundation_type"),
                "strip_width_m": strip_foundation.get("proposed_width_m"),
                "pad_side_m": pad_footings.get("proposed_side_m"),
                "pile_option_score": pile_option.get("pile_need_score"),
                "status": "INDICATIEF"
            }
        ]

    def select_foundation_concept(
        self,
        foundation_type_preference,
        strip_foundation,
        pad_footings,
        pile_option,
        combined_line_load_kN_m
    ):
        selected_type = foundation_type_preference
        reason = "gekozen op basis van projectvoorkeur"

        if foundation_type_preference == "strokenfundering" and combined_line_load_kN_m > 300:
            selected_type = "paaloptie_onderzoeken"
            reason = "lijnlast is hoog; paaloptie moet worden onderzocht"

        if foundation_type_preference == "palen":
            selected_type = "paaloptie_voorlopig"
            reason = "projectvoorkeur geeft palen aan"

        return {
            "selected_foundation_concept": selected_type,
            "reason": reason,
            "strip_foundation_reference": strip_foundation.get("status"),
            "pad_footing_reference": pad_footings.get("status"),
            "pile_option_reference": pile_option.get("pile_need_score"),
            "status": "CONCEPT_GESELECTEERD"
        }

    def build_qa_qc_checks(self, combined_line_load_kN_m, point_load_kN, bearing_capacity_kN_m2, selected_concept):
        return [
            {
                "check": "lijnlast_beschikbaar",
                "status": "OK" if combined_line_load_kN_m > 0 else "AANDACHT"
            },
            {
                "check": "puntlast_beschikbaar",
                "status": "OK" if point_load_kN > 0 else "AANDACHT"
            },
            {
                "check": "draagkracht_beschikbaar",
                "status": "OK" if bearing_capacity_kN_m2 > 0 else "AANDACHT"
            },
            {
                "check": "concept_geselecteerd",
                "status": "OK" if selected_concept.get("status") == "CONCEPT_GESELECTEERD" else "AANDACHT"
            }
        ]

    def build_report_sections(self, project_name, project_id, selected_concept, strip_foundation, pad_footings, pile_option):
        return [
            {
                "section_id": "funderingsontwerp_samenvatting",
                "title": "Funderingsontwerp samenvatting",
                "content": (
                    f"Voor project {project_name} ({project_id}) is een indicatief "
                    f"funderingsconcept geselecteerd: {selected_concept.get('selected_foundation_concept')}."
                )
            },
            {
                "section_id": "strokenfundering",
                "title": "Strokenfundering",
                "content": (
                    f"Voorgestelde strookbreedte: {strip_foundation.get('proposed_width_m')} m, "
                    f"hoogte: {strip_foundation.get('proposed_height_m')} m."
                )
            },
            {
                "section_id": "poeren_en_palen",
                "title": "Poeren en paaloptie",
                "content": (
                    f"Indicatieve poermaat: {pad_footings.get('proposed_side_m')} x "
                    f"{pad_footings.get('proposed_side_m')} m. "
                    f"Paalbehoefte-score: {pile_option.get('pile_need_score')}."
                )
            }
        ]

    def build_warnings(self, combined_line_load_kN_m, bearing_capacity_kN_m2, groundwater_level_m, selected_concept):
        warnings = []

        if combined_line_load_kN_m > 200:
            warnings.append("Hoge funderingslijnlast; controleer strookbreedte, balkhoogte en zettingen.")

        if bearing_capacity_kN_m2 < 75:
            warnings.append("Lage indicatieve draagkracht; paaloptie of grondverbetering onderzoeken.")

        if groundwater_level_m >= -0.75:
            warnings.append("Grondwaterstand ligt ondiep; uitvoering, bemaling en ontgraving controleren.")

        if selected_concept.get("selected_foundation_concept") == "paaloptie_onderzoeken":
            warnings.append("Geselecteerd concept vraagt aanvullend paalonderzoek.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in het indicatieve funderingsontwerp.")

        return warnings

    def build_recommendation(self, selected_concept):
        return {
            "status": "FOUNDATION_DESIGN_ADVIES",
            "selected_foundation_concept": selected_concept.get("selected_foundation_concept"),
            "advice": (
                "Gebruik dit concept als basis voor normatieve funderingsberekening, "
                "wapeningsontwerp, zettingscontrole en koppeling met geotechniek."
            ),
            "next_steps": [
                "geotechnische draagkracht controleren",
                "zettingsberekening toevoegen",
                "wapeningsvoorstel voor strook en funderingsbalk uitwerken",
                "paaloptie onderbouwen indien nodig",
                "funderingsplan genereren"
            ]
        }

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_foundation_design_result(self):
        return self.foundation_design_result

    def create_design(self, *args, **kwargs):
        return self.create_foundation_design(*args, **kwargs)

    def generate_foundation_design(self, *args, **kwargs):
        return self.create_foundation_design(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_foundation_design(*args, **kwargs)
'''


def run_command(command, check=True):
    print("")
    print(f">> {command}")

    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if check and result.returncode != 0:
        raise SystemExit(result.returncode)

    return result


def write_engine_files():
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    INIT_PATH.write_text(INIT_CONTENT, encoding="utf-8")
    MAIN_PATH.write_text(MAIN_CONTENT, encoding="utf-8")


def test_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.foundation_design_engine.main")
    engine_class = getattr(module, "FoundationDesignEngine")
    engine = engine_class()

    result = engine.create_foundation_design(
        project_result={
            "project_id": "test",
            "project_name": "Testproject",
            "foundation_type_preference": "strokenfundering"
        },
        foundation_load_transfer_result={
            "foundation_line_loads": {
                "combined_foundation_line_load_kN_m": 85.0
            },
            "foundation_point_loads": {
                "max_point_load_kN": 280.0
            }
        },
        geo_result={
            "allowable_bearing_capacity_kN_m2": 100,
            "groundwater_level_m": -0.50
        }
    )

    if result.get("status") != "FOUNDATION_DESIGN_GEREED":
        raise RuntimeError("Foundation Design Engine gaf geen correcte status terug.")

    if result.get("strip_foundation", {}).get("proposed_width_m", 0) <= 0:
        raise RuntimeError("Foundation Design Engine gaf geen strookbreedte terug.")

    if result.get("selected_concept", {}).get("status") != "CONCEPT_GESELECTEERD":
        raise RuntimeError("Foundation Design Engine selecteerde geen concept.")

    print("")
    print("FOUNDATION_DESIGN_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Concept: {result.get('selected_concept', {}).get('selected_foundation_concept')}")
    print(f"Strookbreedte: {result.get('strip_foundation', {}).get('proposed_width_m')} m")


def status():
    run_command("git status", check=False)


def clean_outputs():
    run_command("git restore outputs", check=False)


def create_test():
    clean_outputs()
    write_engine_files()
    test_engine()
    print("")
    print("FOUNDATION_DESIGN_ENGINE_V1_AANGEMAAKT")
    status()


def test_baoees():
    result = run_command("python run_baoees_v3.py", check=False)
    clean_outputs()

    combined_output = result.stdout + result.stderr

    if "=== PROJECTANALYSE GEREED ===" not in combined_output:
        print("")
        print("BAOEES_TEST_NIET_OK")
        raise SystemExit(1)

    print("")
    print("BAOEES_TEST_OK")


def commit():
    create_test()
    test_baoees()
    clean_outputs()

    run_command("git add baoees/foundation_design_engine/__init__.py")
    run_command("git add baoees/foundation_design_engine/main.py")
    run_command("git add tools_create_foundation_design_engine_v1.py")
    run_command('git commit -m "feat: add Foundation Design Engine v1"')
    run_command("git push")
    status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["status", "create-test", "test-baoees", "commit"]
    )

    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "create-test":
        create_test()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "commit":
        commit()


if __name__ == "__main__":
    main()
