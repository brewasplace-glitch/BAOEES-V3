from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

PLACEHOLDER = "__PHOENIX_OUTPUT_DIR__"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build_runtime_macro(template_path: Path, output_dir: Path) -> Path:
    template = template_path.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise ValueError(f"FreeCAD macro template lacks {PLACEHOLDER}")
    absolute_output = str(output_dir.resolve()).replace("\\", "\\\\")
    runtime = template.replace(PLACEHOLDER, absolute_output)
    runtime_path = output_dir / "_phoenix_freecad_runtime_macro.py"
    runtime_path.write_text(runtime, encoding="utf-8", newline="\n")
    return runtime_path

def run_acceptance(executable: Path, script: Path, output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime_script = build_runtime_macro(script.resolve(), output_dir)

    version = subprocess.run(
        [str(executable.resolve()), "--version"],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    smoke = subprocess.run(
        [str(executable.resolve()), str(runtime_script)],
        cwd=str(output_dir),
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )

    (output_dir / "freecad_version_stdout.txt").write_text(
        version.stdout or "", encoding="utf-8", newline="\n"
    )
    (output_dir / "freecad_version_stderr.txt").write_text(
        version.stderr or "", encoding="utf-8", newline="\n"
    )
    (output_dir / "freecad_smoke_stdout.txt").write_text(
        smoke.stdout or "", encoding="utf-8", newline="\n"
    )
    (output_dir / "freecad_smoke_stderr.txt").write_text(
        smoke.stderr or "", encoding="utf-8", newline="\n"
    )

    fcstd = output_dir / "phoenix_freecad_acceptance.FCStd"
    step = output_dir / "phoenix_freecad_acceptance.step"

    if version.returncode != 0:
        raise RuntimeError(
            f"FreeCAD version probe failed with exit code {version.returncode}"
        )
    if smoke.returncode != 0:
        raise RuntimeError(
            "FreeCAD smoke test failed with exit code "
            f"{smoke.returncode}. See freecad_smoke_stdout.txt and freecad_smoke_stderr.txt."
        )
    if not fcstd.is_file() or fcstd.stat().st_size == 0:
        raise RuntimeError(
            "FreeCAD FCStd acceptance artifact missing. "
            "See freecad_smoke_stdout.txt and freecad_smoke_stderr.txt."
        )
    if not step.is_file() or step.stat().st_size == 0:
        raise RuntimeError(
            "FreeCAD STEP acceptance artifact missing. "
            "See freecad_smoke_stdout.txt and freecad_smoke_stderr.txt."
        )
    step_head = step.read_bytes()[:512].decode("latin-1", errors="ignore").upper()
    if "ISO-10303-21" not in step_head:
        raise RuntimeError("Generated STEP file lacks ISO-10303-21 header")

    result = {
        "schema_version": "phoenix.freecad-acceptance/5.2.2",
        "status": "ACCEPTED",
        "executable": str(executable.resolve()),
        "version_output": (version.stdout or version.stderr).strip(),
        "runtime_macro": str(runtime_script),
        "artifacts": [
            {
                "path": fcstd.name,
                "size_bytes": fcstd.stat().st_size,
                "sha256": sha256(fcstd),
            },
            {
                "path": step.name,
                "size_bytes": step.stat().st_size,
                "sha256": sha256(step),
            },
        ],
        "simulated": False,
        "professional_review_required": True,
    }
    (output_dir / "freecad_engine_acceptance.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    parser.add_argument("--script", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run_acceptance(
        Path(args.executable),
        Path(args.script),
        Path(args.output),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
