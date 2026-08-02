#!/usr/bin/env python3
"""Launcher/runtime for Phoenix Official Start Screen v3.0.2."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\PROJECT-PHOENIX")
STATE_FILE = Path(tempfile.gettempdir()) / "project_phoenix_official_start_v3_runtime.json"
CONFIG = REPO / "configs" / "phoenix" / "local_one_click_app_v1_0_0.json"


def load_config():
    return json.loads(CONFIG.read_text(encoding="utf-8-sig"))


def health(port: int, timeout: float = 0.8):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
        return value if value.get("status") == "ok" else None
    except Exception:
        return None


def find_live_runtime():
    if not STATE_FILE.is_file():
        return None
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        port = int(state["port"])
    except Exception:
        return None
    value = health(port)
    if not value:
        return None
    if value.get("start_screen_version") != "3.0.2":
        return None
    if value.get("version") != "1.8.2":
        return None
    return port


def port_is_free(host: str, port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(config):
    host = str(config.get("host", "127.0.0.1"))
    preferred = int(config.get("preferred_port", 8765))
    attempts = int(config.get("max_port_attempts", 10))
    for port in range(preferred, preferred + attempts):
        if port_is_free(host, port):
            return host, port
    raise RuntimeError("Geen vrije Phoenix local-app poort gevonden.")


def serve():
    sys.path.insert(0, str(REPO))
    from phoenix.local_app.server import PhoenixLocalApplication

    config = load_config()
    host, port = choose_port(config)
    state = {
        "pid": os.getpid(),
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}/start-v3/",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "start_screen_version": "3.0.2",
        "runtime_version": "1.8.2",
    }
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    app = PhoenixLocalApplication(REPO, config)
    app.serve(host, port)


def refresh_autosync():
    refresh = REPO / "tools" / "start_screen" / "REFRESH_PROJECT_PHOENIX_OFFICIAL_START_v3.ps1"
    if not refresh.is_file():
        return
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(refresh), "-Repo", str(REPO)],
        cwd=REPO, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def spawn_server():
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    args = [sys.executable, str(Path(__file__).resolve()), "--serve"]
    kwargs = {
        "cwd": str(REPO),
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(args, **kwargs)


def launch():
    refresh_autosync()
    port = find_live_runtime()
    if port is None:
        spawn_server()
        deadline = time.time() + 15
        while time.time() < deadline:
            port = find_live_runtime()
            if port is not None:
                break
            time.sleep(0.25)
    if port is None:
        raise RuntimeError("Phoenix 3.0.2 local runtime kon niet worden gestart.")
    url = f"http://127.0.0.1:{port}/start-v3/"
    webbrowser.open(url)
    print(f"PROJECT PHOENIX OFFICIAL START v3.0.2: OPENED -> {url}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.serve:
        serve()
    else:
        launch()


if __name__ == "__main__":
    main()
