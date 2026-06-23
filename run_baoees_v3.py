from pprint import pprint

from baoees.core.main import BAOEESCore
from baoees.project_launcher_engine.main import ProjectLauncherEngine


def main():
    launcher = ProjectLauncherEngine()
    launch_result = launcher.parse_arguments()

    print("Command Line Project Launcher resultaat:")
    pprint(launch_result)
    print("")

    if launch_result.get("dry_run"):
        print("Dry-run actief: projectanalyse wordt niet uitgevoerd.")
        launcher.run()
        return

    core = BAOEESCore()
    core.start_projectanalyse(
        project_id=launch_result.get("project_id"),
        runtime_mode=launch_result.get("runtime_mode", "autonomous")
    )

    launcher.run()


if __name__ == "__main__":
    main()