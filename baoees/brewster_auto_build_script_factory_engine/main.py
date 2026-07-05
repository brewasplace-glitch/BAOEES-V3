from datetime import datetime


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
            "local_workdir": "C:\\BREWSTER-ENGINEERING-WIZARD",
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
