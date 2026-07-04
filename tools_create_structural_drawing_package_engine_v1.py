from pathlib import Path
import argparse
import importlib
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/structural_drawing_package_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"

INIT_CONTENT = "from .main import StructuralDrawingPackageEngine\n"

MAIN_CONTENT = r"""from datetime import datetime


class StructuralDrawingPackageEngine:

    def __init__(self):
        self.drawing_package_result = {}

    def create_structural_drawing_package(
        self,
        project_result=None,
        foundation_design_result=None,
        foundation_verification_result=None,
        structural_element_sizing_result=None,
        structural_reinforcement_result=None,
        structural_calculation_report_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        foundation_design_result = foundation_design_result or {}
        foundation_verification_result = foundation_verification_result or {}
        structural_element_sizing_result = structural_element_sizing_result or {}
        structural_reinforcement_result = structural_reinforcement_result or {}
        structural_calculation_report_result = structural_calculation_report_result or {}

        project_id = project_result.get("project_id", project_result.get("id", "unknown_project"))
        project_name = project_result.get("project_name", project_result.get("name", "Onbekend project"))

        drawing_index = self.build_drawing_index(project_id, project_name)

        foundation_drawing = self.build_drawing(
            drawing_number="S-200",
            title="Funderingsplan",
            source_statuses={
                "foundation_design": foundation_design_result.get("status", "ONTBREEKT"),
                "foundation_verification": foundation_verification_result.get("status", "ONTBREEKT")
            },
            layers=[
                "strokenfundering",
                "funderingsbalken",
                "poeren",
                "paaloptie_voorlopig",
                "funderingszones"
            ],
            data={
                "foundation_design": foundation_design_result.get("foundation_design", {}),
                "foundation_verification": foundation_verification_result.get("foundation_verification", {})
            }
        )

        structural_plan_drawing = self.build_drawing(
            drawing_number="S-100",
            title="Constructieve plattegronden",
            source_statuses={
                "structural_element_sizing": structural_element_sizing_result.get("status", "ONTBREEKT")
            },
            layers=[
                "draaglijnen",
                "vloervelden",
                "balken",
                "kolommen",
                "wanden",
                "dakconstructie"
            ],
            data={
                "element_dimensions": structural_element_sizing_result.get("element_dimensions", {}),
                "sizing_summary": structural_element_sizing_result.get("sizing_summary", {})
            }
        )

        reinforcement_drawing = self.build_drawing(
            drawing_number="S-300",
            title="Wapeningsvoorstellen",
            source_statuses={
                "structural_reinforcement": structural_reinforcement_result.get("status", "ONTBREEKT")
            },
            layers=[
                "vloerwapening",
                "balkwapening",
                "kolomwapening",
                "wandwapening",
                "funderingswapening"
            ],
            data={
                "reinforcement_summary": structural_reinforcement_result.get("reinforcement_summary", {}),
                "reinforcement_proposals": structural_reinforcement_result.get("reinforcement_proposals", {})
            }
        )

        detail_drawing = self.build_drawing(
            drawing_number="S-400",
            title="Constructieve details",
            source_statuses={
                "foundation_design": foundation_design_result.get("status", "ONTBREEKT"),
                "structural_element_sizing": structural_element_sizing_result.get("status", "ONTBREEKT"),
                "structural_reinforcement": structural_reinforcement_result.get("status", "ONTBREEKT")
            },
            layers=[
                "detail_strookfundering",
                "detail_poer_kolom",
                "detail_balk_vloer",
                "detail_wand_vloer"
            ],
            data={
                "notes": [
                    "Details zijn conceptueel.",
                    "Definitieve maatvoering en wapening moeten normatief worden uitgewerkt."
                ]
            }
        )

        drawings = [
            foundation_drawing,
            structural_plan_drawing,
            reinforcement_drawing,
            detail_drawing
        ]

        qa_qc_checks = self.build_qa_qc_checks(drawings)

        self.drawing_package_result = {
            "engine": "StructuralDrawingPackageEngine",
            "version": "1.0",
            "status": "STRUCTURAL_DRAWING_PACKAGE_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "calculation_level": "concept constructietekenpakket",
            "drawing_index": drawing_index,
            "drawings": drawings,
            "export_package": {
                "status": "EXPORT_PACKAGE_VOORBEREID",
                "recommended_formats": [
                    "PDF",
                    "DXF",
                    "DWG",
                    "IFC",
                    "FreeCAD",
                    "JSON"
                ]
            },
            "qa_qc_checks": qa_qc_checks,
            "digital_twin_update": {
                "digital_twin_node": "structural_drawing_package",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "drawing_index": drawing_index,
                    "drawings": drawings
                }
            },
            "warnings": self.build_warnings(qa_qc_checks),
            "recommendation": {
                "status": "STRUCTURAL_DRAWING_PACKAGE_ADVIES",
                "advice": (
                    "Gebruik dit als concept tekeninformatie. Voor definitieve tekeningen "
                    "zijn CAD/BIM-export, maatvoering, schaalcontrole en constructeurcontrole nodig."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.drawing_package_result

    def build_drawing_index(self, project_id, project_name):
        return [
            {"drawing_number": "S-000", "title": "Tekeningenindex", "project_id": project_id, "project_name": project_name},
            {"drawing_number": "S-100", "title": "Constructieve plattegronden"},
            {"drawing_number": "S-200", "title": "Funderingsplan"},
            {"drawing_number": "S-300", "title": "Wapeningsvoorstellen"},
            {"drawing_number": "S-400", "title": "Constructieve details"}
        ]

    def build_drawing(self, drawing_number, title, source_statuses, layers, data):
        status = "GEREED"

        if all(value == "ONTBREEKT" for value in source_statuses.values()):
            status = "AANDACHT"

        return {
            "drawing_number": drawing_number,
            "title": title,
            "status": status,
            "source_statuses": source_statuses,
            "drawing_layers": layers,
            "data": data
        }

    def build_qa_qc_checks(self, drawings):
        checks = []

        for drawing in drawings:
            checks.append(
                {
                    "check": drawing.get("drawing_number"),
                    "title": drawing.get("title"),
                    "status": "OK" if drawing.get("status") != "AANDACHT" else "AANDACHT"
                }
            )

        return checks

    def build_warnings(self, qa_qc_checks):
        warnings = []

        for check in qa_qc_checks:
            if check.get("status") == "AANDACHT":
                warnings.append(f"Tekeningonderdeel vraagt aandacht: {check.get('title')}.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen in het concept constructietekenpakket.")

        return warnings

    def get_drawing_package_result(self):
        return self.drawing_package_result

    def create_drawing_package(self, *args, **kwargs):
        return self.create_structural_drawing_package(*args, **kwargs)

    def generate_structural_drawing_package(self, *args, **kwargs):
        return self.create_structural_drawing_package(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_structural_drawing_package(*args, **kwargs)
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


def write_files():
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    INIT_PATH.write_text(INIT_CONTENT, encoding="utf-8")
    MAIN_PATH.write_text(MAIN_CONTENT, encoding="utf-8")


def test_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.structural_drawing_package_engine.main")
    engine_class = getattr(module, "StructuralDrawingPackageEngine")
    engine = engine_class()

    result = engine.create_structural_drawing_package(
        project_result={"project_id": "test", "project_name": "Testproject"},
        foundation_design_result={"status": "FOUNDATION_DESIGN_GEREED"},
        foundation_verification_result={"status": "FOUNDATION_VERIFICATION_GEREED"},
        structural_element_sizing_result={"status": "STRUCTURAL_ELEMENT_SIZING_GEREED"},
        structural_reinforcement_result={"status": "STRUCTURAL_REINFORCEMENT_GEREED"}
    )

    if result.get("status") != "STRUCTURAL_DRAWING_PACKAGE_GEREED":
        raise RuntimeError("Structural Drawing Package Engine gaf geen correcte status terug.")

    if len(result.get("drawing_index", [])) < 5:
        raise RuntimeError("Structural Drawing Package Engine genereerde te weinig tekeningen.")

    print("")
    print("STRUCTURAL_DRAWING_PACKAGE_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Aantal indexregels: {len(result.get('drawing_index', []))}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("STRUCTURAL_DRAWING_PACKAGE_ENGINE_V1_AANGEMAAKT")


def test_baoees():
    result = run_command("python run_baoees_v3.py", check=False)
    run_command("git restore outputs", check=False)

    combined_output = result.stdout + result.stderr

    if "=== PROJECTANALYSE GEREED ===" not in combined_output:
        print("BAOEES_TEST_NIET_OK")
        raise SystemExit(1)

    print("")
    print("BAOEES_TEST_OK")


def commit():
    create_test()
    test_baoees()

    run_command("git restore outputs", check=False)
    run_command("git add baoees/structural_drawing_package_engine/__init__.py")
    run_command("git add baoees/structural_drawing_package_engine/main.py")
    run_command("git add tools_create_structural_drawing_package_engine_v1.py")
    run_command('git commit -m "feat: add Structural Drawing Package Engine v1"')
    run_command("git push")
    run_command("git status", check=False)


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "status",
            "create-test",
            "test-baoees",
            "commit"
        ]
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
