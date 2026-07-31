from pathlib import Path
import ast
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs/phoenix/parametric_architectural_bim_drawing_generator_v6_5_0.json"
PROJECT = ROOT / "configs/projects/generic_building_architectural_program_v6_5_0.json"
RUNNER = ROOT / "runners/PROJECT_PHOENIX_parametric_architectural_bim_drawing_generator_v6_5_0.py"


def function_nodes():
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def has_mkdir_call(function: ast.FunctionDef, target_kind: str) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "mkdir":
            continue

        # svg_* writers: path.parent.mkdir(...)
        if target_kind == "path_parent":
            owner = func.value
            if (
                isinstance(owner, ast.Attribute)
                and owner.attr == "parent"
                and isinstance(owner.value, ast.Name)
                and owner.value.id == "path"
            ):
                return True

        # BIM writers: output.mkdir(...)
        if target_kind == "output":
            owner = func.value
            if isinstance(owner, ast.Name) and owner.id == "output":
                return True
    return False


class ArchitecturalGeneratorTests(unittest.TestCase):
    def test_generic_mode_has_no_pilot_dependency(self):
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        self.assertEqual(cfg["project_mode"], "GENERIC_BUILDING_PROJECT")
        self.assertFalse(cfg["pilot_project_dependency"])

    def test_project_has_multiple_storeys_and_spaces(self):
        project = json.loads(PROJECT.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(project["storeys"]), 2)
        self.assertGreater(
            sum(len(storey["spaces"]) for storey in project["storeys"]),
            5,
        )

    def test_runner_valid_python(self):
        ast.parse(RUNNER.read_text(encoding="utf-8"))

    def test_runner_generates_bim_and_drawings(self):
        text = RUNNER.read_text(encoding="utf-8")
        for marker in (
            "generate_freecad",
            "generate_ifc",
            "svg_plan",
            "svg_elevation",
            "svg_section",
            "room_schedule.csv",
            "material_schedule.csv",
            "quantity_schedule.csv",
        ):
            self.assertIn(marker, text)

    def test_release_requires_professional_approval(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("permit_approved", text)
        self.assertIn("execution_approved", text)
        self.assertIn("automatic_professional_approval", text)


class ArchitecturalOutputDirectoryRecoveryTests(unittest.TestCase):
    def test_output_directories_are_initialized(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('output / "drawings"', text)
        self.assertIn('output / "schedules"', text)
        self.assertIn('output / "bim"', text)
        self.assertIn("mkdir(parents=True, exist_ok=True)", text)

    def test_svg_writers_defensively_create_parent_directories(self):
        functions = function_nodes()
        for function_name in ("svg_plan", "svg_elevation", "svg_section"):
            self.assertIn(function_name, functions)
            self.assertTrue(
                has_mkdir_call(functions[function_name], "path_parent"),
                f"{function_name} lacks path.parent.mkdir(...)",
            )

    def test_bim_writers_defensively_create_output_directories(self):
        functions = function_nodes()
        for function_name in ("generate_freecad", "generate_ifc"):
            self.assertIn(function_name, functions)
            self.assertTrue(
                has_mkdir_call(functions[function_name], "output"),
                f"{function_name} lacks output.mkdir(...)",
            )

    def test_generated_artifacts_are_non_empty(self):
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("required_generated_files", text)
        self.assertIn("Architectural artifact missing or empty", text)

    def test_no_fragile_formatted_source_assertion_remains(self):
        text = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            '"def svg_plan(storey: dict[str, Any], path: Path) -> None:\\\\n"',
            text,
        )


if __name__ == "__main__":
    unittest.main()
