from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/foundation_verification_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import FoundationVerificationEngine\n"

MAIN_CONTENT = r'''from datetime import datetime


class FoundationVerificationEngine:

    def __init__(self):
        self.foundation_verification_result = {}

    def create_foundation_verification(
        self,
        project_result=None,
        foundation_design_result=None,
        foundation_load_transfer_result=None,
        geo_result=None,
        assumptions_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        foundation_design_result = foundation_design_result or {}
        foundation_load_transfer_result = foundation_load_transfer_result or {}
        geo_result = geo_result or {}
        assumptions_result = assumptions_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        foundation_type = self.get_foundation_type(project_result, foundation_design_result)
        soil_profile = self.build_soil_profile(geo_result, assumptions_result)
        design_loads = self.build_design_loads(foundation_load_transfer_result, foundation_design_result)
        design_geometry = self.build_design_geometry(project_result, foundation_design_result)

        bearing_check = self.check_bearing_pressure(
            design_loads=design_loads,
            design_geometry=design_geometry,
            soil_profile=soil_profile
        )

        strip_check = self.check_strip_foundation(
            foundation_type=foundation_type,
            design_loads=design_loads,
            design_geometry=design_geometry,
            bearing_check=bearing_check
        )

        beam_check = self.check_foundation_beam(
            design_loads=design_loads,
            design_geometry=design_geometry
        )

        settlement_risk = self.check_settlement_risk(
            soil_profile=soil_profile,
            bearing_check=bearing_check
        )

        pile_option_check = self.check_pile_option(
            foundation_type=foundation_type,
            design_loads=design_loads,
            soil_profile=soil_profile
        )

        qa_qc_checks = self.build_qa_qc_checks(
            soil_profile=soil_profile,
            design_loads=design_loads,
            design_geometry=design_geometry,
            bearing_check=bearing_check,
            strip_check=strip_check,
            beam_check=beam_check
        )

        verification_summary = self.build_verification_summary(
            foundation_type=foundation_type,
            bearing_check=bearing_check,
            strip_check=strip_check,
            beam_check=beam_check,
            settlement_risk=settlement_risk,
            pile_option_check=pile_option_check
        )

        self.foundation_verification_result = {
            "engine": "FoundationVerificationEngine",
            "version": "1.0",
            "status": "FOUNDATION_VERIFICATION_GEREED",
            "calculation_level": "indicatieve funderingscontrole en verificatie",
            "project_id": project_id,
            "project_name": project_name,
            "foundation_type": foundation_type,
            "soil_profile": soil_profile,
            "design_loads": design_loads,
            "design_geometry": design_geometry,
            "bearing_check": bearing_check,
            "strip_foundation_check": strip_check,
            "foundation_beam_check": beam_check,
            "settlement_risk": settlement_risk,
            "pile_option_check": pile_option_check,
            "verification_summary": verification_summary,
            "qa_qc_checks": qa_qc_checks,
            "report_sections": self.build_report_sections(
                project_name=project_name,
                project_id=project_id,
                verification_summary=verification_summary
            ),
            "digital_twin_update": {
                "digital_twin_node": "foundation_verification",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "foundation_type": foundation_type,
                    "soil_profile": soil_profile,
                    "design_loads": design_loads,
                    "design_geometry": design_geometry,
                    "bearing_check": bearing_check,
                    "strip_foundation_check": strip_check,
                    "foundation_beam_check": beam_check,
                    "settlement_risk": settlement_risk,
                    "pile_option_check": pile_option_check,
                    "verification_summary": verification_summary
                }
            },
            "warnings": self.build_warnings(
                bearing_check=bearing_check,
                strip_check=strip_check,
                beam_check=beam_check,
                settlement_risk=settlement_risk
            ),
            "recommendation": self.build_recommendation(verification_summary),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Foundation Verification Engine v1.0 maakt een indicatieve funderingscontrole. "
                "De uitkomsten zijn geen definitieve normberekening."
            )
        }

        return self.foundation_verification_result

    def get_foundation_type(self, project_result, foundation_design_result):
        foundation_type = project_result.get(
            "foundation_type",
            foundation_design_result.get("foundation_type", "strokenfundering")
        )
        return str(foundation_type).lower()

    def build_soil_profile(self, geo_result, assumptions_result):
        allowable_bearing_pressure = self.safe_number(
            geo_result.get(
                "allowable_bearing_pressure_kN_m2",
                assumptions_result.get("allowable_bearing_pressure_kN_m2", 100.0)
            ),
            100.0
        )

        groundwater_level_m = self.safe_number(
            geo_result.get(
                "groundwater_level_m",
                assumptions_result.get("groundwater_level_m", -0.50)
            ),
            -0.50
        )

        soil_class = geo_result.get(
            "soil_class",
            assumptions_result.get("soil_class", "indicatief_grondprofiel")
        )

        settlement_sensitivity = geo_result.get(
            "settlement_sensitivity",
            assumptions_result.get("settlement_sensitivity", "nader_te_beoordelen")
        )

        return {
            "soil_class": soil_class,
            "allowable_bearing_pressure_kN_m2": round(allowable_bearing_pressure, 2),
            "groundwater_level_m": round(groundwater_level_m, 2),
            "settlement_sensitivity": settlement_sensitivity,
            "status": "INDICATIEF"
        }

    def build_design_loads(self, foundation_load_transfer_result, foundation_design_result):
        load_sources = [
            foundation_load_transfer_result,
            foundation_design_result
        ]

        combined_line_load = 0.0
        max_point_load = 0.0
        total_vertical_load = 0.0

        for source in load_sources:
            if not isinstance(source, dict):
                continue

            foundation_loads = source.get("foundation_line_loads", {})
            transfer_loads = source.get("foundation_load_transfer", {})
            design_loads = source.get("design_loads", {})

            combined_line_load = max(
                combined_line_load,
                self.safe_number(foundation_loads.get("combined_foundation_line_load_kN_m", 0), 0),
                self.safe_number(transfer_loads.get("combined_foundation_line_load_kN_m", 0), 0),
                self.safe_number(design_loads.get("combined_foundation_line_load_kN_m", 0), 0)
            )

            max_point_load = max(
                max_point_load,
                self.safe_number(source.get("max_point_load_kN", 0), 0),
                self.safe_number(design_loads.get("max_point_load_kN", 0), 0)
            )

            total_vertical_load = max(
                total_vertical_load,
                self.safe_number(source.get("total_vertical_load_kN", 0), 0),
                self.safe_number(design_loads.get("total_vertical_load_kN", 0), 0)
            )

        if combined_line_load <= 0:
            combined_line_load = 85.0

        if max_point_load <= 0:
            max_point_load = 250.0

        if total_vertical_load <= 0:
            total_vertical_load = combined_line_load * 40.0

        return {
            "combined_foundation_line_load_kN_m": round(combined_line_load, 2),
            "max_point_load_kN": round(max_point_load, 2),
            "total_vertical_load_kN": round(total_vertical_load, 2),
            "status": "INDICATIEF"
        }

    def build_design_geometry(self, project_result, foundation_design_result):
        strip_width_m = self.safe_number(
            project_result.get(
                "strip_foundation_width_m",
                foundation_design_result.get("strip_foundation_width_m", 1.50)
            ),
            1.50
        )

        strip_height_m = self.safe_number(
            project_result.get(
                "strip_foundation_height_m",
                foundation_design_result.get("strip_foundation_height_m", 0.40)
            ),
            0.40
        )

        beam_width_m = self.safe_number(
            project_result.get(
                "foundation_beam_width_m",
                foundation_design_result.get("foundation_beam_width_m", 0.50)
            ),
            0.50
        )

        beam_height_m = self.safe_number(
            project_result.get(
                "foundation_beam_height_m",
                foundation_design_result.get("foundation_beam_height_m", 0.60)
            ),
            0.60
        )

        foundation_depth_m = self.safe_number(
            project_result.get(
                "foundation_depth_m",
                foundation_design_result.get("foundation_depth_m", -0.50)
            ),
            -0.50
        )

        return {
            "strip_foundation_width_m": round(strip_width_m, 2),
            "strip_foundation_height_m": round(strip_height_m, 2),
            "foundation_beam_width_m": round(beam_width_m, 2),
            "foundation_beam_height_m": round(beam_height_m, 2),
            "foundation_depth_m": round(foundation_depth_m, 2),
            "status": "INDICATIEF"
        }

    def check_bearing_pressure(self, design_loads, design_geometry, soil_profile):
        line_load = design_loads.get("combined_foundation_line_load_kN_m", 0)
        strip_width = max(design_geometry.get("strip_foundation_width_m", 1.0), 0.1)
        allowable_pressure = soil_profile.get("allowable_bearing_pressure_kN_m2", 100.0)

        calculated_pressure = line_load / strip_width
        unity_check = calculated_pressure / max(allowable_pressure, 1.0)

        status = "OK" if unity_check <= 1.0 else "AANDACHT"

        return {
            "calculated_bearing_pressure_kN_m2": round(calculated_pressure, 2),
            "allowable_bearing_pressure_kN_m2": round(allowable_pressure, 2),
            "unity_check": round(unity_check, 2),
            "status": status
        }

    def check_strip_foundation(self, foundation_type, design_loads, design_geometry, bearing_check):
        strip_width = design_geometry.get("strip_foundation_width_m", 1.50)
        strip_height = design_geometry.get("strip_foundation_height_m", 0.40)
        line_load = design_loads.get("combined_foundation_line_load_kN_m", 0)

        required_width = line_load / max(bearing_check.get("allowable_bearing_pressure_kN_m2", 100.0), 1.0)
        width_status = "OK" if strip_width >= required_width else "AANDACHT"
        height_status = "OK" if strip_height >= 0.35 else "AANDACHT"

        return {
            "foundation_type": foundation_type,
            "provided_strip_width_m": round(strip_width, 2),
            "required_strip_width_m": round(required_width, 2),
            "provided_strip_height_m": round(strip_height, 2),
            "width_status": width_status,
            "height_status": height_status,
            "status": "OK" if width_status == "OK" and height_status == "OK" else "AANDACHT"
        }

    def check_foundation_beam(self, design_loads, design_geometry):
        beam_width = design_geometry.get("foundation_beam_width_m", 0.50)
        beam_height = design_geometry.get("foundation_beam_height_m", 0.60)
        line_load = design_loads.get("combined_foundation_line_load_kN_m", 0)

        minimum_height = 0.50 if line_load <= 100 else 0.70
        minimum_width = 0.40 if line_load <= 100 else 0.50

        width_status = "OK" if beam_width >= minimum_width else "AANDACHT"
        height_status = "OK" if beam_height >= minimum_height else "AANDACHT"

        return {
            "foundation_beam_width_m": round(beam_width, 2),
            "foundation_beam_height_m": round(beam_height, 2),
            "minimum_advised_width_m": round(minimum_width, 2),
            "minimum_advised_height_m": round(minimum_height, 2),
            "width_status": width_status,
            "height_status": height_status,
            "status": "OK" if width_status == "OK" and height_status == "OK" else "AANDACHT"
        }

    def check_settlement_risk(self, soil_profile, bearing_check):
        sensitivity = str(soil_profile.get("settlement_sensitivity", "nader_te_beoordelen")).lower()
        unity = bearing_check.get("unity_check", 0)

        risk = "laag"
        if unity > 1.0:
            risk = "hoog"
        elif unity > 0.75 or "slap" in sensitivity or "hoog" in sensitivity:
            risk = "middel"

        return {
            "settlement_risk_level": risk,
            "settlement_sensitivity": soil_profile.get("settlement_sensitivity"),
            "status": "AANDACHT" if risk in ["middel", "hoog"] else "OK"
        }

    def check_pile_option(self, foundation_type, design_loads, soil_profile):
        line_load = design_loads.get("combined_foundation_line_load_kN_m", 0)
        allowable_pressure = soil_profile.get("allowable_bearing_pressure_kN_m2", 100.0)

        pile_option_advised = False
        reason = "Strokenfundering blijft voorlopig mogelijk."

        if "paal" in foundation_type:
            pile_option_advised = True
            reason = "Paalfundering is als gekozen funderingstype opgegeven."
        elif line_load > 150 or allowable_pressure < 75:
            pile_option_advised = True
            reason = "Hoge lijnlast of lage draagkracht; paaloptie nader onderzoeken."

        return {
            "pile_option_advised": pile_option_advised,
            "reason": reason,
            "status": "AANDACHT" if pile_option_advised else "OK"
        }

    def build_qa_qc_checks(self, soil_profile, design_loads, design_geometry, bearing_check, strip_check, beam_check):
        return [
            {"check": "grondgegevens_beschikbaar", "status": "OK" if soil_profile.get("allowable_bearing_pressure_kN_m2", 0) > 0 else "AANDACHT"},
            {"check": "funderingslast_beschikbaar", "status": "OK" if design_loads.get("combined_foundation_line_load_kN_m", 0) > 0 else "AANDACHT"},
            {"check": "fundering_geometrie_beschikbaar", "status": "OK" if design_geometry.get("strip_foundation_width_m", 0) > 0 else "AANDACHT"},
            {"check": "gronddruk_toets", "status": bearing_check.get("status", "AANDACHT")},
            {"check": "strokenfundering_toets", "status": strip_check.get("status", "AANDACHT")},
            {"check": "funderingsbalk_toets", "status": beam_check.get("status", "AANDACHT")}
        ]

    def build_verification_summary(self, foundation_type, bearing_check, strip_check, beam_check, settlement_risk, pile_option_check):
        statuses = [
            bearing_check.get("status"),
            strip_check.get("status"),
            beam_check.get("status"),
            settlement_risk.get("status"),
            pile_option_check.get("status")
        ]

        overall_status = "OK" if all(status == "OK" for status in statuses) else "AANDACHT"

        return {
            "foundation_type": foundation_type,
            "overall_status": overall_status,
            "bearing_pressure_status": bearing_check.get("status"),
            "strip_foundation_status": strip_check.get("status"),
            "foundation_beam_status": beam_check.get("status"),
            "settlement_risk_status": settlement_risk.get("status"),
            "pile_option_status": pile_option_check.get("status")
        }

    def build_report_sections(self, project_name, project_id, verification_summary):
        return [
            {
                "section_id": "funderingsverificatie_samenvatting",
                "title": "Funderingsverificatie samenvatting",
                "content": (
                    f"Voor project {project_name} ({project_id}) is een indicatieve "
                    f"funderingsverificatie uitgevoerd. Status: {verification_summary.get('overall_status')}."
                )
            }
        ]

    def build_warnings(self, bearing_check, strip_check, beam_check, settlement_risk):
        warnings = []

        if bearing_check.get("status") != "OK":
            warnings.append("Gronddruk overschrijdt of benadert de voorlopige toelaatbare draagkracht.")

        if strip_check.get("status") != "OK":
            warnings.append("Strokenfundering voldoet indicatief niet volledig aan de voorlopige geometriecontrole.")

        if beam_check.get("status") != "OK":
            warnings.append("Funderingsbalk heeft indicatief extra controle of grotere afmetingen nodig.")

        if settlement_risk.get("status") != "OK":
            warnings.append("Zettingsrisico vraagt nadere geotechnische beoordeling.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de indicatieve funderingsverificatie.")

        return warnings

    def build_recommendation(self, verification_summary):
        if verification_summary.get("overall_status") == "OK":
            advice = "Voorlopig funderingsontwerp kan worden doorgezet naar detailberekening."
        else:
            advice = "Voer nadere funderingsoptimalisatie, geotechnische controle en normatieve berekening uit."

        return {
            "status": "FOUNDATION_VERIFICATION_ADVIES",
            "advice": advice,
            "next_steps": [
                "sondering en grondparameters projectspecifiek invoeren",
                "definitieve gronddrukcontrole uitvoeren",
                "wapeningsontwerp voor funderingsbalk maken",
                "zettingsberekening toevoegen",
                "paaloptie vergelijken indien lijnlast of zettingsrisico hoog is"
            ]
        }

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_foundation_verification_result(self):
        return self.foundation_verification_result

    def create_verification(self, *args, **kwargs):
        return self.create_foundation_verification(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_foundation_verification(*args, **kwargs)
'''


def run_command(command, check=True):
    print("")
    print(f">> {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if check and result.returncode != 0:
        raise SystemExit(result.returncode)

    return result


def status():
    run_command("git status", check=False)


def clean_outputs():
    run_command("git restore outputs", check=False)


def write_engine_files():
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    INIT_PATH.write_text(INIT_CONTENT, encoding="utf-8")
    MAIN_PATH.write_text(MAIN_CONTENT, encoding="utf-8")


def test_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.foundation_verification_engine.main")
    engine_class = getattr(module, "FoundationVerificationEngine")
    engine = engine_class()

    result = engine.create_foundation_verification(
        project_result={
            "project_id": "test",
            "project_name": "Testproject",
            "foundation_type": "strokenfundering"
        },
        foundation_load_transfer_result={
            "foundation_line_loads": {
                "combined_foundation_line_load_kN_m": 85.0
            }
        },
        foundation_design_result={
            "foundation_type": "strokenfundering",
            "strip_foundation_width_m": 1.50,
            "strip_foundation_height_m": 0.40,
            "foundation_beam_width_m": 0.50,
            "foundation_beam_height_m": 0.60,
            "foundation_depth_m": -0.50
        },
        geo_result={
            "allowable_bearing_pressure_kN_m2": 100.0,
            "groundwater_level_m": -0.50,
            "soil_class": "indicatief",
            "settlement_sensitivity": "laag"
        }
    )

    if result.get("status") != "FOUNDATION_VERIFICATION_GEREED":
        raise RuntimeError("Foundation Verification Engine gaf geen correcte status terug.")

    if result.get("bearing_check", {}).get("calculated_bearing_pressure_kN_m2", 0) <= 0:
        raise RuntimeError("Gronddrukcontrole is niet aangemaakt.")

    print("")
    print("FOUNDATION_VERIFICATION_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Overall: {result.get('verification_summary', {}).get('overall_status')}")
    print(f"Gronddruk: {result.get('bearing_check', {}).get('calculated_bearing_pressure_kN_m2')} kN/m2")


def create_test():
    clean_outputs()
    write_engine_files()
    test_engine()
    print("")
    print("FOUNDATION_VERIFICATION_ENGINE_V1_AANGEMAAKT")


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
    run_command("git add baoees/foundation_verification_engine/__init__.py")
    run_command("git add baoees/foundation_verification_engine/main.py")
    run_command("git add tools_create_foundation_verification_engine_v1.py")
    run_command('git commit -m "feat: add Foundation Verification Engine v1"')
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
