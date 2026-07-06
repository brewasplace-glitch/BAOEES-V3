from datetime import datetime


class BrewsterBuildProgressTrackerEngine:

    def __init__(self):
        self.tracker_result = {}

    def create_progress_tracker(
        self,
        project_result=None,
        brewster_automation_roadmap_result=None,
        brewster_task_orchestrator_result=None,
        brewster_auto_build_script_factory_result=None,
        previous_progress_state=None,
        *args,
        **kwargs
    ):
        project_result = project_result or {}
        roadmap = brewster_automation_roadmap_result or {}
        orchestrator = brewster_task_orchestrator_result or {}
        factory = brewster_auto_build_script_factory_result or {}
        previous_progress_state = previous_progress_state or {}

        project_id = project_result.get("project_id", "BREWAS_BAOEES")
        project_name = project_result.get("project_name", "BREWSTER ENGINEERING WIZARD")

        tasks = roadmap.get("tasks", []) or self.build_fallback_tasks()
        previous_task_states = previous_progress_state.get("task_states", {})

        task_states = self.build_task_states(tasks, previous_task_states)
        progress_summary = self.build_progress_summary(task_states)
        next_open_task = self.find_next_open_task(tasks, task_states)
        blocked_tasks = self.find_blocked_tasks(tasks, task_states)
        go_required_tasks = self.find_go_required_tasks(tasks, task_states)
        daily_progress_dashboard = self.build_daily_progress_dashboard(
            project_name,
            progress_summary,
            next_open_task,
            blocked_tasks,
            go_required_tasks,
            orchestrator,
            factory
        )

        self.tracker_result = {
            "engine": "BrewsterBuildProgressTrackerEngine",
            "version": "1.0",
            "status": "BREWSTER_BUILD_PROGRESS_TRACKER_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "task_count": len(tasks),
            "task_states": task_states,
            "progress_summary": progress_summary,
            "next_open_task": next_open_task,
            "blocked_tasks": blocked_tasks,
            "go_required_tasks": go_required_tasks,
            "daily_progress_dashboard": daily_progress_dashboard,
            "state_policy": self.build_state_policy(),
            "digital_twin_update": {
                "digital_twin_node": "brewster_build_progress_tracker",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "progress_summary": progress_summary,
                    "next_open_task": next_open_task,
                    "blocked_tasks": blocked_tasks,
                    "go_required_tasks": go_required_tasks
                }
            },
            "warnings": self.build_warnings(next_open_task, blocked_tasks),
            "recommendation": {
                "status": "BUILD_PROGRESS_TRACKER_ADVIES",
                "advice": (
                    "Gebruik deze tracker als voortgangsgeheugen. Na iedere taak moet de status "
                    "worden bijgewerkt naar tested, committed, pushed en clean voordat de volgende taak start."
                )
            },
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.tracker_result

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
                "done_definition": ["working tree clean"]
            }
        ]

    def build_task_states(self, tasks, previous_task_states):
        task_states = {}

        for task in tasks:
            task_id = task.get("task_id")
            previous = previous_task_states.get(task_id, {})

            state = {
                "task_id": task_id,
                "track_id": task.get("track_id"),
                "title": task.get("title"),
                "risk_level": task.get("risk_level", "laag"),
                "go_required": task.get("go_required", False),
                "depends_on": task.get("depends_on", []),
                "status": previous.get("status", "not_started"),
                "started": previous.get("started", False),
                "tested": previous.get("tested", False),
                "committed": previous.get("committed", False),
                "pushed": previous.get("pushed", False),
                "clean": previous.get("clean", False),
                "blocked": False,
                "updated_at": previous.get("updated_at")
            }

            if state["clean"]:
                state["status"] = "clean"
            elif state["pushed"]:
                state["status"] = "pushed"
            elif state["committed"]:
                state["status"] = "committed"
            elif state["tested"]:
                state["status"] = "tested"
            elif state["started"]:
                state["status"] = "in_progress"

            task_states[task_id] = state

        for task_id, state in task_states.items():
            for dependency in state.get("depends_on", []):
                dependency_state = task_states.get(dependency, {})
                if dependency_state.get("status") != "clean":
                    state["blocked"] = True
                    if state["status"] == "not_started":
                        state["status"] = "blocked"

        return task_states

    def build_progress_summary(self, task_states):
        total = len(task_states)
        counts = {
            "not_started": 0,
            "blocked": 0,
            "in_progress": 0,
            "tested": 0,
            "committed": 0,
            "pushed": 0,
            "clean": 0
        }

        for state in task_states.values():
            status = state.get("status", "not_started")
            if status not in counts:
                counts[status] = 0
            counts[status] += 1

        clean_count = counts.get("clean", 0)
        progress_percent = round((clean_count / total) * 100, 2) if total else 0.0

        return {
            "status": "PROGRESS_SUMMARY_GEREED",
            "total_tasks": total,
            "counts": counts,
            "clean_count": clean_count,
            "progress_percent": progress_percent,
            "remaining_tasks": max(total - clean_count, 0)
        }

    def find_next_open_task(self, tasks, task_states):
        sorted_tasks = sorted(
            tasks,
            key=lambda item: (
                item.get("priority", 999),
                item.get("global_order", 999999)
            )
        )

        for task in sorted_tasks:
            task_id = task.get("task_id")
            state = task_states.get(task_id, {})
            status = state.get("status", "not_started")

            if status in ["not_started", "in_progress"] and not state.get("blocked"):
                return {
                    "task_id": task_id,
                    "title": task.get("title"),
                    "description": task.get("description"),
                    "track_id": task.get("track_id"),
                    "track_title": task.get("track_title"),
                    "priority": task.get("priority"),
                    "risk_level": task.get("risk_level", "laag"),
                    "go_required": task.get("go_required", False),
                    "status": status,
                    "expected_files": task.get("expected_files", []),
                    "test_commands": task.get("test_commands", []),
                    "commit_message": task.get("commit_message")
                }

        return {
            "task_id": None,
            "status": "GEEN_OPEN_TAAK",
            "message": "Alle taken zijn clean of geblokkeerd."
        }

    def find_blocked_tasks(self, tasks, task_states):
        blocked = []

        for task in tasks:
            task_id = task.get("task_id")
            state = task_states.get(task_id, {})

            if state.get("blocked"):
                blocked.append(
                    {
                        "task_id": task_id,
                        "title": task.get("title"),
                        "depends_on": state.get("depends_on", []),
                        "status": state.get("status")
                    }
                )

        return blocked[:25]

    def find_go_required_tasks(self, tasks, task_states):
        items = []

        for task in tasks:
            task_id = task.get("task_id")
            state = task_states.get(task_id, {})

            if task.get("go_required") and state.get("status") != "clean":
                items.append(
                    {
                        "task_id": task_id,
                        "title": task.get("title"),
                        "risk_level": task.get("risk_level"),
                        "status": state.get("status", "not_started")
                    }
                )

        return items[:25]

    def build_daily_progress_dashboard(
        self,
        project_name,
        progress_summary,
        next_open_task,
        blocked_tasks,
        go_required_tasks,
        orchestrator,
        factory
    ):
        return {
            "title": f"Voortgang {project_name}",
            "status": "DAGELIJKS_VOORTGANGSDASHBOARD_GEREED",
            "progress_percent": progress_summary.get("progress_percent"),
            "remaining_tasks": progress_summary.get("remaining_tasks"),
            "next_open_task": next_open_task,
            "blocked_task_count": len(blocked_tasks),
            "go_required_task_count": len(go_required_tasks),
            "orchestrator_status": orchestrator.get("status", "OPTIONEEL"),
            "factory_status": factory.get("status", "OPTIONEEL"),
            "today_focus": [
                "git status controleren",
                "alleen verder bij working tree clean",
                "eerstvolgende open taak uitvoeren",
                "GO vragen bij hoge risico's",
                "na taak status bijwerken naar clean"
            ]
        }

    def build_state_policy(self):
        return {
            "status": "STATE_POLICY_GEREED",
            "state_file": "outputs/brewster_build_progress_state_v1.json",
            "allowed_statuses": [
                "not_started",
                "blocked",
                "in_progress",
                "tested",
                "committed",
                "pushed",
                "clean"
            ],
            "clean_definition": [
                "script uitgevoerd zonder fout",
                "BAOEES_TEST_OK",
                "commit en push uitgevoerd",
                "git status meldt nothing to commit, working tree clean"
            ]
        }

    def build_warnings(self, next_open_task, blocked_tasks):
        warnings = []

        if next_open_task.get("go_required"):
            warnings.append(f"GO vereist voor volgende taak: {next_open_task.get('task_id')}.")

        if blocked_tasks:
            warnings.append(f"Aantal geblokkeerde taken: {len(blocked_tasks)}.")

        if not warnings:
            warnings.append("Geen kritieke voortgangswaarschuwingen.")

        return warnings

    def get_tracker_result(self):
        return self.tracker_result

    def create_tracker(self, *args, **kwargs):
        return self.create_progress_tracker(*args, **kwargs)

    def generate_build_progress_tracker(self, *args, **kwargs):
        return self.create_progress_tracker(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_progress_tracker(*args, **kwargs)
