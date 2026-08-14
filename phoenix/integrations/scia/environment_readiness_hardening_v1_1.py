"""PROJECT PHOENIX SCIA Environment Readiness Hardening v1.1."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess

VERSION = "1.1.0"
ENGINE_ID = "PHX-SCIA-ENVIRONMENT-READINESS-HARDENING"

EXIT_CODES = {
    0: "Succeeded",
    1: "Unable to initialize MFC",
    2: "Missing arguments",
    3: "Invalid arguments",
    4: "Unable to open ProjectFile",
    5: "Calculation failed",
    6: "Unable to initialize application environment",
    7: "Error during update ProjectFile by XMLUpdateFile",
    8: "Error during create export outputs",
    9: "Error during create XML outputs",
    10: "Error during update ProjectFile by XLSX Update",
}

RUNTIME_NOT_FOUND = "SCIA_RUNTIME_NOT_FOUND"
RUNTIME_HELP_NOT_PROBED = "SCIA_RUNTIME_PRESENT_HELP_NOT_PROBED"
RUNTIME_HELP_OK = "SCIA_RUNTIME_HELP_CONTRACT_VALIDATED"
RUNTIME_HELP_UNEXPECTED = "SCIA_RUNTIME_HELP_CONTRACT_UNEXPECTED"
LICENSE_TARGET_REQUIRED = "SCIA_LICENSE_TARGET_REQUIRED"
LOCAL_SERVICE_STOPPED = "BLOCKED_SCIA_LOCAL_LICENSE_SERVICE_STOPPED"
LICENSE_UNREACHABLE = "BLOCKED_SCIA_LICENSE_SERVER_UNREACHABLE"
ENDPOINT_REACHABLE = "SCIA_LICENSE_ENDPOINT_REACHABLE_PROBE_REQUIRED"
LIVE_AUTH_REQUIRED = "SCIA_LIVE_PROBE_EXPLICIT_AUTHORIZATION_REQUIRED"
APP_ENV_BLOCKED = "BLOCKED_SCIA_APPLICATION_ENVIRONMENT"
PROJECT_OPEN_BLOCKED = "BLOCKED_SCIA_PROJECT_OPEN"
CALCULATION_BLOCKED = "BLOCKED_SCIA_CALCULATION"
LIVE_READY = "SCIA_LIVE_ENVIRONMENT_READY"
LIVE_FAILED = "SCIA_LIVE_PROBE_FAILED"

SAFETY = {
    "service_start_stop_reconfigure": False,
    "license_configuration_change": False,
    "automatic_runtime_help_probe": False,
    "automatic_live_probe": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_license_target(value: str | None) -> tuple[str | None, int | None]:
    if value is None or not value.strip():
        return None, None
    text = value.strip()
    if "@" not in text:
        raise ValueError("License target must use PORT@HOST format.")
    port_text, host = text.split("@", 1)
    if not port_text.isdigit() or not host.strip():
        raise ValueError("License target must use PORT@HOST format.")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("License target port is out of range.")
    return host.strip(), port


def is_local_host(host: str) -> bool:
    names = {
        "localhost", "127.0.0.1", "::1",
        socket.gethostname().lower(),
        socket.getfqdn().lower(),
    }
    return host.strip().lower() in names


def tcp_probe(host: str, port: int, timeout_seconds: float = 2.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return {"reachable": True, "host": host, "port": port, "error": None}
    except OSError as exc:
        return {"reachable": False, "host": host, "port": port, "error": str(exc)}


def windows_service_state(name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"service": name, "status": "NOT_WINDOWS", "observational_only": True}
    cp = subprocess.run(
        ["sc.exe", "query", name],
        capture_output=True, text=True, timeout=10, check=False
    )
    raw = ((cp.stdout or "") + "\n" + (cp.stderr or "")).strip()
    state = "UNKNOWN"
    for line in raw.splitlines():
        if "STATE" in line and ":" in line:
            state = line.split(":", 1)[1].strip()
            break
    return {
        "service": name,
        "query_return_code": cp.returncode,
        "status": state,
        "raw": raw,
        "observational_only": True,
    }


def inspect_builtin_help(esa_xml: Path, allow_runtime_help: bool) -> dict[str, Any]:
    if not esa_xml.is_file():
        return {"status": RUNTIME_NOT_FOUND, "present": False, "path": str(esa_xml)}
    base = {
        "present": True,
        "path": str(esa_xml),
        "sha256": sha256_file(esa_xml),
    }
    if not allow_runtime_help:
        return {**base, "status": RUNTIME_HELP_NOT_PROBED, "runtime_execution_started": False}

    cp = subprocess.run(
        [str(esa_xml)],
        capture_output=True, text=True, timeout=30, check=False
    )
    stdout = cp.stdout or ""
    stderr = cp.stderr or ""
    contract = (
        cp.returncode == 2
        and "Missing parameters." in stdout
        and "Exit codes:" in stdout
        and "6 = Unable to initialize application environment" in stdout
        and "10 = Error during update ProjectFile by XLSX Update" in stdout
    )
    return {
        **base,
        "status": RUNTIME_HELP_OK if contract else RUNTIME_HELP_UNEXPECTED,
        "runtime_execution_started": True,
        "solver_calculation_started": False,
        "return_code": cp.returncode,
        "return_code_meaning": EXIT_CODES.get(cp.returncode, "UNKNOWN"),
        "contract_valid": contract,
        "stdout": stdout,
        "stderr": stderr,
    }


def inspect_environment(
    esa_xml: Path,
    esa_exe: Path | None = None,
    lockman: Path | None = None,
    license_target: str | None = None,
    allow_runtime_help: bool = False,
    tcp_timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    help_result = inspect_builtin_help(esa_xml, allow_runtime_help)
    services = {
        "lmadmin": windows_service_state("lmadmin"),
        "FLEXnet Licensing Service": windows_service_state("FLEXnet Licensing Service"),
    }

    host, port = parse_license_target(license_target)
    network = None
    local_target = None
    if host is not None and port is not None:
        local_target = is_local_host(host)
        network = tcp_probe(host, port, tcp_timeout_seconds)

    if help_result["status"] == RUNTIME_NOT_FOUND:
        status = RUNTIME_NOT_FOUND
    elif help_result["status"] == RUNTIME_HELP_UNEXPECTED:
        status = RUNTIME_HELP_UNEXPECTED
    elif license_target is None:
        status = LICENSE_TARGET_REQUIRED if allow_runtime_help else RUNTIME_HELP_NOT_PROBED
    elif local_target and network is not None and not network["reachable"]:
        lm = services["lmadmin"]["status"].upper()
        status = LOCAL_SERVICE_STOPPED if "STOPPED" in lm else LICENSE_UNREACHABLE
    elif network is not None and not network["reachable"]:
        status = LICENSE_UNREACHABLE
    else:
        status = ENDPOINT_REACHABLE

    return {
        "schema_version": "phoenix.scia-environment-readiness-hardening/1.1",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "status": status,
        "files": {
            "esa_xml": str(esa_xml),
            "esa_xml_present": esa_xml.is_file(),
            "esa": str(esa_exe) if esa_exe else None,
            "esa_present": bool(esa_exe and esa_exe.is_file()),
            "lockman": str(lockman) if lockman else None,
            "lockman_present": bool(lockman and lockman.is_file()),
        },
        "runtime_help": help_result,
        "license_target": license_target,
        "license_target_is_local_host": local_target,
        "license_network": network,
        "services": services,
        "service_actions_performed": [],
        "license_changes_performed": [],
        "solver_calculation_started": False,
        "exit_code_contract": {str(k): v for k, v in EXIT_CODES.items()},
        "safety": dict(SAFETY),
    }


def classify_existing_probe(probe_json: Path) -> dict[str, Any]:
    if not probe_json.is_file():
        raise FileNotFoundError(probe_json)
    data = json.loads(probe_json.read_text(encoding="utf-8-sig"))
    rc = data.get("return_code")
    try:
        rc_int = int(rc)
    except (TypeError, ValueError):
        rc_int = None

    if rc_int == 0:
        status = LIVE_READY
    elif rc_int == 6:
        status = APP_ENV_BLOCKED
    elif rc_int == 4:
        status = PROJECT_OPEN_BLOCKED
    elif rc_int == 5:
        status = CALCULATION_BLOCKED
    else:
        status = LIVE_FAILED

    return {
        "schema_version": "phoenix.scia-existing-probe-classification/1.1",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "status": status,
        "source_probe": str(probe_json),
        "source_probe_sha256": sha256_file(probe_json),
        "return_code": rc_int,
        "return_code_meaning": EXIT_CODES.get(rc_int, "UNKNOWN"),
        "live_probe_started_by_this_action": False,
        "service_actions_performed": [],
        "license_changes_performed": [],
        "safety": dict(SAFETY),
    }


def run_live_probe(
    esa_xml: Path,
    project_esa: Path,
    output_root: Path,
    allow_live_probe: bool,
    analysis: str = "LIN",
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    if not allow_live_probe:
        result = {
            "status": LIVE_AUTH_REQUIRED,
            "live_probe_started": False,
            "service_actions_performed": [],
            "license_changes_performed": [],
            "safety": dict(SAFETY),
        }
        write_json(output_root / "scia_live_environment_probe_v1_1.json", result)
        return result
    if not esa_xml.is_file():
        result = {
            "status": RUNTIME_NOT_FOUND,
            "live_probe_started": False,
            "safety": dict(SAFETY),
        }
        write_json(output_root / "scia_live_environment_probe_v1_1.json", result)
        return result
    if not project_esa.is_file():
        raise FileNotFoundError(project_esa)

    working = output_root / "probe_working.esa"
    shutil.copy2(project_esa, working)
    before = sha256_file(project_esa)

    command = [str(esa_xml), analysis, str(working)]
    write_json(output_root / "scia_live_environment_probe_command_v1_1.json", {"argv": command})
    try:
        cp = subprocess.run(
            command,
            cwd=str(output_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        rc = cp.returncode
        stdout = cp.stdout or ""
        stderr = cp.stderr or ""
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = None
        stdout = str(exc.stdout or "")
        stderr = str(exc.stderr or "")
        timed_out = True

    (output_root / "scia_live_environment_probe_stdout_v1_1.txt").write_text(stdout, encoding="utf-8")
    (output_root / "scia_live_environment_probe_stderr_v1_1.txt").write_text(stderr, encoding="utf-8")

    if timed_out:
        status = LIVE_FAILED
        meaning = "TIMEOUT"
    elif rc == 0:
        status = LIVE_READY
        meaning = EXIT_CODES[0]
    elif rc == 6:
        status = APP_ENV_BLOCKED
        meaning = EXIT_CODES[6]
    elif rc == 4:
        status = PROJECT_OPEN_BLOCKED
        meaning = EXIT_CODES[4]
    elif rc == 5:
        status = CALCULATION_BLOCKED
        meaning = EXIT_CODES[5]
    else:
        status = LIVE_FAILED
        meaning = EXIT_CODES.get(rc, "UNKNOWN") if rc is not None else "UNKNOWN"

    result = {
        "schema_version": "phoenix.scia-live-environment-probe/1.1",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "status": status,
        "live_probe_started": True,
        "analysis": analysis,
        "return_code": rc,
        "return_code_meaning": meaning,
        "timeout": timed_out,
        "source_project": str(project_esa),
        "source_project_sha256_before": before,
        "source_project_sha256_after": sha256_file(project_esa),
        "source_project_unchanged": before == sha256_file(project_esa),
        "working_copy": str(working),
        "working_copy_sha256": sha256_file(working) if working.is_file() else None,
        "service_actions_performed": [],
        "license_changes_performed": [],
        "safety": dict(SAFETY),
    }
    write_json(output_root / "scia_live_environment_probe_v1_1.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)

    i = sub.add_parser("inspect")
    i.add_argument("--esa-xml", required=True)
    i.add_argument("--esa")
    i.add_argument("--lockman")
    i.add_argument("--license-target")
    i.add_argument("--allow-runtime-help", action="store_true")
    i.add_argument("--tcp-timeout-seconds", type=float, default=2.0)
    i.add_argument("--output", required=True)

    c = sub.add_parser("classify-existing-probe")
    c.add_argument("--probe-json", required=True)
    c.add_argument("--output", required=True)

    p = sub.add_parser("probe")
    p.add_argument("--esa-xml", required=True)
    p.add_argument("--project-esa", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--analysis", default="LIN")
    p.add_argument("--allow-live-probe", action="store_true")
    p.add_argument("--timeout-seconds", type=int, default=900)

    args = parser.parse_args()
    if args.action == "inspect":
        result = inspect_environment(
            Path(args.esa_xml),
            Path(args.esa) if args.esa else None,
            Path(args.lockman) if args.lockman else None,
            args.license_target,
            args.allow_runtime_help,
            args.tcp_timeout_seconds,
        )
        write_json(Path(args.output), result)
    elif args.action == "classify-existing-probe":
        result = classify_existing_probe(Path(args.probe_json))
        write_json(Path(args.output), result)
    else:
        result = run_live_probe(
            Path(args.esa_xml),
            Path(args.project_esa),
            Path(args.output),
            args.allow_live_probe,
            args.analysis,
            args.timeout_seconds,
        )

    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result.get("status") in {RUNTIME_HELP_UNEXPECTED, LIVE_FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
