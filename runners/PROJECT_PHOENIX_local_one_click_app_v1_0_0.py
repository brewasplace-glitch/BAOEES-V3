"""Launch or self-test the Project Phoenix local application."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.local_app.dashboard_adapter import DashboardAdapter
from phoenix.local_app.server import PhoenixLocalApplication


CONFIG_REL = Path("configs/phoenix/local_one_click_app_v1_0_0.json")


def load_config(repository: Path):
    return json.loads((repository / CONFIG_REL).read_text(encoding="utf-8"))


def find_port(host: str, preferred: int, attempts: int) -> int:
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError("Geen vrije lokale Phoenix-poort gevonden.")


def health(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=0.5) as response:
            return response.status == 200
    except Exception:
        return False


def self_test(repository: Path) -> dict:
    config = load_config(repository)
    adapter = DashboardAdapter(repository, config)
    candidates = adapter.discover()
    selected = adapter.select()
    html, info = adapter.render(token="SELF_TEST_TOKEN")
    workflows = []
    for item in config["workflows"]:
        available = all(
            (repository / relative).is_file()
            for relative in item.get("required_files", [])
        )
        workflows.append({"id": item["id"], "available": available})
    checks = {
        "config_loaded": config["version"] == "1.0.0",
        "local_bind_only": config["host"] == "127.0.0.1",
        "dashboard_rendered": "phoenix-local-bridge" in html,
        "dashboard_source_selected": bool(info["source_path"]),
        "workflow_allowlist_present": len(workflows) == 4,
        "three_existing_workflows_available": sum(
            1 for item in workflows if item["available"]
        ) >= 3,
        "production_workflow_visible_but_gated": any(
            item["id"] == "real_concept_drawings_reports"
            and not item["available"]
            for item in workflows
        ),
        "launcher_present": (repository / "START_PHOENIX.ps1").is_file(),
        "cmd_launcher_present": (repository / "START_PHOENIX.cmd").is_file(),
        "stop_launcher_present": (repository / "STOP_PHOENIX.ps1").is_file(),
    }
    return {
        "execution_status": "PASSED" if all(checks.values()) else "FAILED",
        "version": config["version"],
        "dashboard": info,
        "candidate_count": len(candidates),
        "top_candidates": [item.to_dict() for item in candidates[:5]],
        "workflows": workflows,
        "checks": checks,
        "check_count": len(checks),
        "checks_passed": sum(1 for value in checks.values() if value),
    }


def spawn_background(repository: Path, host: str, port: int, open_browser: bool) -> int:
    runtime = repository / "outputs/runtime/phoenix_local_app_v1_0_0"
    runtime.mkdir(parents=True, exist_ok=True)
    log = runtime / "server.log"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--repository",
        str(repository),
        "--serve",
        "--host",
        host,
        "--port",
        str(port),
    ]
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with log.open("ab") as handle:
        subprocess.Popen(
            command,
            cwd=repository,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=(os.name != "nt"),
        )
    url = f"http://{host}:{port}"
    for _ in range(50):
        if health(url):
            if open_browser:
                webbrowser.open(url)
            print(json.dumps({"status": "STARTED", "url": url}, ensure_ascii=False))
            return 0
        time.sleep(0.1)
    raise RuntimeError(f"Phoenix lokale runtime startte niet. Bekijk: {log}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repository = args.repository.resolve()
    config = load_config(repository)
    host = args.host or config["host"]
    preferred = args.port or int(config["preferred_port"])

    if args.self_test:
        result = self_test(repository)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["execution_status"] == "PASSED" else 1

    if host != "127.0.0.1":
        raise RuntimeError("Phoenix Local mag alleen aan 127.0.0.1 binden.")

    port = preferred if args.serve else find_port(
        host,
        preferred,
        int(config["max_port_attempts"]),
    )

    if args.background:
        return spawn_background(repository, host, port, args.open_browser)

    application = PhoenixLocalApplication(repository, config)
    runtime = repository / config["runtime_root"]
    runtime.mkdir(parents=True, exist_ok=True)
    session = runtime / "session.json"
    session.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "host": host,
                "port": port,
                "url": f"http://{host}:{port}",
                "token": application.token,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    try:
        application.serve(host, port)
    finally:
        session.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
