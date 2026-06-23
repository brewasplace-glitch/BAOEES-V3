import argparse
from datetime import datetime


class ProjectLauncherEngine:

    def __init__(self):
        self.launch_result = {}

    def parse_arguments(self, args=None):
        parser = argparse.ArgumentParser(
            description="BAOEES V3 Project Launcher"
        )

        parser.add_argument(
            "--project",
            dest="project_id",
            default=None,
            help=(
                "Project-id uit configs/projects/project_index.json, "
                "bijvoorbeeld: plutostraat, moskee_bunschoten, bruynzeel_waterfront"
            )
        )

        parser.add_argument(
            "--mode",
            dest="runtime_mode",
            default="autonomous",
            choices=[
                "assistant",
                "semi-autonomous",
                "autonomous"
            ],
            help="BAOEES runtime modus"
        )

        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Alleen launcher-configuratie tonen zonder volledige projectanalyse"
        )

        parsed_args = parser.parse_args(args=args)

        self.launch_result = {
            "engine": "ProjectLauncherEngine",
            "version": "1.0",
            "status": "PROJECT_LAUNCH_ARGUMENTS_GELADEN",
            "calculation_level": "command line project launcher",
            "project_id": parsed_args.project_id,
            "runtime_mode": parsed_args.runtime_mode,
            "dry_run": parsed_args.dry_run,
            "available_examples": [
                "python run_baoees_v3.py --project plutostraat",
                "python run_baoees_v3.py --project moskee_bunschoten",
                "python run_baoees_v3.py --project bruynzeel_waterfront"
            ],
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds")
        }

        return self.launch_result

    def build_recommendation(self):
        return {
            "status": "PROJECT_LAUNCHER_ADVIES",
            "advice": (
                "Gebruik deze launcher om BAOEES vanaf de command line met een gekozen project "
                "te starten. Later kan dezelfde logica worden gekoppeld aan het startscherm."
            ),
            "next_steps": [
                "project_id doorgeven aan ProjectSelectorEngine",
                "runtime_mode koppelen aan RuntimeEngine",
                "dry-run gebruiken voor snelle projectcontrole",
                "later GUI-startscherm koppelen aan dezelfde launcherlogica"
            ]
        }

    def get_launch_result(self):
        return self.launch_result

    def run(self):
        print("Command Line Project Launcher actief")