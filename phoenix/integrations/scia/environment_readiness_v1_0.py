"""PROJECT PHOENIX SCIA Environment Readiness v1.0."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import json
import os
import shutil
import socket
import subprocess
import tempfile

VERSION = "1.0.0"
ENGINE_ID = "PHX-SCIA-ENVIRONMENT-READINESS"

SCIA_EXIT_CODES = {
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
RUNTIME_HELP_VALIDATED = "SCIA_RUNTIME_HELP_VALIDATED"
LICENSE_TARGET_UNCONFIRMED = "SCIA_LICENSE_TARGET_UNCONFIRMED"
LICENSE_SERVER_UNREACHABLE = "BLOCKED_SCIA_LICENSE_SERVER_UNREACHABLE"
READY_FOR_PROBE = "SCIA_READY_FOR_CONTROLLED_LIVE_PROBE"
LIVE_AUTH_REQUIRED = "SCIA_LIVE_PROBE_EXPLICIT_AUTHORIZATION_REQUIRED"
LIVE_PROBE_PASSED = "SCIA_LIVE_PROBE_PASSED"
APPLICATION_ENV_BLOCKED = "BLOCKED_SCIA_APPLICATION_ENVIRONMENT"
PROJECT_OPEN_BLOCKED = "BLOCKED_SCIA_PROJECT_OPEN"
CALCULATION_BLOCKED = "BLOCKED_SCIA_CALCULATION"
LIVE_PROBE_FAILED = "SCIA_LIVE_PROBE_FAILED"

SAFETY = {
    "service_start_stop_reconfigure": False,
    "license_configuration_change": False,
    "automatic_live_probe": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


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
    if port < 1 or port > 65535:
        raise ValueError("License target port out of range.")
    return host.strip(), port


def tcp_probe(host: str, port: int, timeout_seconds: float = 2.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return {"reachable": True, "host": host, "port": port, "error": None}
    except OSError as exc:
        return {"reachable": False, "host": host, "port": port, "error": str(exc)}


def windows_service_state(name: str) -> dict[str, Any]:
    if os.name != "nt":
        return {"service": name, "status": "NOT_WINDOWS", "observational_only": True}
    try:
        cp = subprocess.run(
            ["sc.exe", "query", name],
            capture_output=True, text=True, timeout=10, check=False
        )
    except Exception as exc:
        return {"service": name, "status": "QUERY_FAILED", "error": str(exc), "observational_only": True}
    text = (cp.stdout or "") + "\n" + (cp.stderr or "")
    status = "UNKNOWN"
    for line in text.splitlines():
        if "STATE" in line and ":" in line:
            status = line.split(":", 1)[1].strip()
            break
    return {
        "service": name,
        "query_return_code": cp.returncode,
        "status": status,
        "raw": text.strip(),
        "observational_only": True,
    }


def esa_xml_help(esa_xml: Path) -> dict[str, Any]:
    if not esa_xml.is_file():
        return {"present": False, "status": RUNTIME_NOT_FOUND, "path": str(esa_xml)}
    cp = subprocess.run(
        [str(esa_xml)],
        capture_output=True, text=True, timeout=30, check=False
    )
    stdout = cp.stdout or ""
    stderr = cp.stderr or ""
    signature_ok = (
        cp.returncode == 2
        and "Missing parameters." in stdout
        and "Exit codes:" in stdout
        and "6 = Unable to initialize application environment" in stdout
    )
    return {
        "present": True,
        "status": RUNTIME_HELP_VALIDATED if signature_ok else "SCIA_RUNTIME_HELP_UNEXPECTED",
        "path": str(esa_xml),
        "return_code": cp.returncode,
        "return_code_meaning": SCIA_EXIT_CODES.get(cp.returncode, "UNKNOWN"),
        "builtin_help_signature_valid": signature_ok,
        "stdout": stdout,
        "stderr": stderr,
    }


def inspect_environment(
    esa_xml: Path,
    esa_exe: Path | None = None,
    lockman: Path | None = None,
    license_target: str | None = None,
) -> dict[str, Any]:
    help_result = esa_xml_help(esa_xml)
    services = {
        "lmadmin": windows_service_state("lmadmin"),
        "FLEXnet Licensing Service": windows_service_state("FLEXnet Licensing Service"),
    }
    host, port = parse_license_target(license_target)
    network = None
    if host is not None and port is not None:
        network = tcp_probe(host, port)

    if not help_result.get("present"):
        status = RUNTIME_NOT_FOUND
    elif help_result.get("status") != RUNTIME_HELP_VALIDATED:
        status = help_result.get("status")
    elif host is None:
        status = LICENSE_TARGET_UNCONFIRMED
    elif network is not None and not network["reachable"]:
        status = LICENSE_SERVER_UNREACHABLE
    else:
        status = READY_FOR_PROBE

    return {
        "schema_version": "phoenix.scia-environment-readiness/1.0",
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
        "esa_xml_help": help_result,
        "license_target": license_target,
        "license_network": network,
        "services": services,
        "service_actions_performed": [],
        "license_changes_performed": [],
        "exit_code_contract": {str(k): v for k, v in SCIA_EXIT_CODES.items()},
        "safety": dict(SAFETY),
    }


def probe_application_environment(
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
            "live_execution_started": False,
            "safety": dict(SAFETY),
        }
        write_json(output_root / "scia_environment_probe_result.json", result)
        return result
    if not esa_xml.is_file():
        result = {
            "status": RUNTIME_NOT_FOUND,
            "live_execution_started": False,
            "safety": dict(SAFETY),
        }
        write_json(output_root / "scia_environment_probe_result.json", result)
        return result
    if not project_esa.is_file():
        raise FileNotFoundError(project_esa)

    working = output_root / "probe_working.esa"
    shutil.copy2(project_esa, working)
    command = [str(esa_xml), analysis, str(working)]
    write_json(output_root / "scia_environment_probe_command.json", {"argv": command})

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
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        timed_out = True

    (output_root / "scia_environment_probe_stdout.txt").write_text(str(stdout), encoding="utf-8")
    (output_root / "scia_environment_probe_stderr.txt").write_text(str(stderr), encoding="utf-8")

    if timed_out:
        status = LIVE_PROBE_FAILED
        meaning = "TIMEOUT"
    elif rc == 0:
        status = LIVE_PROBE_PASSED
        meaning = SCIA_EXIT_CODES[0]
    elif rc == 6:
        status = APPLICATION_ENV_BLOCKED
        meaning = SCIA_EXIT_CODES[6]
    elif rc == 4:
        status = PROJECT_OPEN_BLOCKED
        meaning = SCIA_EXIT_CODES[4]
    elif rc == 5:
        status = CALCULATION_BLOCKED
        meaning = SCIA_EXIT_CODES[5]
    else:
        status = LIVE_PROBE_FAILED
        meaning = SCIA_EXIT_CODES.get(rc, "UNKNOWN") if rc is not None else "UNKNOWN"

    result = {
        "schema_version": "phoenix.scia-environment-live-probe/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "status": status,
        "live_execution_started": True,
        "analysis": analysis,
        "return_code": rc,
        "return_code_meaning": meaning,
        "timeout": timed_out,
        "working_copy": str(working),
        "original_project": str(project_esa),
        "service_actions_performed": [],
        "license_changes_performed": [],
        "safety": dict(SAFETY),
    }
    write_json(output_root / "scia_environment_probe_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)

    i = sub.add_parser("inspect")
    i.add_argument("--esa-xml", required=True)
    i.add_argument("--esa")
    i.add_argument("--lockman")
    i.add_argument("--license-target")
    i.add_argument("--output", required=True)

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
        )
        write_json(Path(args.output), result)
    else:
        result = probe_application_environment(
            Path(args.esa_xml),
            Path(args.project_esa),
            Path(args.output),
            args.allow_live_probe,
            args.analysis,
            args.timeout_seconds,
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if args.action == "probe" and result.get("status") != LIVE_PROBE_PASSED:
        raise SystemExit(2)
    if result.get("status") in {RUNTIME_NOT_FOUND, LIVE_PROBE_FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
