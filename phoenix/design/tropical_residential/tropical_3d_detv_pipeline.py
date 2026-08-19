from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .apng_writer import inspect_apng, write_apng
from .real_pipeline import generate_real_spatial_ifc_package
from .tool_discovery import discover_tools


VIEWS = (
    ("exterior_front", "phoenix_exterior_front.png", "Tropische villa's A-E · voorzijde"),
    ("exterior_rear", "phoenix_exterior_rear.png", "Tropische villa's A-E · achterzijde"),
    ("bird_view", "phoenix_bird_view.png", "Tropische villa's A-E · vogelvlucht"),
    ("interior_cutaway", "phoenix_interior_cutaway.png", "Tropische villa's A-E · interieur cutaway"),
)


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _run_blender_variant(
    executable: str,
    layout_json: Path,
    output_dir: Path,
    quick: bool,
) -> Dict[str, Any]:
    script = Path(__file__).with_name("blender_tropical_scene_script.py")
    args = [
        executable,
        "--background",
        "--python",
        str(script),
        "--",
        "--layout",
        str(layout_json),
        "--output-dir",
        str(output_dir),
    ]
    if quick:
        args.append("--quick")

    cp = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=360 if quick else 900,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"Blender tropical render failed ({cp.returncode}): {cp.stdout[-8000:]}")

    renders = {}
    for view, _, _ in VIEWS:
        p = output_dir / f"{view}.png"
        if not p.is_file() or p.stat().st_size < 1000:
            raise RuntimeError(f"Missing/invalid Blender render: {p}")
        renders[view] = str(p)

    blends = sorted(output_dir.glob("variant_*.blend"))
    if len(blends) != 1 or blends[0].stat().st_size < 1000:
        raise RuntimeError(f"Expected exactly one valid blend file in {output_dir}")

    cycles_cpu = (
        "PHOENIX_BLENDER_RENDER_ENGINE CYCLES" in cp.stdout
        and "PHOENIX_BLENDER_RENDER_DEVICE CPU" in cp.stdout
    )
    if not cycles_cpu:
        raise RuntimeError(
            "Blender completed without proving Cycles CPU headless rendering: "
            f"{cp.stdout[-5000:]}"
        )

    return {
        "status": "PASS",
        "output_dir": str(output_dir),
        "blend": str(blends[0]),
        "blend_bytes": blends[0].stat().st_size,
        "renders": renders,
        "render_engine": "CYCLES",
        "render_device": "CPU",
        "cycles_cpu_proven": True,
        "log_tail": cp.stdout[-2500:],
    }


def generate_tropical_real_3d_detv_package(
    project: Dict[str, Any],
    runtime_root: Path,
    quick: bool = False,
) -> Dict[str, Any]:
    runtime_root = Path(runtime_root)
    project_id = str(project["project_id"])
    project_dir = runtime_root / project_id
    results = project_dir / "results"
    spatial_dir = results / "tropical_residential_real_spatial_ifc_v1_0"
    media_root = results / "generated_visual_media"
    variants_media = media_root / "tropical_residential_variants"
    detv_dir = media_root / "blender_presentation"

    tools = discover_tools()
    if not tools["freecad"]["found"]:
        raise RuntimeError("FreeCAD was not found; this build requires the proven FreeCAD handoff.")
    if not tools["blender"]["found"]:
        raise RuntimeError("Blender was not found; this build requires real Blender rendering.")

    spatial_summary = generate_real_spatial_ifc_package(
        project,
        spatial_dir,
        run_freecad_if_available=True,
        run_blender_if_available=False,
    )
    if spatial_summary["freecad_handoff"].get("status") != "PASS":
        raise RuntimeError("FreeCAD handoff did not pass.")
    if not spatial_summary["freecad_handoff"].get("script_completion_marker"):
        raise RuntimeError("FreeCAD handoff completion marker was not proven.")

    variant_results: Dict[str, Any] = {}
    for vid in "ABCDE":
        layout_json = spatial_dir / "variants" / f"variant_{vid}" / "real_spatial_layout.json"
        if not layout_json.is_file():
            raise RuntimeError(f"Missing real spatial layout for variant {vid}: {layout_json}")
        variant_results[vid] = _run_blender_variant(
            str(tools["blender"]["executable"]),
            layout_json,
            variants_media / f"variant_{vid}",
            quick,
        )

    detv_dir.mkdir(parents=True, exist_ok=True)
    canonical: Dict[str, Any] = {}
    for view, canonical_name, label in VIEWS:
        frames = [
            Path(variant_results[vid]["renders"][view])
            for vid in "ABCDE"
        ]
        target = detv_dir / canonical_name
        evidence = write_apng(frames, target, delay_ms=1700 if quick else 2200, loops=0)
        if not evidence["is_apng"] or evidence["frame_count"] != 5:
            raise RuntimeError(f"DE TV APNG validation failed: {target}")
        canonical[view] = {
            "file": str(target),
            "filename": canonical_name,
            "label": label,
            "animation": "APNG",
            "variants": ["A","B","C","D","E"],
            "frame_count": evidence["frame_count"],
            "bytes": evidence["bytes"],
        }

    recommended_id = str(spatial_summary["recommended_variant_id"])
    recommended_blend = Path(variant_results[recommended_id]["blend"])
    authoritative_blend = detv_dir / f"{project_id}_recommended_{recommended_id}.blend"
    shutil.copy2(recommended_blend, authoritative_blend)

    manifest = {
        "schema": "PHOENIX_TROPICAL_RESIDENTIAL_DE_TV_PRESENTATION_v1",
        "project_id": project_id,
        "recommended_variant_id": recommended_id,
        "variant_order": ["A","B","C","D","E"],
        "views": canonical,
        "variant_outputs": variant_results,
        "authoritative_ifc": spatial_summary["authoritative_ifc"],
        "authoritative_blend": str(authoritative_blend),
        "freecad_handoff": spatial_summary["freecad_handoff"],
        "blender": tools["blender"],
        "de_tv_contract": {
            "sidecar_path": f"projects/runtime/{project_id}/results/generated_visual_media/blender_presentation/",
            "canonical_files": [x[1] for x in VIEWS],
            "core_player_patch_required": False,
            "existing_single_visual_authority_preserved": True,
            "presentation_behavior": "Each of the four existing DE TV image slots is an animated PNG cycling variants A-E.",
        },
        "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
    }
    _write_json(detv_dir / "tropical_residential_presentation_manifest.json", manifest)

    summary = {
        "engine": "PROJECT_PHOENIX_TROPICAL_RESIDENTIAL_REAL_3D_DE_TV_PRESENTATION_v1_0",
        "project_id": project_id,
        "variant_count": 5,
        "view_count": 4,
        "render_count": 20,
        "recommended_variant_id": recommended_id,
        "authoritative_ifc": spatial_summary["authoritative_ifc"],
        "authoritative_blend": str(authoritative_blend),
        "freecad_status": spatial_summary["freecad_handoff"]["status"],
        "freecad_execution_mode": spatial_summary["freecad_handoff"].get("execution_mode"),
        "freecad_python_executable": spatial_summary["freecad_handoff"].get("python_executable"),
        "freecad_script_completion_marker": spatial_summary["freecad_handoff"].get("script_completion_marker", False),
        "blender_status": "PASS",
        "blender_executable": tools["blender"]["executable"],
        "blender_render_engine": "CYCLES",
        "blender_render_device": "CPU",
        "blender_cycles_cpu_proven": all(
            bool(variant_results[vid].get("cycles_cpu_proven")) for vid in "ABCDE"
        ),
        "detv_media_dir": str(detv_dir),
        "detv_canonical": canonical,
        "detv_core_player_modified": False,
        "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
    }
    _write_json(results / "tropical_residential_real_3d_detv_summary.json", summary)
    return summary
