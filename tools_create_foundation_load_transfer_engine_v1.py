from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/foundation_load_transfer_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import FoundationLoadTransferEngine\n"

MAIN_CONTENT = r"""from datetime import datetime


class FoundationLoadTransferEngine:

    def __init__(self):
        self.foundation_load_transfer_result = {}

    def create_foundation_load_transfer_analysis(
        self,
        project_result=None,
        structural_load_result=None,
        element_load_result=None,
        geo_result=None,
        assumptions_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        structural_load_result = structural_load_result or {}
        element_load_result = element_load_result or {}
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

        foundation_system = project_result.get(
            "foundation_system",
            project_result.get("foundation_type", "strokenfundering")
        )

        gross_floor_area_m2 = self.safe_number(
            project_result.get(
                "gross_floor_area_m2",
                element_load_result.get(
                    "gross_floor_area_m2",
                    structural_load_result.get("gross_floor_area_m2", 100.0)
                )
            ),
            100.0
        )

        if gross_floor_area_m2 <= 0:
            gross_floor_area_m2 = 100.0

        groundwater_level_m = self.safe_number(
            project_result.get(
                "groundwater_level_m",
                geo_result.get(
                    "groundwater_level_m",
                    assumptions_result.get("groundwater_level_m", -0.50)
                )
            ),
            -0.50
        )

        foundation_level_m = self.safe_number(
            project_result.get(
                "foundation_level_m",
                assumptions_result.get("foundation_level_m", -0.50)
            ),
            -0.50
        )

        element_foundation_line_load = element_load_result.get(
            "foundation_line_loads",
            {}
        )

        structural_foundation_precheck = structural_load_result.get(
            "foundation_load_precheck",
            {}
        )

        governing_line_load_kN_m = self.determine_governing_line_load(
            element_foundation_line_load=element_foundation_line_load,
            structural_foundation_precheck=structural_foundation_precheck,
            project_result=project_result
        )

        strip_foundation_result = self.build_strip_foundation_transfer(
            project_result=project_result,
            gross_floor_area_m2=gross_floor_area_m2,
            governing_line_load_kN_m=governing_line_load_kN_m
        )

        isolated_footing_result = self.build_isolated_footing_transfer(
            project_result=project_result,
            element_load_result=element_load_result
        )

        pile_reaction_precheck = self.build_pile_reaction_precheck(
            project_result=project_result,
            governing_line_load_kN_m=governing_line_load_kN_m,
            isolated_footing_result=isolated_footing_result
        )

        geotechnical_interface = self.build_geotechnical_interface(
            geo_result=geo_result,
            groundwater_level_m=groundwater_level_m,
            foundation_level_m=foundation_level_m,
            strip_foundation_result=strip_foundation_result,
            isolated_footing_result=isolated_footing_result,
            pile_reaction_precheck=pile_reaction_precheck
        )

        qa_qc_checks = self.build_qa_qc_checks(
            foundation_system=foundation_system,
            governing_line_load_kN_m=governing_line_load_kN_m,
            strip_foundation_result=strip_foundation_result,
            geotechnical_interface=geotechnical_interface
        )

        load_transfer_summary = self.build_load_transfer_summary(
            foundation_system=foundation_system,
            governing_line_load_kN_m=governing_line_load_kN_m,
            strip_foundation_result=strip_foundation_result,
            isolated_footing_result=isolated_footing_result,
            pile_reaction_precheck=pile_reaction_precheck
        )

        self.foundation_load_transfer_result = {
            "engine": "FoundationLoadTransferEngine",
            "version": "1.0",
            "status": "FOUNDATION_LOAD_TRANSFER_GEREED",
            "calculation_level": "indicatieve funderingsbelastingafdracht",
            "project_id": project_id,
            "project_name": project_name,
            "foundation_system": foundation_system,
            "gross_floor_area_m2": gross_floor_area_m2,
            "groundwater_level_m": groundwater_level_m,
            "foundation_level_m": foundation_level_m,
            "governing_line_load_kN_m": governing_line_load_kN_m,
            "strip_foundation_transfer": strip_foundation_result,
            "isolated_footing_transfer": isolated_footing_result,
            "pile_reaction_precheck": pile_reaction_precheck,
            "geotechnical_interface": geotechnical_interface,
            "load_transfer_summary": load_transfer_summary,
            "qa_qc_checks": qa_qc_checks,
            "report_sections": self.build_report_sections(
                project_name=project_name,
                project_id=project_id,
                load_transfer_summary=load_transfer_summary
            ),
            "digital_twin_update": {
                "digital_twin_node": "foundation_load_transfer",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "foundation_system": foundation_system,
                    "governing_line_load_kN_m": governing_line_load_kN_m,
                    "strip_foundation_transfer": strip_foundation_result,
                    "isolated_footing_transfer": isolated_footing_result,
                    "pile_reaction_precheck": pile_reaction_precheck,
                    "geotechnical_interface": geotechnical_interface,
                    "load_transfer_summary": load_transfer_summary
                }
            },
            "warnings": self.build_warnings(
                foundation_system=foundation_system,
                groundwater_level_m=groundwater_level_m,
                foundation_level_m=foundation_level_m,
                geotechnical_interface=geotechnical_interface
            ),
            "recommendation": self.build_recommendation(foundation_system),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Foundation Load Transfer Engine v1.0 maakt een indicatieve "
                "voorcontrole van funderingsbelastingafdracht. Dit is nog geen "
                "normatieve funderingsberekening."
            )
        }

        return self.foundation_load_transfer_result

    def determine_governing_line_load(
        self,
        element_foundation_line_load,
        structural_foundation_precheck,
        project_result
    ):
        element_line_load = self.safe_number(
            element_foundation_line_load.get("combined_foundation_line_load_kN_m", 0),
            0
        )

        structural_line_load = self.safe_number(
            structural_foundation_precheck.get("estimated_line_load_kN_m", 0),
            0
        )

        project_line_load = self.safe_number(
            project_result.get("foundation_line_load_kN_m", 0),
            0
        )

        governing = max(element_line_load, structural_line_load, project_line_load)

        if governing <= 0:
            governing = 40.0

        return round(governing, 2)

    def build_strip_foundation_transfer(
        self,
        project_result,
        gross_floor_area_m2,
        governing_line_load_kN_m
    ):
        strip_width_m = self.safe_number(
            project_result.get("strip_foundation_width_m", 1.50),
            1.50
        )

        strip_height_m = self.safe_number(
            project_result.get("strip_foundation_height_m", 0.40),
            0.40
        )

        beam_width_m = self.safe_number(
            project_result.get("foundation_beam_width_m", 0.50),
            0.50
        )

        beam_height_m = self.safe_number(
            project_result.get("foundation_beam_height_m", 0.60),
            0.60
        )

        estimated_perimeter_m = self.safe_number(
            project_result.get("estimated_foundation_length_m", 0),
            0
        )

        if estimated_perimeter_m <= 0:
            estimated_perimeter_m = (gross_floor_area_m2 ** 0.5) * 4.0

        bearing_pressure_kN_m2 = governing_line_load_kN_m / max(strip_width_m, 0.01)

        total_strip_load_kN = governing_line_load_kN_m * estimated_perimeter_m

        return {
            "foundation_type": "strokenfundering",
            "strip_width_m": round(strip_width_m, 2),
            "strip_height_m": round(strip_height_m, 2),
            "foundation_beam_width_m": round(beam_width_m, 2),
            "foundation_beam_height_m": round(beam_height_m, 2),
            "estimated_foundation_length_m": round(estimated_perimeter_m, 2),
            "governing_line_load_kN_m": round(governing_line_load_kN_m, 2),
            "indicative_bearing_pressure_kN_m2": round(bearing_pressure_kN_m2, 2),
            "total_strip_load_kN": round(total_strip_load_kN, 2),
            "status": "VOORCONTROLE"
        }

    def build_isolated_footing_transfer(self, project_result, element_load_result):
        column_loads = element_load_result.get("column_loads", {})

        service_column_load = self.safe_number(
            column_loads.get(
                "service_load_per_column_kN",
                project_result.get("service_load_per_column_kN", 0)
            ),
            0
        )

        uls_column_load = self.safe_number(
            column_loads.get(
                "uls_load_per_column_kN",
                project_result.get("uls_load_per_column_kN", 0)
            ),
            0
        )

        column_count = int(
            max(
                self.safe_number(
                    column_loads.get(
                        "estimated_column_count",
                        project_result.get("estimated_column_count", 0)
                    ),
                    0
                ),
                0
            )
        )

        footing_width_m = self.safe_number(
            project_result.get("isolated_footing_width_m", 1.20),
            1.20
        )

        footing_length_m = self.safe_number(
            project_result.get("isolated_footing_length_m", 1.20),
            1.20
        )

        footing_area_m2 = footing_width_m * footing_length_m

        bearing_pressure_kN_m2 = 0
        if service_column_load > 0:
            bearing_pressure_kN_m2 = service_column_load / max(footing_area_m2, 0.01)

        return {
            "foundation_type": "poeren",
            "estimated_column_count": column_count,
            "service_load_per_column_kN": round(service_column_load, 2),
            "uls_load_per_column_kN": round(uls_column_load, 2),
            "footing_width_m": round(footing_width_m, 2),
            "footing_length_m": round(footing_length_m, 2),
            "footing_area_m2": round(footing_area_m2, 2),
            "indicative_bearing_pressure_kN_m2": round(bearing_pressure_kN_m2, 2),
            "status": "VOORCONTROLE"
        }

    def build_pile_reaction_precheck(
        self,
        project_result,
        governing_line_load_kN_m,
        isolated_footing_result
    ):
        pile_spacing_m = self.safe_number(
            project_result.get("pile_spacing_m", 3.0),
            3.0
        )

        piles_per_pilecap = int(
            max(
                self.safe_number(project_result.get("piles_per_pilecap", 1), 1),
                1
            )
        )

        line_based_pile_reaction = governing_line_load_kN_m * pile_spacing_m

        column_based_pile_reaction = isolated_footing_result.get(
            "service_load_per_column_kN",
            0
        ) / max(piles_per_pilecap, 1)

        governing_pile_reaction = max(
            line_based_pile_reaction,
            column_based_pile_reaction
        )

        return {
            "foundation_type": "palenfundering_voorcontrole",
            "pile_spacing_m": round(pile_spacing_m, 2),
            "piles_per_pilecap": piles_per_pilecap,
            "line_based_pile_reaction_kN": round(line_based_pile_reaction, 2),
            "column_based_pile_reaction_kN": round(column_based_pile_reaction, 2),
            "governing_pile_reaction_kN": round(governing_pile_reaction, 2),
            "status": "OPTIONEEL_VOORCONTROLE"
        }

    def build_geotechnical_interface(
        self,
        geo_result,
        groundwater_level_m,
        foundation_level_m,
        strip_foundation_result,
        isolated_footing_result,
        pile_reaction_precheck
    ):
        indicative_allowable_bearing_pressure = self.safe_number(
            geo_result.get("indicative_allowable_bearing_pressure_kN_m2", 100.0),
            100.0
        )

        strip_pressure = strip_foundation_result.get(
            "indicative_bearing_pressure_kN_m2",
            0
        )

        footing_pressure = isolated_footing_result.get(
            "indicative_bearing_pressure_kN_m2",
            0
        )

        max_pressure = max(strip_pressure, footing_pressure)

        bearing_pressure_status = "OK"
        if max_pressure > indicative_allowable_bearing_pressure:
            bearing_pressure_status = "AANDACHT"

        groundwater_status = "OK"
        if foundation_level_m <= groundwater_level_m:
            groundwater_status = "AANDACHT"

        return {
            "indicative_allowable_bearing_pressure_kN_m2": round(
                indicative_allowable_bearing_pressure,
                2
            ),
            "max_indicative_bearing_pressure_kN_m2": round(max_pressure, 2),
            "bearing_pressure_status": bearing_pressure_status,
            "groundwater_level_m": round(groundwater_level_m, 2),
            "foundation_level_m": round(foundation_level_m, 2),
            "groundwater_status": groundwater_status,
            "governing_pile_reaction_kN": pile_reaction_precheck.get(
                "governing_pile_reaction_kN",
                0
            ),
            "status": "READY_FOR_GEO_ENGINE"
        }

    def build_load_transfer_summary(
        self,
        foundation_system,
        governing_line_load_kN_m,
        strip_foundation_result,
        isolated_footing_result,
        pile_reaction_precheck
    ):
        return {
            "foundation_system": foundation_system,
            "governing_line_load_kN_m": round(governing_line_load_kN_m, 2),
            "strip_bearing_pressure_kN_m2": strip_foundation_result.get(
                "indicative_bearing_pressure_kN_m2",
                0
            ),
            "footing_bearing_pressure_kN_m2": isolated_footing_result.get(
                "indicative_bearing_pressure_kN_m2",
                0
            ),
            "governing_pile_reaction_kN": pile_reaction_precheck.get(
                "governing_pile_reaction_kN",
                0
            ),
            "status": "INDICATIEF"
        }

    def build_qa_qc_checks(
        self,
        foundation_system,
        governing_line_load_kN_m,
        strip_foundation_result,
        geotechnical_interface
    ):
        return [
            {
                "check": "funderingssysteem_beschikbaar",
                "status": "OK" if foundation_system else "AANDACHT"
            },
            {
                "check": "maatgevende_lijnlast_beschikbaar",
                "status": "OK" if governing_line_load_kN_m > 0 else "AANDACHT"
            },
            {
                "check": "strookbreedte_beschikbaar",
                "status": "OK" if strip_foundation_result.get("strip_width_m", 0) > 0 else "AANDACHT"
            },
            {
                "check": "grondspanning_voorcontrole",
                "status": geotechnical_interface.get("bearing_pressure_status", "AANDACHT")
            },
            {
                "check": "grondwater_voorcontrole",
                "status": geotechnical_interface.get("groundwater_status", "AANDACHT")
            }
        ]

    def build_report_sections(self, project_name, project_id, load_transfer_summary):
        return [
            {
                "section_id": "funderingsbelastingafdracht_samenvatting",
                "title": "Funderingsbelastingafdracht samenvatting",
                "content": (
                    f"Voor project {project_name} ({project_id}) is een indicatieve "
                    "belastingafdracht naar de fundering bepaald."
                )
            },
            {
                "section_id": "maatgevende_lijnlast",
                "title": "Maatgevende funderingslijnlast",
                "content": (
                    "Indicatieve maatgevende funderingslijnlast: "
                    f"{load_transfer_summary.get('governing_line_load_kN_m')} kN/m."
                )
            }
        ]

    def build_warnings(
        self,
        foundation_system,
        groundwater_level_m,
        foundation_level_m,
        geotechnical_interface
    ):
        warnings = []

        if foundation_system not in ["strokenfundering", "palenfundering", "poeren"]:
            warnings.append(
                "Funderingssysteem is algemeen of onbekend; controleer projectspecifieke keuze."
            )

        if foundation_level_m <= groundwater_level_m:
            warnings.append(
                "Funderingsniveau ligt op of onder grondwaterniveau; bemaling of aangepast ontwerp beoordelen."
            )

        if geotechnical_interface.get("bearing_pressure_status") == "AANDACHT":
            warnings.append(
                "Indicatieve grondspanning overschrijdt de aangenomen toelaatbare grondspanning."
            )

        if not warnings:
            warnings.append(
                "Geen kritieke waarschuwingen in de indicatieve funderingsbelastingafdracht."
            )

        return warnings

    def build_recommendation(self, foundation_system):
        return {
            "status": "FOUNDATION_LOAD_TRANSFER_ADVIES",
            "foundation_system": foundation_system,
            "advice": (
                "Gebruik deze funderingsbelastingafdracht als invoer voor de "
                "geotechnische controle, strokenfunderingberekening, poerberekening "
                "of palenfunderingvoorcontrole."
            ),
            "next_steps": [
                "koppelen aan geotechnische engine",
                "werkelijke funderingslijnen uit plattegrond halen",
                "grondspanning normatief controleren",
                "zettingscontrole toevoegen",
                "wapeningsvoorstel voor strook en funderingsbalk genereren"
            ]
        }

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_foundation_load_transfer_result(self):
        return self.foundation_load_transfer_result

    def create_load_transfer_analysis(self, *args, **kwargs):
        return self.create_foundation_load_transfer_analysis(*args, **kwargs)

    def create_load_analysis(self, *args, **kwargs):
        return self.create_foundation_load_transfer_analysis(*args, **kwargs)

    def generate_foundation_load_transfer_analysis(self, *args, **kwargs):
        return self.create_foundation_load_transfer_analysis(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_foundation_load_transfer_analysis(*args, **kwargs)
"""


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


def clean():
    run_command("git restore outputs", check=False)


def create_foundation_engine():
    clean()

    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    INIT_PATH.write_text(INIT_CONTENT, encoding="utf-8")
    MAIN_PATH.write_text(MAIN_CONTENT, encoding="utf-8")

    test_foundation_engine()

    print("")
    print("FOUNDATION_LOAD_TRANSFER_ENGINE_V1_AANGEMAAKT")


def test_foundation_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.foundation_load_transfer_engine.main")
    engine_class = getattr(module, "FoundationLoadTransferEngine")
    engine = engine_class()

    result = engine.create_foundation_load_transfer_analysis(
        project_result={
            "project_id": "test",
            "project_name": "Testproject",
            "gross_floor_area_m2": 180,
            "foundation_system": "strokenfundering",
            "groundwater_level_m": -0.50,
            "foundation_level_m": -0.50
        },
        structural_load_result={
            "gross_floor_area_m2": 180,
            "foundation_load_precheck": {
                "estimated_line_load_kN_m": 42.50
            }
        },
        element_load_result={
            "gross_floor_area_m2": 180,
            "foundation_line_loads": {
                "combined_foundation_line_load_kN_m": 62.50
            },
            "column_loads": {
                "estimated_column_count": 7,
                "service_load_per_column_kN": 367.50,
                "uls_load_per_column_kN": 510.00
            }
        },
        geo_result={
            "indicative_allowable_bearing_pressure_kN_m2": 100.0,
            "groundwater_level_m": -0.50
        }
    )

    if result.get("status") != "FOUNDATION_LOAD_TRANSFER_GEREED":
        raise RuntimeError("Foundation Load Transfer Engine gaf geen correcte status terug.")

    if result.get("governing_line_load_kN_m", 0) <= 0:
        raise RuntimeError("Geen maatgevende funderingslijnlast gegenereerd.")

    if result.get("strip_foundation_transfer", {}).get(
        "indicative_bearing_pressure_kN_m2",
        0
    ) <= 0:
        raise RuntimeError("Geen indicatieve grondspanning gegenereerd.")

    print("")
    print("FOUNDATION_LOAD_TRANSFER_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Maatgevende lijnlast: {result.get('governing_line_load_kN_m')} kN/m")
    print(
        "Indicatieve grondspanning strook: "
        f"{result.get('strip_foundation_transfer', {}).get('indicative_bearing_pressure_kN_m2')} kN/m2"
    )


def test_baoees():
    result = run_command("python run_baoees_v3.py", check=False)

    run_command("git restore outputs", check=False)

    combined_output = result.stdout + result.stderr

    if "=== PROJECTANALYSE GEREED ===" not in combined_output:
        print("")
        print("BAOEES_TEST_NIET_OK")
        raise SystemExit(1)

    print("")
    print("BAOEES_TEST_OK")


def status():
    run_command("git status", check=False)


def commit_foundation_engine():
    create_foundation_engine()
    test_baoees()

    run_command("git restore outputs", check=False)
    run_command("git add baoees/foundation_load_transfer_engine/__init__.py")
    run_command("git add baoees/foundation_load_transfer_engine/main.py")
    run_command("git add tools_create_foundation_load_transfer_engine_v1.py")
    run_command('git commit -m "feat: add Foundation Load Transfer Engine v1"')
    run_command("git push")
    status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "clean",
            "create-test",
            "test-engine",
            "test-baoees",
            "commit",
            "status"
        ]
    )

    args = parser.parse_args()

    if args.command == "clean":
        clean()
    elif args.command == "create-test":
        create_foundation_engine()
    elif args.command == "test-engine":
        test_foundation_engine()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "commit":
        commit_foundation_engine()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
