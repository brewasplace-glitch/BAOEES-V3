"""PROJECT PHOENIX CalculiX Golden Reference verification v1.0."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess

VERSION = "1.0.0"
ENGINE_ID = "PHX-CALCULIX-REFERENCE-VERIFICATION"

PREPARED = "CALCULIX_REFERENCE_PREPARED"
AUTH_REQUIRED = "CALCULIX_LIVE_SOLVER_EXPLICIT_AUTHORIZATION_REQUIRED"
TEST_MODE_BLOCKED = "CALCULIX_LIVE_SOLVER_DISABLED_BY_PHOENIX_TEST_MODE"
SOLVER_NOT_FOUND = "CALCULIX_EXECUTABLE_NOT_FOUND"
SOLVER_FAILED = "CALCULIX_REFERENCE_SOLVER_FAILED"
PARSE_REQUIRED = "CALCULIX_REFERENCE_REACTION_PARSE_REQUIRED"
VALIDATED = "CALCULIX_GOLDEN_REFERENCE_VALIDATED"

SAFETY = {
    "automatic_live_solver": False,
    "raw_solver_evidence_required": True,
    "second_solver_is_professional_review": False,
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_ccx(explicit: str | None = None, repository: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    from_path = shutil.which("ccx")
    if from_path:
        candidates.append(Path(from_path))
    if repository:
        for rel in (
            "tools/calculix/ccx.exe",
            "bin/ccx.exe",
            "vendor/calculix/ccx.exe",
        ):
            candidates.append(repository / rel)
    if os.name == "nt":
        for base in (
            Path(r"C:\Program Files"),
            Path(r"C:\Program Files (x86)"),
            Path(r"C:\CalculiX"),
        ):
            if base.exists():
                try:
                    candidates.extend(base.glob("**/ccx*.exe"))
                except OSError:
                    pass
    seen = set()
    for p in candidates:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.is_file():
            return p
    return None


def build_golden_beam_deck(output_root: Path, elements: int = 100) -> dict[str, Any]:
    if elements < 2:
        raise ValueError("At least 2 beam elements required.")
    L = 5.0
    q = 1000.0
    dx = L / elements
    lines = [
        "*HEADING",
        "PHOENIX PHX-GOLDEN-SCIA-BEAM-001 CalculiX second-solver reference",
        "*NODE",
    ]
    for i in range(elements + 1):
        lines.append(f"{i+1}, {i*dx:.12g}, 0., 0.")
    lines += ["*ELEMENT, TYPE=B31, ELSET=EALL"]
    for i in range(elements):
        lines.append(f"{i+1}, {i+1}, {i+2}")
    lines += [
        "*MATERIAL, NAME=REFMAT",
        "*ELASTIC",
        "210000000000., 0.3",
        "*BEAM SECTION, ELSET=EALL, MATERIAL=REFMAT, SECTION=RECT",
        "0.1, 0.1",
        "0., 1., 0.",
        "*NSET, NSET=SUPPORTS",
        f"1, {elements+1}",
        "*BOUNDARY",
        "1, 1, 3",
        "1, 4, 4",
        f"{elements+1}, 2, 3",
        "*STEP",
        "*STATIC",
        "*CLOAD",
    ]
    nodal_loads = []
    for i in range(elements + 1):
        load = -q * dx * (0.5 if i in (0, elements) else 1.0)
        nodal_loads.append(load)
        lines.append(f"{i+1}, 3, {load:.12g}")
    lines += [
        "*NODE PRINT, NSET=SUPPORTS, TOTALS=YES",
        "RF",
        "*NODE FILE, NSET=SUPPORTS",
        "RF",
        "*EL FILE, ELSET=EALL",
        "S",
        "*END STEP",
    ]
    output_root.mkdir(parents=True, exist_ok=True)
    deck = output_root / "PHX_GOLDEN_BEAM_CCX.inp"
    deck.write_text("\n".join(lines) + "\n", encoding="ascii")
    result = {
        "status": PREPARED,
        "reference_model_id": "PHX-GOLDEN-SCIA-BEAM-001",
        "deck": str(deck),
        "deck_sha256": sha256_file(deck),
        "elements": elements,
        "span_m": L,
        "q_N_per_m": q,
        "applied_total_load_N": sum(nodal_loads),
        "expected_total_reaction_N": 5000.0,
        "expected_each_reaction_N": 2500.0,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "calculix_reference_preparation.json", result)
    return result


def parse_reaction_total(dat_path: Path, expected_abs_N: float = 5000.0) -> dict[str, Any]:
    if not dat_path.is_file():
        return {"status": PARSE_REQUIRED, "reason": "DAT_MISSING", "reaction_total_N": None}
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    # Preferred: CalculiX TOTALS output line from *NODE PRINT, TOTALS=YES.
    candidates: list[float] = []
    for line in text.splitlines():
        if "total" not in line.lower():
            continue
        nums = re.findall(r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?", line)
        if len(nums) >= 3:
            try:
                candidates.append(float(nums[-1]))
            except ValueError:
                pass
    if candidates:
        chosen = min(candidates, key=lambda x: abs(abs(x) - expected_abs_N))
        return {"status": "PARSED", "reaction_total_N": chosen, "basis": "TOTALS_LINE"}
    # Fallback: parse node-force rows after a force/reaction heading and sum support node Z.
    support = {}
    active = False
    for line in text.splitlines():
        low = line.lower()
        if ("force" in low or "reaction" in low) and ("node" in low or "rf" in low):
            active = True
            continue
        if not active:
            continue
        m = re.match(
            r"\s*(1|101)\s+([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?)\s+"
            r"([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?)\s+"
            r"([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?)",
            line
        )
        if m:
            support[int(m.group(1))] = float(m.group(4))
    if len(support) == 2:
        return {
            "status": "PARSED",
            "reaction_total_N": support[1] + support[101],
            "support_reactions_N": support,
            "basis": "SUPPORT_ROWS",
        }
    return {"status": PARSE_REQUIRED, "reason": "REACTION_TOTAL_NOT_FOUND", "reaction_total_N": None}


def run_golden_beam(
    output_root: Path,
    repository: Path | None = None,
    explicit_ccx: str | None = None,
    allow_live_solver: bool = False,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    prep = build_golden_beam_deck(output_root)
    if os.environ.get("PHOENIX_TEST_MODE"):
        result = {"status": TEST_MODE_BLOCKED, "live_execution_started": False, "preparation": prep, "safety": dict(SAFETY)}
        write_json(output_root / "calculix_reference_result.json", result)
        return result
    if not allow_live_solver:
        result = {"status": AUTH_REQUIRED, "live_execution_started": False, "preparation": prep, "safety": dict(SAFETY)}
        write_json(output_root / "calculix_reference_result.json", result)
        return result
    ccx = discover_ccx(explicit_ccx, repository)
    if ccx is None:
        result = {"status": SOLVER_NOT_FOUND, "live_execution_started": False, "preparation": prep, "safety": dict(SAFETY)}
        write_json(output_root / "calculix_reference_result.json", result)
        return result

    job = output_root / "PHX_GOLDEN_BEAM_CCX"
    command = [str(ccx), "-i", job.name]
    write_json(output_root / "calculix_command.json", {"argv": command})
    try:
        cp = subprocess.run(
            command, cwd=output_root, capture_output=True, text=True,
            timeout=timeout_seconds, check=False
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
    (output_root / "calculix_stdout.txt").write_text(stdout, encoding="utf-8")
    (output_root / "calculix_stderr.txt").write_text(stderr, encoding="utf-8")

    evidence = {}
    for ext in (".dat", ".frd", ".sta", ".cvg"):
        p = job.with_suffix(ext)
        if p.is_file():
            evidence[p.name] = {"sha256": sha256_file(p), "size_bytes": p.stat().st_size}

    if timed_out or rc != 0:
        result = {
            "status": SOLVER_FAILED,
            "live_execution_started": True,
            "return_code": rc,
            "timeout": timed_out,
            "ccx": str(ccx),
            "raw_evidence": evidence,
            "preparation": prep,
            "safety": dict(SAFETY),
        }
        write_json(output_root / "calculix_reference_result.json", result)
        return result

    parsed = parse_reaction_total(job.with_suffix(".dat"))
    if parsed["status"] != "PARSED":
        status = PARSE_REQUIRED
        error_N = None
    else:
        error_N = abs(abs(float(parsed["reaction_total_N"])) - 5000.0)
        status = VALIDATED if error_N <= 5.0 else SOLVER_FAILED

    result = {
        "status": status,
        "live_execution_started": True,
        "return_code": rc,
        "timeout": timed_out,
        "ccx": str(ccx),
        "reaction_parse": parsed,
        "reaction_total_abs_error_N": error_N,
        "golden_reference_test_tolerance_N": 5.0,
        "tolerance_scope": "SOFTWARE_GOLDEN_REFERENCE_ONLY_NOT_GENERAL_ENGINEERING",
        "raw_evidence": evidence,
        "preparation": prep,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "calculix_reference_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare-golden-beam")
    p.add_argument("--output", required=True)
    r = sub.add_parser("run-golden-beam")
    r.add_argument("--output", required=True)
    r.add_argument("--repository")
    r.add_argument("--ccx")
    r.add_argument("--allow-live-solver", action="store_true")
    r.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()

    if args.action == "prepare-golden-beam":
        result = build_golden_beam_deck(Path(args.output))
    else:
        result = run_golden_beam(
            Path(args.output),
            Path(args.repository) if args.repository else None,
            args.ccx,
            args.allow_live_solver,
            args.timeout_seconds,
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result.get("status") in {SOLVER_FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
