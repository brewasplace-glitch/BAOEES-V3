from datetime import datetime


class BrewsterTaskOrchestratorEngine:

    def __init__(self):
        self.orchestrator_result = {}

    def create_task_orchestration(
        self,
        project_result=None,
        brewster_automation_roadmap_result=None,
        phoenix_bridge_result=None,
        phoenix_ui_mapping_result=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        roadmap = brewster_automation_roadmap_result or {}
        phoenix_bridge_result = phoenix_bridge_result or {}
        phoenix_ui_mapping_result = phoenix_ui_mapping_result or {}

        project_id = project_result.get("project_id", "BREWAS_BAOEES")
        project_name = project_result.get("project_name", "BREWSTER ENGINEERING WIZARD")

        tasks = roadmap.get("tasks", []) or self.build_fallback_tasks()
        queue = self.build_execution_queue(tasks)
        next_task = queue[0] if queue else {}
        go_gate = self.build_go_gate(next_task)

        self.orchestrator_result = {
            "engine": "BrewsterTaskOrchestratorEngine",
            "version": "1.0",
            "status": "BREWSTER_TASK_ORCHESTRATION_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "roadmap_task_count": len(tasks),
            "execution_queue": queue,
            "next_task": next_task,
            "go_gate": go_gate,
            "automation_plan": self.build_automation_plan(next_task),
            "daily_priorities": self.build_daily_priorities(queue),
            "command_plan": self.build_command_plan(next_task),
            "progress_snapshot": self.build_progress_snapshot(
                tasks,
                queue,
                phoenix_bridge_result,
                phoenix_ui_mapping_result
            ),
            "digital_twin_update": {
                "digital_twin_node": "brewster_task_orchestrator",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "next_task": next_task,
                    "go_gate": go_gate,
                    "daily_priorities": self.build_daily_priorities(queue)
                }
            },
            "warnings": self.build_warnings(go_gate, next_task),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.orchestrator_result

    def build_fallback_tasks(self):
        return [
            {
                "task_id": "AUTO-T001",
                "global_order": 1,
                "track_id": "S01",
                "track_title": "Stabilisatie en automatisering",
                "title": "Maak volgende veilige automatiseringsstap",
                "description": "Maak een kleine downloadbare engine of connector met test en commitroute.",
                "priority": 1,
                "risk_level": "laag",
                "go_required": False,
                "depends_on": [],
                "expected_files": [],
                "test_commands": ["python run_baoees_v3.py", "git restore outputs", "git status"],
                "commit_message": "feat: add next automated build task",
                "done_definition": ["working tree clean"]
            }
        ]

    def build_execution_queue(self, tasks):
        sorted_tasks = sorted(
            tasks,
            key=lambda item: (
                item.get("priority", 999),
                item.get("global_order", 999999)
            )
        )

        queue = []

        for task in sorted_tasks[:25]:
            queue.append(
                {
                    "task_id": task.get("task_id"),
                    "global_order": task.get("global_order"),
                    "track_id": task.get("track_id"),
                    "track_title": task.get("track_title"),
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "priority": task.get("priority"),
                    "risk_level": task.get("risk_level"),
                    "go_required": task.get("go_required", False),
                    "depends_on": task.get("depends_on", []),
                    "expected_files": task.get("expected_files", []),
                    "test_commands": task.get("test_commands", []),
                    "commit_message": task.get("commit_message"),
                    "done_definition": task.get("done_definition", [])
                }
            )

        return queue

    def build_go_gate(self, next_task):
        go_required = next_task.get("go_required", False)

        return {
            "status": "GO_VEREIST" if go_required else "GO_NIET_VEREIST",
            "risk_level": next_task.get("risk_level", "laag"),
            "go_required": go_required,
            "instruction": (
                "Vraag expliciet GO voordat deze taak wordt uitgevoerd."
                if go_required
                else "Deze taak mag als normale veilige stap worden voorbereid."
            )
        }

    def build_automation_plan(self, next_task):
        task_id = str(next_task.get("task_id", "AUTO-T001")).lower().replace("-", "_")

        return {
            "status": "AUTOMATION_PLAN_GEREED",
            "next_script_name": f"tools_execute_{task_id}_v1.py",
            "script_policy": "downloadbaar script of ZIP",
            "required_steps": ["status", "create-test", "test-baoees", "commit", "git status"],
            "backup_required": next_task.get("risk_level") == "hoog",
            "rollback_required": next_task.get("risk_level") in ["middel", "hoog"]
        }

    def build_daily_priorities(self, queue):
        return {
            "status": "DAGPRIORITEITEN_GEREED",
            "items": [
                {
                    "task_id": task.get("task_id"),
                    "title": task.get("title"),
                    "risk_level": task.get("risk_level"),
                    "go_required": task.get("go_required"),
                    "priority": task.get("priority")
                }
                for task in queue[:10]
            ]
        }

    def build_command_plan(self, next_task):
        task_id = str(next_task.get("task_id", "AUTO-T001")).lower().replace("-", "_")
        script_name = f"tools_execute_{task_id}_v1.py"

        return {
            "status": "COMMAND_PLAN_GEREED",
            "local_workdir": "C:\\BREWSTER-ENGINEERING-WIZARD",
            "commands": [
                f"python {script_name} status",
                f"python {script_name} create-test",
                f"python {script_name} commit",
                "git status"
            ],
            "expected_final_status": "nothing to commit, working tree clean"
        }

    def build_progress_snapshot(self, tasks, queue, phoenix_bridge_result, phoenix_ui_mapping_result):
        high_risk_count = len([task for task in tasks if task.get("risk_level") == "hoog"])
        go_required_count = len([task for task in tasks if task.get("go_required")])

        return {
            "status": "PROGRESS_SNAPSHOT_GEREED",
            "total_tasks": len(tasks),
            "queued_tasks": len(queue),
            "high_risk_tasks": high_risk_count,
            "go_required_tasks": go_required_count,
            "phoenix_bridge_status": phoenix_bridge_result.get("status", "OPTIONEEL"),
            "phoenix_ui_mapping_status": phoenix_ui_mapping_result.get("status", "OPTIONEEL")
        }

    def build_warnings(self, go_gate, next_task):
        warnings = []

        if go_gate.get("go_required"):
            warnings.append(f"GO vereist voor taak: {next_task.get('task_id')}.")

        if next_task.get("risk_level") == "hoog":
            warnings.append("Hoge-risico taak: backup en rollback verplicht.")

        if not warnings:
            warnings.append("Geen kritieke waarschuwingen voor de eerstvolgende taak.")

        return warnings

    def get_orchestrator_result(self):
        return self.orchestrator_result

    def create_orchestration(self, *args, **kwargs):
        return self.create_task_orchestration(*args, **kwargs)

    def generate_task_orchestration(self, *args, **kwargs):
        return self.create_task_orchestration(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_task_orchestration(*args, **kwargs)
