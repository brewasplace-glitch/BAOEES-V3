from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess

ELEMENT_DIR = Path("baoees/element_load_engine")
ELEMENT_INIT = ELEMENT_DIR / "__init__.py"
ELEMENT_MAIN = ELEMENT_DIR / "main.py"

BAD_TEMP_FILES = [Path("tools_create_element_load_engine_v1.py")]
ELEMENT_INIT_CONTENT = "from .main import ElementLoadEngine\n"

ELEMENT_MAIN_CONTENT = r'''from datetime import datetime


class ElementLoadEngine:

    def __init__(self):
        self.element_load_result = {}

    def create_element_load_analysis(
        self,
        project_result=None,
        structural_load_result=None,
        building_technical_result=None,
        geo_result=None,
        assumptions_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        structural_load_result = structural_load_result or {}
        building_technical_result = building_technical_result or {}
        building_profile = building_technical_result.get("building_profile", {})
        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        area = self.safe_number(
            project_result.get(
                "gross_floor_area_m2",
                structural_load_result.get("gross_floor_area_m2", building_profile.get("gross_floor_area_m2", 100))
            ),
            100
        )
        if area <= 0:
            area = 100.0

        floors = int(max(self.safe_number(
            project_result.get(
                "number_of_floors",
                structural_load_result.get("number_of_floors", building_profile.get("number_of_floors", 1))
            ),
            1
        ), 1))

        g_load = self.safe_number(structural_load_result.get("permanent_loads", {}).get("total_dead_load_kN_m2", 5.60), 5.60)
        q_load = self.safe_number(structural_load_result.get("imposed_loads", {}).get("main_imposed_load_kN_m2", 2.50), 2.50)
        roof_g = self.safe_number(structural_load_result.get("roof_loads", {}).get("roof_dead_load_kN_m2", 0.85), 0.85)
        roof_q = self.safe_number(structural_load_result.get("roof_loads", {}).get("roof_live_load_kN_m2", 0.75), 0.75)

        floor_loads = self.build_floor_loads(area, floors, g_load, q_load)
        roof_element_loads = self.build_roof_loads(area, roof_g, roof_q)
        wall_line_loads = self.build_wall_line_loads(project_result, area, floors)
        column_loads = self.build_column_loads(project_result, area, floors, g_load, q_load)
        foundation_line_loads = self.build_foundation_line_loads(structural_load_result, wall_line_loads, column_loads)
        load_takeoff_summary = self.build_summary(floor_loads, roof_element_loads, wall_line_loads, column_loads, foundation_line_loads)

        self.element_load_result = {
            "engine": "ElementLoadEngine",
            "version": "1.0",
            "status": "ELEMENT_LOAD_ANALYSIS_GEREED",
            "calculation_level": "indicatieve elementlasten en belastingafdracht",
            "project_id": project_id,
            "project_name": project_name,
            "gross_floor_area_m2": area,
            "number_of_floors": floors,
            "floor_loads": floor_loads,
            "roof_element_loads": roof_element_loads,
            "wall_line_loads": wall_line_loads,
            "column_loads": column_loads,
            "foundation_line_loads": foundation_line_loads,
            "load_takeoff_summary": load_takeoff_summary,
            "qa_qc_checks": self.build_qa_qc_checks(area, floors, floor_loads, foundation_line_loads),
            "digital_twin_update": {
                "digital_twin_node": "element_loads",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "floor_loads": floor_loads,
                    "roof_element_loads": roof_element_loads,
                    "wall_line_loads": wall_line_loads,
                    "column_loads": column_loads,
                    "foundation_line_loads": foundation_line_loads,
                    "load_takeoff_summary": load_takeoff_summary
                }
            },
            "warnings": self.build_warnings(area, column_loads, foundation_line_loads),
            "recommendation": {
                "status": "ELEMENT_LOAD_ADVIES",
                "advice": "Gebruik deze elementlasten als invoer voor vloer-, dak-, kolom-, wand- en funderingsberekening."
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }
        return self.element_load_result

    def build_floor_loads(self, area, floors, g_load, q_load):
        floor_area = area / floors
        floor_loads = []
        for floor_number in range(1, floors + 1):
            permanent_total = g_load * floor_area
            imposed_total = q_load * floor_area
            floor_loads.append({
                "floor_number": floor_number,
                "floor_area_m2": round(floor_area, 2),
                "permanent_load_kN_m2": round(g_load, 2),
                "imposed_load_kN_m2": round(q_load, 2),
                "total_permanent_load_kN": round(permanent_total, 2),
                "total_imposed_load_kN": round(imposed_total, 2),
                "total_service_load_kN": round(permanent_total + imposed_total, 2),
                "uls_floor_load_kN_m2": round(1.35 * g_load + 1.50 * q_load, 2)
            })
        return floor_loads

    def build_roof_loads(self, area, roof_g, roof_q):
        return {
            "roof_area_m2": round(area, 2),
            "roof_dead_load_kN_m2": round(roof_g, 2),
            "roof_live_load_kN_m2": round(roof_q, 2),
            "total_roof_dead_load_kN": round(roof_g * area, 2),
            "total_roof_live_load_kN": round(roof_q * area, 2),
            "uls_roof_load_kN_m2": round(1.35 * roof_g + 1.50 * roof_q, 2),
            "status": "INDICATIEF"
        }

    def build_wall_line_loads(self, project_result, area, floors):
        perimeter = (area ** 0.5) * 4.0
        wall_height = self.safe_number(project_result.get("wall_height_m", 3.0), 3.0)
        wall_weight = self.safe_number(project_result.get("wall_weight_kN_m2", 2.5), 2.5)
        wall_line_load = wall_height * wall_weight * floors
        return {
            "estimated_perimeter_m": round(perimeter, 2),
            "wall_height_m": round(wall_height, 2),
            "wall_weight_kN_m2": round(wall_weight, 2),
            "wall_line_load_kN_m": round(wall_line_load, 2),
            "total_wall_load_kN": round(wall_line_load * perimeter, 2),
            "status": "INDICATIEF"
        }

    def build_column_loads(self, project_result, area, floors, g_load, q_load):
        grid_spacing = self.safe_number(project_result.get("grid_spacing_m", 5.0), 5.0)
        tributary_area = grid_spacing * grid_spacing
        column_count = int(max(round(area / tributary_area), 1))
        service_load_per_column = (g_load + q_load) * tributary_area * floors
        uls_load_per_column = (1.35 * g_load + 1.50 * q_load) * tributary_area * floors
        return {
            "grid_spacing_m": round(grid_spacing, 2),
            "tributary_area_m2": round(tributary_area, 2),
            "estimated_column_count": column_count,
            "service_load_per_column_kN": round(service_load_per_column, 2),
            "uls_load_per_column_kN": round(uls_load_per_column, 2),
            "status": "INDICATIEF"
        }

    def build_foundation_line_loads(self, structural_load_result, wall_line_loads, column_loads):
        foundation_precheck = structural_load_result.get("foundation_load_precheck", {})
        estimated_line_load = self.safe_number(foundation_precheck.get("estimated_line_load_kN_m", 0), 0)
        wall_line_load = self.safe_number(wall_line_loads.get("wall_line_load_kN_m", 0), 0)
        column_equivalent_line_load = self.safe_number(column_loads.get("service_load_per_column_kN", 0), 0) / 5.0
        combined_line_load = max(estimated_line_load, wall_line_load + column_equivalent_line_load)
        return {
            "estimated_structural_line_load_kN_m": round(estimated_line_load, 2),
            "wall_line_load_kN_m": round(wall_line_load, 2),
            "column_equivalent_line_load_kN_m": round(column_equivalent_line_load, 2),
            "combined_foundation_line_load_kN_m": round(combined_line_load, 2),
            "status": "VOORCONTROLE"
        }

    def build_summary(self, floor_loads, roof_element_loads, wall_line_loads, column_loads, foundation_line_loads):
        return {
            "total_floor_service_load_kN": round(sum(item["total_service_load_kN"] for item in floor_loads), 2),
            "total_roof_service_load_kN": round(roof_element_loads["total_roof_dead_load_kN"] + roof_element_loads["total_roof_live_load_kN"], 2),
            "total_wall_load_kN": wall_line_loads["total_wall_load_kN"],
            "estimated_column_count": column_loads["estimated_column_count"],
            "combined_foundation_line_load_kN_m": foundation_line_loads["combined_foundation_line_load_kN_m"],
            "status": "INDICATIEF"
        }

    def build_qa_qc_checks(self, area, floors, floor_loads, foundation_line_loads):
        return [
            {"check": "oppervlakte_beschikbaar", "status": "OK" if area > 0 else "AANDACHT"},
            {"check": "bouwlagen_beschikbaar", "status": "OK" if floors > 0 else "AANDACHT"},
            {"check": "vloerlasten_gegenereerd", "status": "OK" if len(floor_loads) > 0 else "AANDACHT"},
            {"check": "funderingslijnlast_bepaald", "status": "OK" if foundation_line_loads.get("combined_foundation_line_load_kN_m", 0) > 0 else "AANDACHT"}
        ]

    def build_warnings(self, area, column_loads, foundation_line_loads):
        warnings = []
        if area <= 0:
            warnings.append("BVO/oppervlakte ontbreekt; tijdelijke rekenwaarde gebruikt.")
        if column_loads.get("estimated_column_count", 0) <= 1:
            warnings.append("Kolommen zijn indicatief; stramien moet projectspecifiek worden bepaald.")
        if foundation_line_loads.get("combined_foundation_line_load_kN_m", 0) <= 0:
            warnings.append("Funderingslijnlast kon niet betrouwbaar worden bepaald.")
        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in de indicatieve elementlastanalyse.")
        return warnings

    def safe_number(self, value, default_value=0):
        try:
            return float(value)
        except Exception:
            return default_value

    def get_element_load_result(self):
        return self.element_load_result

    def create_load_analysis(self, *args, **kwargs):
        return self.create_element_load_analysis(*args, **kwargs)

    def generate_element_load_analysis(self, *args, **kwargs):
        return self.create_element_load_analysis(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_element_load_analysis(*args, **kwargs)
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


def clean():
    for path in BAD_TEMP_FILES:
        if path.exists():
            path.unlink()
            print(f"Verwijderd: {path}")
    run_command("git restore outputs", check=False)


def create_element_load_engine():
    clean()
    ELEMENT_DIR.mkdir(parents=True, exist_ok=True)
    ELEMENT_INIT.write_text(ELEMENT_INIT_CONTENT, encoding="utf-8")
    ELEMENT_MAIN.write_text(ELEMENT_MAIN_CONTENT, encoding="utf-8")
    test_element_load_engine()
    print("")
    print("ELEMENT_LOAD_ENGINE_V1_AANGEMAAKT")


def test_element_load_engine():
    py_compile.compile(str(ELEMENT_MAIN), doraise=True)
    importlib.invalidate_caches()
    module = importlib.import_module("baoees.element_load_engine.main")
    engine_class = getattr(module, "ElementLoadEngine")
    engine = engine_class()
    result = engine.create_element_load_analysis(
        project_result={"project_id": "test", "project_name": "Testproject", "gross_floor_area_m2": 180, "number_of_floors": 2},
        structural_load_result={
            "gross_floor_area_m2": 180,
            "number_of_floors": 2,
            "permanent_loads": {"total_dead_load_kN_m2": 5.60},
            "imposed_loads": {"main_imposed_load_kN_m2": 1.75},
            "roof_loads": {"roof_dead_load_kN_m2": 0.85, "roof_live_load_kN_m2": 0.75},
            "foundation_load_precheck": {"estimated_line_load_kN_m": 42.50}
        },
        building_technical_result={"building_profile": {"gross_floor_area_m2": 180, "number_of_floors": 2, "roof_type": "plat_dak"}}
    )
    if result.get("status") != "ELEMENT_LOAD_ANALYSIS_GEREED":
        raise RuntimeError("Element Load Engine gaf geen correcte status terug.")
    if len(result.get("floor_loads", [])) != 2:
        raise RuntimeError("Element Load Engine genereerde niet 2 vloerlastlagen.")
    line_load = result.get("foundation_line_loads", {}).get("combined_foundation_line_load_kN_m", 0)
    if line_load <= 0:
        raise RuntimeError("Element Load Engine genereerde geen funderingslijnlast.")
    print("")
    print("ELEMENT_LOAD_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Aantal vloerlastlagen: {len(result.get('floor_loads', []))}")
    print(f"Funderingslijnlast: {line_load} kN/m")


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


def commit_element_load_engine():
    create_element_load_engine()
    test_baoees()
    run_command("git restore outputs", check=False)
    run_command("git add baoees/element_load_engine/__init__.py")
    run_command("git add baoees/element_load_engine/main.py")
    run_command("git add tools_baoees_dev_runner.py")
    run_command('git commit -m "feat: add Element Load Engine v1"')
    run_command("git push")
    status()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["clean", "create-element-load-engine", "test-element-load-engine", "test-baoees", "commit-element-load-engine", "status"])
    args = parser.parse_args()
    if args.command == "clean":
        clean()
    elif args.command == "create-element-load-engine":
        create_element_load_engine()
    elif args.command == "test-element-load-engine":
        test_element_load_engine()
    elif args.command == "test-baoees":
        test_baoees()
    elif args.command == "commit-element-load-engine":
        commit_element_load_engine()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
