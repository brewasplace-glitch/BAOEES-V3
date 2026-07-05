from pathlib import Path
import argparse
import importlib
import json
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/brewster_auto_build_script_factory_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"
OUTPUT_DIR = Path("outputs")
FACTORY_JSON_PATH = OUTPUT_DIR / "brewster_auto_build_script_factory_v1.json"
FACTORY_TXT_PATH = OUTPUT_DIR / "brewster_auto_build_script_factory_v1.txt"

INIT_CONTENT = "from .main import BrewsterAutoBuildScriptFactoryEngine\n"

MAIN_CONTENT = '''from datetime import datetime


class BrewsterAutoBuildScriptFactoryEngine:

    def __init__(self):
        self.factory_result = {}

    def create_script_factory_plan(
        self,
        project_result=None,
        brewster_task_orchestrator_result=None,
        brewster_automation_roadmap_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        orchestrator = brewster_task_orchestrator_result or {}
        roadmap = brewster_automation_roadmap_result or {}

        project_id = project_result.get("project_id", "BREWAS_BAOEES")
        project_name = project_result.get("project_name", "BREWSTER ENGINEERING WIZARD")

        next_task = orchestrator.get("next_task", {}) or self.build_fallback_next_task()
        script_blueprint = self.build_script_blueprint(next_task)
        file_blueprints = self.build_file_blueprints(next_task)
        safety_blueprint = self.build_safety_blueprint(next_task)
        command_blueprint = self.build_command_blueprint(script_blueprint)
        supported_task_types = self.build_supported_task_types()

        self.factory_result = {
            "engine": "BrewsterAutoBuildScriptFactoryEngine",
            "version": "1.0",
            "status": "BREWSTER_AUTO_BUILD_SCRIPT_FACTORY_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "roadmap_task_count": roadmap.get("task_count", len(roadmap.get("tasks", []))),
            "next_task": next_task,
            "script_blueprint": script_blueprint,
            "file_blueprints": file_blueprints,
            "safety_blueprint": safety_blueprint,
            "command_blueprint": command_blueprint,
            "supported_task_types": supported_task_types,
            "digital_twin_update": {
                "digital_twin_node": "brewster_auto_build_script_factory",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "next_task": next_task,
                    "script_blueprint": script_blueprint,
                    "command_blueprint": command_blueprint
                }
            },
            "warnings": self.build_warnings(next_task, safety_blueprint),
            "recommendation": {
                "status": "SCRIPT_FACTORY_ADVIES",
                "advice": (
                    "Gebruik deze factory als standaardgenerator voor volgende bouwscripts. "
                    "Elke taak krijgt een eigen downloadbaar script met status, create-test, "
                    "test-baoees, commit en rollback waar nodig."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.factory_result

    def build_fallback_next_task(self):
        return {
            "task_id": "AUTO-T001",
            "track_id": "S01",
            "title": "Volgende automatiseringsstap",
            "description": "Maak een downloadbaar bouwscript voor de eerstvolgende roadmaptaak.",
            "risk_level": "laag",
            "go_required": False,
            "expected_files": [],
            "commit_message": "feat: add automated build script"
        }

    def build_script_blueprint(self, next_task):
        task_id = str(next_task.get("task_id", "AUTO-T001"))
        safe_task_id = task_id.lower().replace("-", "_")
        risk = next_task.get("risk_level", "laag")

        return {
            "status": "SCRIPT_BLUEPRINT_GEREED",
            "task_id": task_id,
            "script_name": f"tools_execute_{safe_task_id}_v1.py",
            "zip_name": f"{safe_task_id}_auto_build_v1.zip",
            "script_type": self.detect_script_type(next_task),
            "commands": [
                "status",
                "create-test",
                "test-baoees",
                "commit",
                "rollback" if risk in ["middel", "hoog"] else "status"
            ],
            "must_include": [
                "argparse command interface",
                "git restore outputs",
                "python compile checks",
                "engine import test where applicable",
                "BAOEES run check for PROJECTANALYSE GEREED",
                "git add/commit/push",
                "final git status"
            ]
        }

    def detect_script_type(self, next_task):
        title = str(next_task.get("title", "")).lower()
        description = str(next_task.get("description", "")).lower()

        combined = title + " " + description

        if "core" in combined or "koppel" in combined or "connector" in combined:
            return "core_connector_script"

        if "documentatie" in combined or "handleiding" in combined:
            return "documentation_script"

        if "install" in combined or "update" in combined or "patch" in combined:
            return "installer_patch_script"

        if "cad" in combined or "bim" in combined or "ifc" in combined:
            return "cad_bim_script"

        return "engine_creation_script"

    def build_file_blueprints(self, next_task):
        expected_files = next_task.get("expected_files", [])

        if not expected_files:
            expected_files = [
                "baoees/example_engine/__init__.py",
                "baoees/example_engine/main.py",
                "tools_create_example_engine_v1.py"
            ]

        blueprints = []

        for path in expected_files:
            blueprints.append(
                {
                    "path": path,
                    "status": "TE_GENEREREN",
                    "encoding": "utf-8",
                    "backup_required": "baoees/core/main.py" in path
                }
            )

        return blueprints

    def build_safety_blueprint(self, next_task):
        risk = next_task.get("risk_level", "laag")
        go_required = next_task.get("go_required", False)

        return {
            "status": "SAFETY_BLUEPRINT_GEREED",
            "risk_level": risk,
            "go_required": go_required,
            "backup_required": risk in ["middel", "hoog"],
            "rollback_required": risk in ["middel", "hoog"],
            "core_change_policy": "backup verplicht vóór wijziging van baoees/core/main.py",
            "stop_conditions": [
                "compile error",
                "BAOEES_TEST_NIET_OK",
                "PROJECTANALYSE GEREED ontbreekt",
                "unexpected git status"
            ]
        }

    def build_command_blueprint(self, script_blueprint):
        script_name = script_blueprint.get("script_name", "tools_execute_auto_t001_v1.py")

        return {
            "status": "COMMAND_BLUEPRINT_GEREED",
            "local_workdir": "C:\\\\BREWSTER-ENGINEERING-WIZARD",
            "commands": [
                f"python {script_name} status",
                f"python {script_name} create-test",
                f"python {script_name} test-baoees",
                f"python {script_name} commit",
                "git status"
            ],
            "expected_final_status": "nothing to commit, working tree clean"
        }

    def build_supported_task_types(self):
        return [
            "engine_creation_script",
            "core_connector_script",
            "documentation_script",
            "installer_patch_script",
            "cad_bim_script",
            "test_data_script",
            "report_generator_script",
            "database_migration_script",
            "knowledge_graph_script",
            "gui_mapping_script"
        ]

    def build_warnings(self, next_task, safety_blueprint):
        warnings = []

        if safety_blueprint.get("go_required"):
            warnings.append(f"GO vereist voor taak {next_task.get('task_id')}.")

        if safety_blueprint.get("backup_required"):
            warnings.append("Backup en rollback verplicht voor deze taak.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen voor scriptgeneratie.")

        return warnings

    def get_factory_result(self):
        return self.factory_result

    def create_factory_plan(self, *args, **kwargs):
        return self.create_script_factory_plan(*args, **kwargs)

    def generate_auto_build_script_factory(self, *args, **kwargs):
        return self.create_script_factory_plan(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_script_factory_plan(*args, **kwargs)
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


def write_files():
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    INIT_PATH.write_text(INIT_CONTENT, encoding="utf-8")
    MAIN_PATH.write_text(MAIN_CONTENT, encoding="utf-8")


def write_outputs(result):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FACTORY_JSON_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    blueprint = result.get("script_blueprint", {})
    safety = result.get("safety_blueprint", {})

    lines = [
        "BREWSTER AUTO BUILD SCRIPT FACTORY",
        "=" * 42,
        "",
        f"Status: {result.get('status')}",
        f"Volgende taak: {result.get('next_task', {}).get('task_id')}",
        f"Scriptnaam: {blueprint.get('script_name')}",
        f"Scripttype: {blueprint.get('script_type')}",
        f"Risico: {safety.get('risk_level')}",
        f"GO vereist: {safety.get('go_required')}",
        "",
        "Commando's:"
    ]

    for command in result.get("command_blueprint", {}).get("commands", []):
        lines.append(f"- {command}")

    lines.append("")
    lines.append("Stopcondities:")

    for item in safety.get("stop_conditions", []):
        lines.append(f"- {item}")

    FACTORY_TXT_PATH.write_text("\n".join(lines), encoding="utf-8")


def test_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.brewster_auto_build_script_factory_engine.main")
    engine_class = getattr(module, "BrewsterAutoBuildScriptFactoryEngine")
    engine = engine_class()

    result = engine.create_script_factory_plan(
        project_result={
            "project_id": "BREWAS_BAOEES",
            "project_name": "BREWSTER ENGINEERING WIZARD"
        },
        brewster_task_orchestrator_result={
            "next_task": {
                "task_id": "S01-T001",
                "title": "Stabilisatie - Maak Python engine skeleton",
                "description": "Maak een kleine downloadbare engine.",
                "risk_level": "laag",
                "go_required": False,
                "expected_files": [
                    "baoees/test_engine/__init__.py",
                    "baoees/test_engine/main.py"
                ],
                "commit_message": "feat: add test engine"
            }
        }
    )

    if result.get("status") != "BREWSTER_AUTO_BUILD_SCRIPT_FACTORY_GEREED":
        raise RuntimeError("Auto Build Script Factory gaf geen correcte status terug.")

    if not result.get("script_blueprint", {}).get("script_name"):
        raise RuntimeError("Auto Build Script Factory genereerde geen scriptnaam.")

    write_outputs(result)

    print("")
    print("BREWSTER_AUTO_BUILD_SCRIPT_FACTORY_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Script: {result.get('script_blueprint', {}).get('script_name')}")
    print(f"Output JSON: {FACTORY_JSON_PATH}")
    print(f"Output TXT: {FACTORY_TXT_PATH}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("BREWSTER_AUTO_BUILD_SCRIPT_FACTORY_ENGINE_V1_AANGEMAAKT")


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
    run_command("git add baoees/brewster_auto_build_script_factory_engine/__init__.py")
    run_command("git add baoees/brewster_auto_build_script_factory_engine/main.py")
    run_command("git add tools_create_brewster_auto_build_script_factory_engine_v1.py")
    run_command("git add outputs/brewster_auto_build_script_factory_v1.json")
    run_command("git add outputs/brewster_auto_build_script_factory_v1.txt")
    run_command('git commit -m "feat: add Brewster Auto Build Script Factory Engine v1"')
    run_command("git push")
    run_command("git status", check=False)


def status():
    run_command("git status", check=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["status", "create-test", "test-baoees", "commit"])
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
