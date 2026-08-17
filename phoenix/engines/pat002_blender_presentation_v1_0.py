"""PROJECT PHOENIX PAT-002 real IFC -> Blender presentation activation v1.0."""
from __future__ import annotations

import json
import subprocess
import struct
from pathlib import Path

from phoenix.engines.ifc_visual_mesh_adapter_v1_0 import ifc_to_obj
from phoenix.engines.visual_engine_discovery_v1_0 import discover_executable

VERSION = "1.0.0"
SCHEMA = "phoenix.pat002-real-ifc-blender-presentation/1.0"


def verify_cycles_cpu_bootstrap(blender_executable: Path, timeout: int = 180) -> dict:
    import tempfile
    exe = Path(blender_executable).resolve()
    if not exe.exists():
        return {
            "passed": False,
            "reason": "BLENDER_EXECUTABLE_NOT_FOUND",
            "executable": str(exe),
        }

    expr = (
        "import bpy;"
        "s=bpy.context.scene;"
        "assert s.render.engine=='CYCLES', s.render.engine;"
        "s.cycles.device='CPU';"
        "print('PHOENIX_CYCLES_CPU_BOOTSTRAP_OK');"
        "print('ENGINE=', s.render.engine)"
    )

    with tempfile.TemporaryDirectory(prefix="phoenix_cycles_cli_bootstrap_") as td:
        p = subprocess.run(
            [
                str(exe),
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "23",
                "-E",
                "CYCLES",
                "--python-expr",
                expr,
            ],
            cwd=td,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    text = (p.stdout or "") + "\n" + (p.stderr or "")
    return {
        "passed": (
            p.returncode == 0
            and "PHOENIX_CYCLES_CPU_BOOTSTRAP_OK" in text
            and "ENGINE= CYCLES" in text
        ),
        "returncode": p.returncode,
        "stdout": p.stdout[-6000:],
        "stderr": p.stderr[-6000:],
        "executable": str(exe),
        "bootstrap_method": "BLENDER_CLI_-E_CYCLES",
    }


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def _write_json(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _resolve_ifc(workspace: Path, arch: Path) -> Path:
    model_path = Path(arch) / "architectural_model.json"
    if model_path.exists():
        data = _read_json(model_path)
        raw = data.get("authoritative_ifc")
        if raw and Path(raw).exists():
            return Path(raw).resolve()
    candidates = sorted((Path(arch) / "ifc").glob("*_architectural_authoritative.ifc"))
    if len(candidates) == 1:
        return candidates[0].resolve()
    if not candidates:
        raise RuntimeError("AUTHORITATIVE_IFC_NOT_FOUND_FOR_BLENDER_PRESENTATION")
    raise RuntimeError("AUTHORITATIVE_IFC_AMBIGUOUS_FOR_BLENDER_PRESENTATION")

def activate_blender_presentation(repository: Path, workspace: Path, arch: Path, selected: dict, variants: list) -> dict:
    repository = Path(repository).resolve()
    workspace = Path(workspace).resolve()
    arch = Path(arch).resolve()
    project_id = str(selected["project_id"])
    if project_id.upper() != "PHOENIX-PAT-002":
        return {
            "schema_version": SCHEMA,
            "version": VERSION,
            "status": "SKIPPED",
            "reason": "PAT002_SCOPED_ACTIVATION",
            "project_id": project_id,
        }

    ifc_path = _resolve_ifc(workspace, arch)
    blender = discover_executable("blender", repository)
    if not blender.get("available"):
        raise RuntimeError("BLENDER_REQUIRED_FOR_PAT002_PRESENTATION_NOT_AVAILABLE")

    cycles_bootstrap = verify_cycles_cpu_bootstrap(Path(blender["executable"]))
    if not cycles_bootstrap.get("passed"):
        raise RuntimeError(
            "BLENDER_CYCLES_CPU_BOOTSTRAP_FAILED "
            f"returncode={cycles_bootstrap.get('returncode')} "
            f"stdout_tail={' '.join((cycles_bootstrap.get('stdout') or '').split())[-2500:]!r} "
            f"stderr_tail={' '.join((cycles_bootstrap.get('stderr') or '').split())[-2500:]!r}"
        )

    out_dir = workspace / "results" / "generated_visual_media" / "blender_presentation"
    out_dir.mkdir(parents=True, exist_ok=True)

    obj_path = out_dir / f"{project_id}_authoritative_ifc.obj"
    mesh_evidence = ifc_to_obj(ifc_path, obj_path)

    script = Path(__file__).resolve().parent / "adapters" / "blender_pat002_presentation_script_v1_0.py"
    if not script.exists():
        raise RuntimeError(f"BLENDER_PRESENTATION_SCRIPT_MISSING: {script}")

    cmd = [
        str(blender["executable"]),
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "23",
        "-E",
        "CYCLES",
        "--python",
        str(script),
        "--",
        str(obj_path),
        str(out_dir),
        project_id,
        str(selected["variant"]["id"]),
        str(selected["variant"]["name"]),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(out_dir),
        capture_output=True,
        text=True,
        timeout=900,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    expected = {
        "exterior_front": out_dir / "phoenix_exterior_front.png",
        "exterior_rear": out_dir / "phoenix_exterior_rear.png",
        "bird_view": out_dir / "phoenix_bird_view.png",
        "interior_cutaway": out_dir / "phoenix_interior_cutaway.png",
    }

    def _png_quality(path: Path) -> dict:
        result = {
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "png_signature": False,
            "width": None,
            "height": None,
            "valid": False,
        }
        if not path.exists():
            return result
        try:
            raw = path.read_bytes()
            result["png_signature"] = raw[:8] == bytes.fromhex("89504E470D0A1A0A")
            if len(raw) >= 24 and result["png_signature"] and raw[12:16] == b"IHDR":
                result["width"], result["height"] = struct.unpack(">II", raw[16:24])
            result["valid"] = bool(
                result["png_signature"]
                and result["width"] is not None
                and result["height"] is not None
                and result["width"] >= 1280
                and result["height"] >= 720
                and result["size_bytes"] >= 1500
            )
        except Exception:
            result["valid"] = False
        return result

    quality = {name: _png_quality(path) for name, path in expected.items()}
    invalid = [name for name, check in quality.items() if not check["valid"]]
    scene_evidence = out_dir / "phoenix_blender_scene_evidence.txt"
    scene_ok = scene_evidence.exists() and scene_evidence.stat().st_size > 10

    if proc.returncode != 0 or invalid or not scene_ok:
        evidence = {
            "schema_version": SCHEMA,
            "version": VERSION,
            "project_id": project_id,
            "status": "FAILED",
            "returncode": proc.returncode,
            "invalid_pngs": invalid,
            "png_quality": quality,
            "scene_evidence_ok": scene_ok,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "source_ifc": str(ifc_path),
            "obj": str(obj_path),
        }
        _write_json(out_dir / "blender_presentation_failure.json", evidence)
        stdout_tail = " ".join((proc.stdout or "").split())[-2500:]
        stderr_tail = " ".join((proc.stderr or "").split())[-2500:]
        raise RuntimeError(
            f"BLENDER_PRESENTATION_FAILED returncode={proc.returncode} "
            f"invalid_pngs={invalid} scene_evidence_ok={scene_ok} "
            f"stdout_tail={stdout_tail!r} stderr_tail={stderr_tail!r}"
        )

    artifacts = {name: str(path.resolve()) for name, path in expected.items()}
    manifest = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "status": "PASSED",
        "project_id": project_id,
        "selected_variant": selected["variant"]["id"],
        "selected_variant_name": selected["variant"]["name"],
        "authoritative_geometry": "IFC",
        "source_ifc": str(ifc_path),
        "derived_mesh": str(obj_path),
        "mesh_evidence": mesh_evidence,
        "renderer": "Blender",
        "blender_executable": blender["executable"],
        "blender_version": blender.get("version"),
        "cycles_cpu_bootstrap": cycles_bootstrap,
        "artifacts": artifacts,
        "png_quality": quality,
        "scene_evidence": str(scene_evidence),
        "tv_primary": artifacts["exterior_front"],
        "presentation_only": True,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    _write_json(out_dir / "blender_presentation_manifest.json", manifest)

    # Publish a compact pointer into architecture state without changing IFC authority.
    model_path = arch / "architectural_model.json"
    if model_path.exists():
        data = _read_json(model_path)
        data["blender_presentation"] = {
            "status": "PASSED",
            "manifest": str(out_dir / "blender_presentation_manifest.json"),
            "artifacts": artifacts,
            "source_geometry": "IFC_AUTHORITATIVE",
            "presentation_only": True,
        }
        _write_json(model_path, data)

    for twin_path in (
        workspace / "results" / "session_adapters" / "digital_twin" / "central_project_digital_twin.json",
        workspace / "digital_twin" / "central_project_digital_twin.json",
    ):
        if twin_path.exists():
            twin = _read_json(twin_path)
            twin["architectural_visual_presentation"] = {
                "engine": "Blender",
                "source_geometry": "IFC_AUTHORITATIVE",
                "selected_variant": selected["variant"]["id"],
                "artifacts": artifacts,
                "manifest": str(out_dir / "blender_presentation_manifest.json"),
                "presentation_only": True,
                "production_release": "LOCKED",
            }
            _write_json(twin_path, twin)

    return manifest
