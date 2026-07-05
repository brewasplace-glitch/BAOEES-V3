from pathlib import Path
import argparse
import importlib
import json
import py_compile
import subprocess


ENGINE_DIR = Path("baoees/brewster_automation_roadmap_engine")
INIT_PATH = ENGINE_DIR / "__init__.py"
MAIN_PATH = ENGINE_DIR / "main.py"
OUTPUT_DIR = Path("outputs")
ROADMAP_JSON_PATH = OUTPUT_DIR / "brewster_automation_roadmap_v1.json"
DAGSTART_TXT_PATH = OUTPUT_DIR / "brewster_dagstart_dashboard_v1.txt"

INIT_CONTENT = "from .main import BrewsterAutomationRoadmapEngine\n"

MAIN_CONTENT = r"""from datetime import datetime


class BrewsterAutomationRoadmapEngine:

    def __init__(self):
        self.roadmap_result = {}

    def create_automation_roadmap(self, project_result=None, *args, **kwargs):
        project_result = project_result or {}
        project_id = project_result.get("project_id", "BREWAS_BAOEES")
        project_name = project_result.get("project_name", "BREWSTER ENGINEERING WIZARD")

        tracks = self.build_tracks()
        tasks = self.build_tasks(tracks)
        dashboard = self.build_daily_dashboard(project_name, tracks, tasks)

        self.roadmap_result = {
            "engine": "BrewsterAutomationRoadmapEngine",
            "version": "1.0",
            "status": "BREWSTER_AUTOMATION_ROADMAP_GEREED",
            "project_id": project_id,
            "project_name": project_name,
            "track_count": len(tracks),
            "task_count": len(tasks),
            "tracks": tracks,
            "tasks": tasks,
            "daily_dashboard": dashboard,
            "execution_policy": self.build_execution_policy(),
            "progress_model": self.build_progress_model(tracks, tasks),
            "digital_twin_update": {
                "digital_twin_node": "brewster_automation_roadmap",
                "project_id": project_id,
                "project_name": project_name,
                "status": "READY_FOR_DIGITAL_TWIN_MERGE",
                "data": {
                    "track_count": len(tracks),
                    "task_count": len(tasks),
                    "daily_dashboard": dashboard
                }
            },
            "warnings": [
                "Elke ingrijpende core-, database-, GUI- of exportwijziging vereist vooraf GO.",
                "Definitieve engineering vereist normatieve controle en constructeurbeoordeling.",
                "Taken worden pas uitgevoerd na lokaal script, test, commit en clean status."
            ],
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.roadmap_result

    def build_tracks(self):
        return [
            {"track_id": "S01", "title": "Stabilisatie en automatisering", "priority": 1},
            {"track_id": "S02", "title": "Phoenix hoofdscherm en GUI", "priority": 2},
            {"track_id": "S03", "title": "Project Intake en automatische aannames", "priority": 3},
            {"track_id": "S04", "title": "Digital Twin en Knowledge Graph", "priority": 4},
            {"track_id": "S05", "title": "Constructie, fundering en geotechniek", "priority": 5},
            {"track_id": "S06", "title": "Infra, wegen, riolering en waterbouw", "priority": 6},
            {"track_id": "S07", "title": "Vergunningen en omgeving", "priority": 7},
            {"track_id": "S08", "title": "Kosten, planning en aanbesteding", "priority": 8},
            {"track_id": "S09", "title": "Rapporten, tekeningen en CAD/BIM-export", "priority": 9},
            {"track_id": "S10", "title": "Installatie, updates en documentatie", "priority": 10}
        ]

    def build_tasks(self, tracks):
        templates = [
            ("architectuur", "Ontwerp modulearchitectuur en bestandsstructuur", "laag"),
            ("engine_skeleton", "Maak Python engine skeleton", "laag"),
            ("data_contract", "Definieer input- en outputcontracten", "middel"),
            ("digital_twin_node", "Definieer Digital Twin-node", "middel"),
            ("knowledge_graph_node", "Definieer Knowledge Graph-entiteiten", "middel"),
            ("qaqc_checks", "Maak QA/QC-controles", "middel"),
            ("report_mapping", "Maak rapport- en dashboardmapping", "middel"),
            ("export_mapping", "Maak exportmapping", "middel"),
            ("cad_bim_mapping", "Maak CAD/BIM mapping", "hoog"),
            ("test_engine", "Maak importtest en engine-test", "laag"),
            ("test_baoees", "Voer BAOEES-run uit", "laag"),
            ("connector", "Koppel module veilig aan BAOEES Core", "hoog"),
            ("phoenix_tile", "Maak Phoenix dashboardtegel", "middel"),
            ("settings", "Maak configuratie en standaardinstellingen", "middel"),
            ("example_project", "Maak voorbeeldproject en testdata", "middel"),
            ("docs_user", "Schrijf gebruikershandleiding", "laag"),
            ("docs_technical", "Schrijf technische documentatie", "laag"),
            ("installer_update", "Maak update-/installatiescript", "hoog"),
            ("commit_push", "Maak git add/commit/push-stap", "laag"),
            ("release_note", "Maak release note en changelog", "laag"),
            ("error_handling", "Maak foutafhandeling en rollbackroute", "middel"),
            ("audit_log", "Maak auditlog en bronvermelding", "middel"),
            ("security_review", "Controleer bestands- en gebruikersveiligheid", "middel"),
            ("final_acceptance", "Maak acceptatietest en clean controle", "laag")
        ]

        tasks = []
        order = 1

        for track in tracks:
            previous_task_id = None

            for number, template in enumerate(templates, start=1):
                code, description, risk = template
                task_id = f"{track['track_id']}-T{number:03d}"
                go_required = risk == "hoog" or code in ["connector", "installer_update", "cad_bim_mapping"]

                task = {
                    "task_id": task_id,
                    "global_order": order,
                    "track_id": track["track_id"],
                    "track_title": track["title"],
                    "title": f"{track['title']} - {description}",
                    "description": description,
                    "priority": track["priority"],
                    "risk_level": risk,
                    "go_required": go_required,
                    "depends_on": [previous_task_id] if previous_task_id else [],
                    "expected_files": [
                        f"baoees/{track['track_id'].lower()}_{code}_engine/__init__.py",
                        f"baoees/{track['track_id'].lower()}_{code}_engine/main.py",
                        f"tools_create_{track['track_id'].lower()}_{code}_v1.py"
                    ],
                    "test_commands": [
                        "python run_baoees_v3.py",
                        "git restore outputs",
                        "git status"
                    ],
                    "commit_message": f"feat: {track['track_id'].lower()} {code.replace('_', ' ')}",
                    "done_definition": [
                        "script uitgevoerd zonder fout",
                        "BAOEES_TEST_OK of PROJECTANALYSE GEREED",
                        "commit en push uitgevoerd",
                        "nothing to commit, working tree clean"
                    ]
                }

                tasks.append(task)
                previous_task_id = task_id
                order += 1

        return tasks

    def build_daily_dashboard(self, project_name, tracks, tasks):
        return {
            "title": f"Dagstart {project_name}",
            "status": "DAGSTART_DASHBOARD_GEREED",
            "today_focus": [
                "git status controleren",
                "alleen verder bij working tree clean",
                "eerstvolgende taak kiezen uit roadmap",
                "GO vragen bij ingrijpende stap",
                "testen, committen en pushen"
            ],
            "top_priority_tasks": tasks[:10],
            "track_overview": tracks,
            "next_safe_step": "Voer één roadmaptaak uit via downloadbaar script en eindig met git status clean."
        }

    def build_execution_policy(self):
        return {
            "status": "EXECUTION_POLICY_GEREED",
            "local_workdir": "C:\\\\BREWSTER-ENGINEERING-WIZARD",
            "rules": [
                "Geen ingrijpende stap zonder GO.",
                "Geen lange handmatige codeblokken voor grote bestanden.",
                "Gebruik downloadbare scripts of ZIP-bestanden.",
                "Maak backup vóór wijziging van baoees/core/main.py.",
                "Rollback bij compile- of BAOEES-testfout.",
                "Na iedere stap: git restore outputs, git status.",
                "Einddoel: nothing to commit, working tree clean."
            ]
        }

    def build_progress_model(self, tracks, tasks):
        return {
            "status": "PROGRESS_MODEL_GEREED",
            "total_tracks": len(tracks),
            "total_tasks": len(tasks),
            "default_progress": {
                "not_started": len(tasks),
                "in_progress": 0,
                "tested": 0,
                "committed": 0,
                "pushed": 0,
                "clean": 0
            }
        }

    def get_roadmap_result(self):
        return self.roadmap_result

    def create_roadmap(self, *args, **kwargs):
        return self.create_automation_roadmap(*args, **kwargs)

    def generate_brewster_automation_roadmap(self, *args, **kwargs):
        return self.create_automation_roadmap(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.create_automation_roadmap(*args, **kwargs)
"""


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
    ROADMAP_JSON_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    dashboard = result.get("daily_dashboard", {})
    lines = [
        "BREWSTER ENGINEERING WIZARD - DAGSTART",
        "=" * 46,
        "",
        f"Status: {dashboard.get('status')}",
        f"Totaal sporen: {result.get('track_count')}",
        f"Totaal taken: {result.get('task_count')}",
        "",
        "Focus vandaag:"
    ]

    for item in dashboard.get("today_focus", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Top prioriteit taken:")

    for task in dashboard.get("top_priority_tasks", []):
        marker = "GO vereist" if task.get("go_required") else "normale stap"
        lines.append(f"- {task.get('task_id')}: {task.get('description')} ({marker})")

    lines.append("")
    lines.append(f"Volgende veilige stap: {dashboard.get('next_safe_step')}")

    DAGSTART_TXT_PATH.write_text("\n".join(lines), encoding="utf-8")


def test_engine():
    py_compile.compile(str(MAIN_PATH), doraise=True)
    importlib.invalidate_caches()

    module = importlib.import_module("baoees.brewster_automation_roadmap_engine.main")
    engine_class = getattr(module, "BrewsterAutomationRoadmapEngine")
    engine = engine_class()

    result = engine.create_automation_roadmap(
        project_result={
            "project_id": "BREWAS_BAOEES",
            "project_name": "BREWSTER ENGINEERING WIZARD"
        }
    )

    if result.get("status") != "BREWSTER_AUTOMATION_ROADMAP_GEREED":
        raise RuntimeError("Roadmap Engine gaf geen correcte status terug.")

    if result.get("task_count", 0) < 200:
        raise RuntimeError("Roadmap bevat minder dan 200 taken.")

    write_outputs(result)

    print("")
    print("BREWSTER_AUTOMATION_ROADMAP_ENGINE_TEST_OK")
    print(f"Status: {result.get('status')}")
    print(f"Sporen: {result.get('track_count')}")
    print(f"Taken: {result.get('task_count')}")
    print(f"Roadmap JSON: {ROADMAP_JSON_PATH}")
    print(f"Dagstart dashboard: {DAGSTART_TXT_PATH}")


def create_test():
    run_command("git restore outputs", check=False)
    write_files()
    test_engine()
    print("")
    print("BREWSTER_AUTOMATION_ROADMAP_ENGINE_V1_AANGEMAAKT")


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
    run_command("git add baoees/brewster_automation_roadmap_engine/__init__.py")
    run_command("git add baoees/brewster_automation_roadmap_engine/main.py")
    run_command("git add tools_create_brewster_automation_roadmap_engine_v1.py")
    run_command("git add outputs/brewster_automation_roadmap_v1.json")
    run_command("git add outputs/brewster_dagstart_dashboard_v1.txt")
    run_command('git commit -m "feat: add Brewster Automation Roadmap Engine v1"')
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
