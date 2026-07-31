from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ENGINES = ("freecad", "ifcopenshell", "qgis", "calculix", "opensees", "energyplus")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def artifact(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }

def run_command(args, *, cwd=None, timeout=1200, env=None) -> subprocess.CompletedProcess:
    cp = subprocess.run(
        [str(x) for x in args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return cp

def resolve_existing(candidates):
    for item in candidates:
        if not item:
            continue
        p = Path(item)
        if p.is_file():
            return p.resolve()
    return None

def resolve_ifcopenshell_python() -> Path:
    candidates = [
        os.environ.get("IFCOPENSHELL_PYTHON"),
        r"C:\Users\brewasplace\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    ]

    for command_name in ("python.exe", "py.exe", "python3.exe"):
        resolved = shutil.which(command_name)
        if resolved:
            candidates.append(resolved)

    seen = set()
    for item in candidates:
        if not item:
            continue
        path = Path(item)
        try:
            key = str(path.resolve())
        except Exception:
            key = str(path)
        if key.lower() in seen:
            continue
        seen.add(key.lower())

        if not path.is_file():
            continue
        if "Microsoft\\WindowsApps" in str(path):
            continue

        if path.name.lower() == "py.exe":
            cp = run_command(
                [path, "-3", "-c", "import sys;print(sys.executable)"],
                timeout=120,
            )
            if cp.returncode != 0:
                continue
            resolved_path = Path((cp.stdout or "").strip())
            if not resolved_path.is_file():
                continue
            path = resolved_path

        probe = run_command(
            [
                path,
                "-c",
                "import ifcopenshell,sys;"
                "print(sys.executable);"
                "print(ifcopenshell.version)",
            ],
            timeout=180,
        )
        if probe.returncode == 0:
            return path.resolve()

    raise RuntimeError(
        "No Python runtime with a working IfcOpenShell import was found"
    )


def qualify_ifcopenshell(engine_dir: Path) -> dict[str, Any]:
    python = resolve_ifcopenshell_python()
    script = engine_dir / "qualification_ifcopenshell.py"
    ifc_path = engine_dir / "qualification.ifc"
    result_path = engine_dir / "result.json"

    script.write_text(
        "import ifcopenshell,ifcopenshell.guid,json,sys\n"
        "model=ifcopenshell.file(schema='IFC4')\n"
        "project=model.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new(),Name='Phoenix Qualification')\n"
        "site=model.create_entity('IfcSite',GlobalId=ifcopenshell.guid.new(),Name='Qualification Site')\n"
        "building=model.create_entity('IfcBuilding',GlobalId=ifcopenshell.guid.new(),Name='Qualification Building')\n"
        "storey=model.create_entity('IfcBuildingStorey',GlobalId=ifcopenshell.guid.new(),Name='Ground Floor')\n"
        "model.create_entity('IfcRelAggregates',GlobalId=ifcopenshell.guid.new(),RelatingObject=project,RelatedObjects=[site])\n"
        "model.create_entity('IfcRelAggregates',GlobalId=ifcopenshell.guid.new(),RelatingObject=site,RelatedObjects=[building])\n"
        "model.create_entity('IfcRelAggregates',GlobalId=ifcopenshell.guid.new(),RelatingObject=building,RelatedObjects=[storey])\n"
        f"model.write(r'{ifc_path}')\n"
        f"reopened=ifcopenshell.open(r'{ifc_path}')\n"
        "projects=len(reopened.by_type('IfcProject'))\n"
        "buildings=len(reopened.by_type('IfcBuilding'))\n"
        "assert projects==1 and buildings==1\n"
        f"json.dump({{'version':ifcopenshell.version,'python':sys.executable,'projects':projects,'buildings':buildings}},open(r'{result_path}','w'),indent=2)\n",
        encoding="utf-8",
    )

    cp = run_command([python, script], cwd=engine_dir, timeout=300)
    (engine_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (engine_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")

    if cp.returncode != 0:
        raise RuntimeError(
            f"IfcOpenShell dedicated-runtime qualification failed with exit code {cp.returncode}"
        )
    if not ifc_path.is_file() or ifc_path.stat().st_size == 0:
        raise RuntimeError("IfcOpenShell produced no IFC artifact")
    if not result_path.is_file() or result_path.stat().st_size == 0:
        raise RuntimeError("IfcOpenShell produced no result record")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("projects") != 1 or result.get("buildings") != 1:
        raise RuntimeError("IfcOpenShell round-trip entity validation failed")

    return {
        "status": "PASSED",
        "version": result.get("version", "unknown"),
        "python_runtime": result.get("python"),
        "execution": "REAL_IFC4_CREATE_WRITE_REOPEN_DEDICATED_RUNTIME",
        "artifacts": [
            artifact(ifc_path, engine_dir.parent),
            artifact(result_path, engine_dir.parent),
        ],
    }

def qualify_freecad(engine_dir: Path) -> dict[str, Any]:
    exe = resolve_existing([
        os.environ.get("FREECAD_CMD"),
        r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
    ])
    if not exe:
        raise RuntimeError("FreeCADCmd executable not found")
    macro = engine_dir / "qualification_freecad.py"
    fcstd = engine_dir / "qualification.FCStd"
    step = engine_dir / "qualification.step"
    macro.write_text(
        "import FreeCAD as App, Part\n"
        "doc=App.newDocument('PhoenixQualification')\n"
        "obj=doc.addObject('Part::Feature','QualificationBox')\n"
        "obj.Shape=Part.makeBox(1000,500,300)\n"
        f"doc.recompute()\ndoc.saveAs(r'{fcstd}')\n"
        f"obj.Shape.exportStep(r'{step}')\n"
        "print('PHOENIX_FREECAD_OK')\n",
        encoding="utf-8",
    )
    cp = run_command([exe, str(macro)], cwd=engine_dir, timeout=600)
    (engine_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (engine_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
    if cp.returncode != 0 or not fcstd.is_file() or not step.is_file():
        raise RuntimeError(f"FreeCAD qualification failed with exit code {cp.returncode}")
    if fcstd.stat().st_size == 0 or step.stat().st_size == 0:
        raise RuntimeError("FreeCAD generated empty model artifacts")
    version_cp = run_command([exe, "--version"], timeout=120)
    return {
        "status": "PASSED",
        "version": (version_cp.stdout or version_cp.stderr).strip(),
        "executable": str(exe),
        "execution": "REAL_PARAMETRIC_BOX_FCSTD_STEP",
        "artifacts": [artifact(p, engine_dir.parent) for p in (fcstd, step)],
    }

def qualify_qgis(engine_dir: Path) -> dict[str, Any]:
    launcher = resolve_existing([
        os.environ.get("QGIS_PROCESS_EXE"),
        r"C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat",
        r"C:\OSGeo4W\bin\qgis_process-qgis.bat",
        r"C:\OSGeo4W\bin\qgis_process.bat",
        r"C:\OSGeo4W\bin\qgis_process.exe",
    ])
    if not launcher:
        raise RuntimeError("QGIS processing launcher not found")
    source = engine_dir / "input.geojson"
    output = engine_dir / "buffer.gpkg"
    source.write_text(json.dumps({
        "type": "FeatureCollection",
        "name": "phoenix_input",
        "crs": {"type": "name", "properties": {"name": "EPSG:28992"}},
        "features": [{
            "type": "Feature",
            "properties": {"id": 1},
            "geometry": {"type": "Point", "coordinates": [155000.0, 463000.0]}
        }]
    }), encoding="utf-8")
    if launcher.suffix.lower() in {".bat", ".cmd"}:
        args = ["cmd.exe", "/d", "/c", str(launcher), "run", "native:buffer",
                "--", f"INPUT={source}", "DISTANCE=10", "SEGMENTS=8",
                "DISSOLVE=false", f"OUTPUT={output}"]
    else:
        args = [launcher, "run", "native:buffer", "--",
                f"INPUT={source}", "DISTANCE=10", "SEGMENTS=8",
                "DISSOLVE=false", f"OUTPUT={output}"]
    cp = run_command(args, cwd=engine_dir, timeout=900)
    (engine_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (engine_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
    if cp.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"QGIS buffer qualification failed with exit code {cp.returncode}")
    version_args = ["cmd.exe", "/d", "/c", str(launcher), "--version"] if launcher.suffix.lower() in {".bat", ".cmd"} else [launcher, "--version"]
    vp = run_command(version_args, timeout=180)
    return {
        "status": "PASSED",
        "version": (vp.stdout or vp.stderr).strip(),
        "executable": str(launcher),
        "execution": "REAL_NATIVE_BUFFER_GPKG",
        "artifacts": [artifact(source, engine_dir.parent), artifact(output, engine_dir.parent)],
    }

def qualify_calculix(engine_dir: Path) -> dict[str, Any]:
    exe = resolve_existing([
        os.environ.get("CALCULIX_CCX_EXE"),
        r"C:\msys64\mingw64\bin\ccx.exe",
    ])
    if not exe:
        raise RuntimeError("CalculiX CCX executable not found")

    repository = Path.cwd().resolve()
    acceptance_script = (
        repository
        / "phoenix"
        / "adapters"
        / "open_source"
        / "calculix_acceptance_v5_4_9.py"
    )
    if not acceptance_script.is_file():
        raise RuntimeError(
            "Verified CalculiX v5.4.9 acceptance module is missing: "
            f"{acceptance_script}"
        )

    cp = run_command(
        [
            sys.executable,
            acceptance_script,
            "--executable",
            exe,
            "--output",
            engine_dir,
            "--package-version",
            "2.23-1",
        ],
        cwd=repository,
        timeout=1200,
    )

    suite_stdout = engine_dir / "suite_acceptance_stdout.txt"
    suite_stderr = engine_dir / "suite_acceptance_stderr.txt"
    suite_stdout.write_text(cp.stdout or "", encoding="utf-8")
    suite_stderr.write_text(cp.stderr or "", encoding="utf-8")

    evidence_path = engine_dir / "calculix_engine_acceptance.json"
    required_paths = [
        engine_dir / "phoenix_calculix_acceptance.inp",
        engine_dir / "phoenix_calculix_acceptance.dat",
        engine_dir / "phoenix_calculix_acceptance.frd",
        evidence_path,
        engine_dir / "calculix_stdout.txt",
        engine_dir / "calculix_stderr.txt",
    ]

    if cp.returncode != 0:
        raise RuntimeError(
            "Verified CalculiX v5.4.9 acceptance failed with exit code "
            f"{cp.returncode}. See "
            f"{suite_stdout.name} and {suite_stderr.name}."
        )

    for path in required_paths:
        if not path.is_file():
            raise RuntimeError(
                f"Verified CalculiX acceptance artifact missing: {path.name}"
            )

    for path in required_paths[:4]:
        if path.stat().st_size == 0:
            raise RuntimeError(
                f"Verified CalculiX acceptance artifact is empty: {path.name}"
            )

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    required_evidence = {
        "status": "ACCEPTED",
        "engine_id": "calculix",
        "linear_solver_contract": "SPOOLES",
        "load_step_contract": "CLOAD_WITHIN_STATIC_STEP",
        "element_type": "C3D8",
        "acceptance_basis": "REAL_CCX_DAT_FRD_ARTIFACTS",
        "simulated": False,
    }
    for key, expected in required_evidence.items():
        if evidence.get(key) != expected:
            raise RuntimeError(
                "Verified CalculiX acceptance evidence mismatch: "
                f"{key}={evidence.get(key)!r}, expected {expected!r}"
            )

    if evidence.get("solver_exit_code") != 0:
        raise RuntimeError("Verified CalculiX solver exit code is not zero")

    dat_path = engine_dir / "phoenix_calculix_acceptance.dat"
    frd_path = engine_dir / "phoenix_calculix_acceptance.frd"
    dat_text = dat_path.read_text(encoding="utf-8", errors="replace")
    frd_text = frd_path.read_text(encoding="utf-8", errors="replace")
    if "displacements" not in dat_text.lower():
        raise RuntimeError("Verified CalculiX DAT lacks displacements")
    if "1PSTEP" not in frd_text and "1C" not in frd_text:
        raise RuntimeError("Verified CalculiX FRD lacks dataset markers")

    solver_stdout = (
        engine_dir / "calculix_stdout.txt"
    ).read_text(encoding="utf-8", errors="replace")
    solver_stderr = (
        engine_dir / "calculix_stderr.txt"
    ).read_text(encoding="utf-8", errors="replace")
    solver_output = (solver_stdout + "\n" + solver_stderr).lower()
    if "pastix" in solver_output:
        raise RuntimeError(
            "Verified CalculiX qualification unexpectedly selected PaStiX"
        )
    if "spooles" not in solver_output:
        raise RuntimeError(
            "Verified CalculiX qualification did not confirm SPOOLES"
        )

    artifacts = [
        artifact(path, engine_dir.parent)
        for path in required_paths
        if path.is_file()
    ]
    artifacts.extend([
        artifact(suite_stdout, engine_dir.parent),
        artifact(suite_stderr, engine_dir.parent),
    ])

    return {
        "status": "PASSED",
        "version": evidence.get("version", "2.23"),
        "executable": str(exe),
        "execution": (
            "REUSED_VERIFIED_CALCULIX_V5_4_9_"
            "C3D8_SPOOLES_DAT_FRD_ACCEPTANCE"
        ),
        "verified_acceptance_contract": "5.4.9",
        "solver": "SPOOLES",
        "solver_exit_code": evidence.get("solver_exit_code"),
        "acceptance_basis": evidence.get("acceptance_basis"),
        "artifacts": artifacts,
    }

def qualify_opensees(engine_dir: Path) -> dict[str, Any]:
    python = resolve_existing([
        os.environ.get("OPENSEESPY_PYTHON"),
        r"C:\PHOENIX-ENGINES\OpenSeesPy\3.8.0.0\venv\Scripts\python.exe",
    ])
    if not python:
        raise RuntimeError("Dedicated OpenSeesPy Python runtime not found")
    script = engine_dir / "qualification_opensees.py"
    result = engine_dir / "result.json"
    script.write_text(
        "import json,openseespy.opensees as ops\n"
        "ops.wipe();ops.model('basic','-ndm',2,'-ndf',2)\n"
        "ops.node(1,0,0);ops.node(2,1,0);ops.fix(1,1,1);ops.fix(2,0,1)\n"
        "ops.uniaxialMaterial('Elastic',1,200000.0)\n"
        "ops.element('truss',1,1,2,0.01,1)\n"
        "ops.timeSeries('Linear',1);ops.pattern('Plain',1,1);ops.load(2,100.0,0.0)\n"
        "ops.system('BandSPD');ops.numberer('RCM');ops.constraints('Plain')\n"
        "ops.integrator('LoadControl',1.0);ops.algorithm('Linear');ops.analysis('Static')\n"
        "code=ops.analyze(1);ops.reactions();u=ops.nodeDisp(2,1);r=ops.nodeReaction(1,1)\n"
        f"json.dump({{'code':code,'u':u,'reaction':r,'version':ops.version()}},open(r'{result}','w'),indent=2)\n"
        "assert code==0 and abs(r+100.0)<1e-6 and u>0\n",
        encoding="utf-8",
    )
    cp = run_command([python, script], cwd=engine_dir, timeout=300)
    (engine_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (engine_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
    if cp.returncode != 0 or not result.is_file():
        raise RuntimeError(f"OpenSees qualification failed with exit code {cp.returncode}")
    data = json.loads(result.read_text(encoding="utf-8"))
    return {
        "status": "PASSED",
        "version": data["version"],
        "executable": str(python),
        "execution": "REAL_LINEAR_STATIC_2D_TRUSS",
        "artifacts": [artifact(result, engine_dir.parent)],
    }

def qualify_energyplus(engine_dir: Path) -> dict[str, Any]:
    exe = resolve_existing([
        os.environ.get("ENERGYPLUS_EXE"),
        r"C:\PHOENIX-ENGINES\EnergyPlus\26.1.0\energyplus.exe",
    ])
    if not exe:
        raise RuntimeError("EnergyPlus executable not found")
    examples = list((exe.parent / "ExampleFiles").glob("1ZoneUncontrolled*.idf"))
    if not examples:
        raise RuntimeError("EnergyPlus official example model not found")
    model = engine_dir / "qualification.idf"
    shutil.copy2(examples[0], model)
    text = model.read_text(encoding="utf-8", errors="replace")
    if "Output:SQLite" not in text:
        model.write_text(text.rstrip() + "\n\nOutput:SQLite,\n  SimpleAndTabular;\n", encoding="utf-8")
    cp = run_command([exe, "-D", "-d", engine_dir, model], cwd=engine_dir, timeout=1800)
    (engine_dir / "stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (engine_dir / "stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
    required = [engine_dir / "eplusout.err", engine_dir / "eplusout.end", engine_dir / "eplusout.sql"]
    if cp.returncode != 0 or any(not p.is_file() or p.stat().st_size == 0 for p in required):
        raise RuntimeError(f"EnergyPlus qualification failed with exit code {cp.returncode}")
    err = required[0].read_text(encoding="utf-8", errors="replace")
    if "** Severe  **" in err or "** Fatal  **" in err:
        raise RuntimeError("EnergyPlus reported Severe or Fatal errors")
    vp = run_command([exe, "--version"], timeout=120)
    return {
        "status": "PASSED",
        "version": (vp.stdout or vp.stderr).strip(),
        "executable": str(exe),
        "execution": "REAL_DESIGN_DAY_SQLITE",
        "artifacts": [artifact(p, engine_dir.parent) for p in [model, *required]],
    }

QUALIFIERS = {
    "freecad": qualify_freecad,
    "ifcopenshell": qualify_ifcopenshell,
    "qgis": qualify_qgis,
    "calculix": qualify_calculix,
    "opensees": qualify_opensees,
    "energyplus": qualify_energyplus,
}

def write_reports(output: Path, results: dict[str, Any]) -> None:
    all_passed = all(results[e].get("status") == "PASSED" for e in ENGINES)
    report = {
        "schema_version": "phoenix.multi-engine-qualification/6.0.0",
        "suite_id": "PHX-MEQS-600",
        "status": "PASSED" if all_passed else "FAILED",
        "simulated": False,
        "qualified_engines": sum(1 for e in ENGINES if results[e].get("status") == "PASSED"),
        "required_engines": len(ENGINES),
        "engines": results,
        "production_release": "UNLOCKED" if all_passed else "LOCKED",
        "professional_review_required": True,
    }
    (output / "multi_engine_qualification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    artifacts = []
    for p in sorted(output.rglob("*")):
        if p.is_file() and p.name not in {"artifact_manifest.json"}:
            artifacts.append(artifact(p, output))
    (output / "artifact_manifest.json").write_text(
        json.dumps({"artifacts": artifacts}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    gate = {
        "status": "UNLOCKED" if all_passed else "LOCKED",
        "basis": "ALL_SIX_REAL_ENGINE_QUALIFICATIONS_PASSED" if all_passed else "ONE_OR_MORE_ENGINE_QUALIFICATIONS_FAILED",
        "simulated_results_allowed": False,
    }
    (output / "production_release_gate.json").write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Project Phoenix Multi-Engine Qualification v6.0.0",
        "",
        f"**Status:** {report['status']}",
        f"**Production release:** {report['production_release']}",
        "",
        "| Engine | Status | Real execution | Version |",
        "|---|---:|---|---|",
    ]
    for engine in ENGINES:
        r = results[engine]
        lines.append(f"| {engine} | {r.get('status')} | {r.get('execution','-')} | {str(r.get('version','-')).replace('|','/')} |")
    lines += [
        "",
        "All results are generated by installed third-party engines. Simulated results are disabled.",
        "Professional review remains mandatory before project release.",
    ]
    (output / "multi_engine_qualification.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    results = {}
    for engine in ENGINES:
        engine_dir = output / engine
        engine_dir.mkdir()
        started = time.time()
        try:
            result = QUALIFIERS[engine](engine_dir)
            result["duration_seconds"] = round(time.time() - started, 3)
            result["simulated"] = False
            results[engine] = result
            print(f"{engine}: PASSED")
        except Exception as exc:
            results[engine] = {
                "status": "FAILED",
                "error": str(exc),
                "duration_seconds": round(time.time() - started, 3),
                "simulated": False,
            }
            print(f"{engine}: FAILED: {exc}", file=sys.stderr)
            write_reports(output, results | {e: results.get(e, {"status":"NOT_RUN"}) for e in ENGINES})
            return 1
    write_reports(output, results)
    print("UNIFIED MULTI-ENGINE QUALIFICATION: PASSED")
    print("PRODUCTION RELEASE GATE: UNLOCKED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
