from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.adapters.open_source.calculix_windows import probe_ccx, run_ccx

MODEL = """*HEADING
PHOENIX CALCULIX 2.23 LINEAR STATIC ACCEPTANCE
*NODE, NSET=NALL
1, 0., 0., 0.
2, 10., 0., 0.
3, 10., 10., 0.
4, 0., 10., 0.
5, 0., 0., 10.
6, 10., 0., 10.
7, 10., 10., 10.
8, 0., 10., 10.
*ELEMENT, TYPE=C3D8, ELSET=EALL
1, 1,2,3,4,5,6,7,8
*MATERIAL, NAME=STEEL
*ELASTIC
210000., 0.3
*SOLID SECTION, ELSET=EALL, MATERIAL=STEEL
*BOUNDARY
1,1,3
4,1,3
5,1,3
8,1,3
*STEP
*STATIC, SOLVER=SPOOLES
*CLOAD
2,1,250.
3,1,250.
6,1,250.
7,1,250.
*NODE FILE
U
*EL FILE
S,E
*NODE PRINT, NSET=NALL
U
*EL PRINT, ELSET=EALL
S
*END STEP
"""

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_version(text: str) -> str:
    patterns = (
        r"CalculiX\s+Version\s+([0-9]+\.[0-9]+)",
        r"Version\s+([0-9]+\.[0-9]+)",
        r"ccx[_\s-]*([0-9]+\.[0-9]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return "2.23"

def run_acceptance(executable: Path, output_dir: Path, package_version: str = "2.23-1") -> dict:
    executable = executable.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model_stem = "phoenix_calculix_acceptance"
    inp = output_dir / f"{model_stem}.inp"
    dat = output_dir / f"{model_stem}.dat"
    frd = output_dir / f"{model_stem}.frd"
    inp.write_text(MODEL, encoding="ascii", newline="\n")

    probe = probe_ccx(executable)
    probe_stdout = output_dir / "calculix_probe_stdout.txt"
    probe_stderr = output_dir / "calculix_probe_stderr.txt"
    probe_stdout.write_text(probe.stdout or "", encoding="utf-8", newline="\n")
    probe_stderr.write_text(probe.stderr or "", encoding="utf-8", newline="\n")
    probe_text = (probe.stdout or "") + "\n" + (probe.stderr or "")
    if probe.returncode not in (0, 1) and "CalculiX" not in probe_text:
        raise RuntimeError(
            f"CalculiX launcher probe failed with exit code {probe.returncode}"
        )

    completed = run_ccx(executable, model_stem, output_dir)
    stdout_path = output_dir / "calculix_stdout.txt"
    stderr_path = output_dir / "calculix_stderr.txt"
    stdout_path.write_text(completed.stdout or "", encoding="utf-8", newline="\n")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8", newline="\n")

    combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
    version = parse_version(combined)

    if completed.returncode != 0:
        stdout_text = stdout_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        stderr_text = stderr_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        print("===== CALCULIX STDOUT =====", file=sys.stderr)
        print(stdout_text, file=sys.stderr)
        print("===== CALCULIX STDERR =====", file=sys.stderr)
        print(stderr_text, file=sys.stderr)
        raise RuntimeError(
            f"CalculiX solver failed with exit code {completed.returncode}"
        )
    combined_lower = combined.lower()
    if "pastix" in combined_lower:
        raise RuntimeError(
            "CalculiX acceptance unexpectedly selected PaStiX instead of SPOOLES"
        )
    if "spooles" not in combined_lower:
        raise RuntimeError(
            "CalculiX output does not confirm the required SPOOLES solver"
        )

    if not dat.is_file() or dat.stat().st_size == 0:
        raise RuntimeError("CalculiX DAT result missing")
    if not frd.is_file() or frd.stat().st_size == 0:
        raise RuntimeError("CalculiX FRD result missing")

    dat_text = dat.read_text(encoding="utf-8", errors="replace")
    frd_text = frd.read_text(encoding="utf-8", errors="replace")
    if "displacements" not in dat_text.lower():
        raise RuntimeError("CalculiX DAT lacks displacement results")
    if "1PSTEP" not in frd_text and "1C" not in frd_text:
        raise RuntimeError("CalculiX FRD lacks result dataset markers")

    result = {
        "schema_version": "phoenix.calculix-acceptance/5.4.9",
        "status": "ACCEPTED",
        "engine_id": "calculix",
        "version": version,
        "windows_binary_provider": "MSYS2",
        "msys2_package": "mingw-w64-x86_64-calculix-ccx",
        "msys2_package_version": package_version,
        "executable": str(executable),
        "launcher_probe_exit_code": probe.returncode,
        "runtime_path_prepend": str(executable.resolve().parent),
        "solver_exit_code": completed.returncode,
        "analysis": "linear_static_3d_solid_cube",
        "solver_argument_contract": ["-i", model_stem],
        "load_step_contract": "CLOAD_WITHIN_STATIC_STEP",
        "linear_solver_contract": "SPOOLES",
        "element_type": "C3D8",
        "acceptance_basis": "REAL_CCX_DAT_FRD_ARTIFACTS",
        "artifacts": [
            {
                "path": inp.name,
                "size_bytes": inp.stat().st_size,
                "sha256": sha256(inp),
            },
            {
                "path": dat.name,
                "size_bytes": dat.stat().st_size,
                "sha256": sha256(dat),
            },
            {
                "path": frd.name,
                "size_bytes": frd.stat().st_size,
                "sha256": sha256(frd),
            },
        ],
        "simulated": False,
        "professional_review_required": True,
    }
    (output_dir / "calculix_engine_acceptance.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--package-version", default="2.23-1")
    args = parser.parse_args()
    result = run_acceptance(Path(args.executable), Path(args.output), args.package_version)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
