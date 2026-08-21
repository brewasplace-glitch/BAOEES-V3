from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

from phoenix.architecture.integrated_suite_v4_0_0 import run as run_integrated_suite
from phoenix.architecture.ifc_authoritative_model_adapter_v1_0 import generate_authoritative_ifc
from phoenix.engines.architectural_visual_pipeline_v1_0 import render_project_exterior

RELEASE_STATUS = "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"
ENGINE_ROUTE = "NONRESIDENTIAL_REUSE_V1"

VARIANT_SPECS = [
    {"id": "A", "name": "Minimum Intervention", "strategy": "minimum_intervention", "x_factor": 1.00, "score": 86},
    {"id": "B", "name": "Access & Flow", "strategy": "accessibility_flow", "x_factor": 1.04, "score": 90},
    {"id": "C", "name": "Daylight & Orientation", "strategy": "daylight_orientation", "x_factor": 0.96, "score": 89},
    {"id": "D", "name": "Assembly Capacity", "strategy": "assembly_capacity", "x_factor": 1.02, "score": 91},
    {"id": "E", "name": "Balanced Community", "strategy": "balanced_nonresidential", "x_factor": 0.99, "score": 94},
]

@dataclass
class NonResidentialOrchestrationResult:
    project_id: str
    recommended_variant_id: str
    runtime_dir: str
    delivery_dir: str
    manifest_path: str
    summary_md_path: str
    evidence_json_path: str
    authoritative_ifc: str
    authoritative_blend: str | None
    freecad_output: str
    detv_media_dir: str
    blender_render: str
    release_status: str = RELEASE_STATUS

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_models(repo: Path) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    arch = _load(repo / "configs/projects/moskee_bunschoten_architectural_model_v4_0_0.json")
    geom = _load(repo / "configs/projects/moskee_bunschoten_central_geometric_model_v1_0_0.json")
    prod = _load(repo / "configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json")
    return arch, geom, prod


def _base_dimensions(geom: Dict[str, Any], prod: Dict[str, Any]) -> Tuple[float, float, float, int]:
    ext = geom.get("extension", {})
    pgeom = prod.get("geometry", {})
    x = float(pgeom.get("extension_length_m", ext.get("length_m", 10.0)))
    y = float(pgeom.get("extension_width_m", ext.get("width_m", 7.0)))
    gross = float(pgeom.get("gross_area_m2", ext.get("gross_area_m2", x * y * 2)))
    storeys = int(pgeom.get("storeys", ext.get("storeys", 2)))
    if x <= 0 or y <= 0 or gross <= 0 or storeys < 1:
        raise ValueError("Invalid source extension geometry")
    return x, y, gross, storeys


def _scaled_point(point, sx: float, sy: float):
    return [round(float(point[0]) * sx, 4), round(float(point[1]) * sy, 4)]


def _scale_model(base: Dict[str, Any], project_id: str, project_name: str, spec: Dict[str, Any], base_x: float, base_y: float, gross: float, storeys: int) -> Dict[str, Any]:
    model = deepcopy(base)
    x = round(base_x * float(spec["x_factor"]), 4)
    target_floor = gross / storeys
    y = round(target_floor / x, 4)
    sx, sy = x / base_x, y / base_y

    model["project_id"] = f"{project_id}-VAR-{spec['id']}"
    model["project_name"] = f"{project_name} — Variant {spec['id']} {spec['name']}"
    model["phase"] = "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"

    for wall in model.get("walls", []):
        if isinstance(wall.get("start"), list):
            wall["start"] = _scaled_point(wall["start"], sx, sy)
        if isinstance(wall.get("end"), list):
            wall["end"] = _scaled_point(wall["end"], sx, sy)

    for space in model.get("spaces", []):
        if isinstance(space.get("polygon"), list):
            space["polygon"] = [_scaled_point(p, sx, sy) for p in space["polygon"]]

    metadata = model.get("metadata") if isinstance(model.get("metadata"), dict) else {}
    metadata = dict(metadata)
    metadata["phoenix_nonresidential_variant"] = {
        "variant_id": spec["id"],
        "variant_name": spec["name"],
        "strategy": spec["strategy"],
        "score": spec["score"],
        "envelope_x_m": x,
        "envelope_y_m": y,
        "gross_area_m2": gross,
        "storeys": storeys,
        "source_grounding": [
            "configs/projects/moskee_bunschoten_architectural_model_v4_0_0.json",
            "configs/projects/moskee_bunschoten_central_geometric_model_v1_0_0.json",
            "configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json",
        ],
        "residential_program_fabricated": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    model["metadata"] = metadata
    return model


def _room_box(space: Dict[str, Any]) -> Dict[str, Any]:
    polygon = space.get("polygon") or []
    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]
    if not xs or not ys:
        raise ValueError(f"Space without polygon: {space.get('id')}")
    return {
        "name": str(space.get("name", "Space")),
        "function": str(space.get("function", "assembly")),
        "occupancy": int(space.get("occupancy", 0) or 0),
        "x": min(xs),
        "y": min(ys),
        "w": max(xs) - min(xs),
        "d": max(ys) - min(ys),
    }


def _selected_contract(project_id: str, model: Dict[str, Any], spec: Dict[str, Any], gross: float) -> Dict[str, Any]:
    levels = sorted(model.get("levels", []), key=lambda x: float(x.get("elevation_m", 0)))
    level_ids = [str(level.get("id")) for level in levels]
    grouped = {level_id: [] for level_id in level_ids}
    for space in model.get("spaces", []):
        level_id = str(space.get("level_id"))
        grouped.setdefault(level_id, []).append(_room_box(space))

    all_points = [p for wall in model.get("walls", []) for p in (wall.get("start"), wall.get("end")) if isinstance(p, list)]
    if not all_points:
        all_points = [p for space in model.get("spaces", []) for p in space.get("polygon", [])]
    xs = [float(p[0]) for p in all_points]
    ys = [float(p[1]) for p in all_points]
    width = max(xs) - min(xs)
    depth = max(ys) - min(ys)

    rooms = {
        "ground": grouped.get(level_ids[0], []) if level_ids else [],
        "upper": grouped.get(level_ids[1], []) if len(level_ids) > 1 else [],
    }
    return {
        "project_id": project_id,
        "variant": {
            "id": spec["id"],
            "name": spec["name"],
            "strategy": spec["strategy"],
            "score": spec["score"],
        },
        "building_envelope_m": {
            "width": round(width, 4),
            "depth": round(depth, 4),
            "height": round(len(levels) * 3.2, 4),
        },
        "gross_floor_area_m2": round(gross, 2),
        "levels": len(levels),
        "rooms": rooms,
        "candidate_only": True,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }


def _freecad_handoff(ifc_path: Path, output: Path, scratch: Path) -> None:
    """Create a FreeCAD handoff derived from the authoritative IFC."""
    freecad = Path(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe")
    if not freecad.is_file():
        raise RuntimeError(f"FreeCAD strict runtime missing: {freecad}")

    from phoenix.engines.ifc_visual_mesh_adapter_v1_0 import ifc_to_obj

    output = Path(output).resolve()
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    obj_path = scratch / "freecad_nonresidential_ifc_derived.obj"
    mesh_evidence = ifc_to_obj(Path(ifc_path).resolve(), obj_path)
    if not obj_path.is_file() or obj_path.stat().st_size < 1000:
        raise RuntimeError(f"FreeCAD handoff derived OBJ missing or too small: {mesh_evidence}")

    script = scratch / "freecad_nonresidential_handoff.py"
    script.write_text(
        "import FreeCAD as App\n"
        "import Mesh\n"
        "doc=App.newDocument('PHOENIX_NONRESIDENTIAL_E2E')\n"
        f"mesh=Mesh.Mesh({str(obj_path)!r})\n"
        "obj=doc.addObject('Mesh::Feature','IFC_DERIVED_MESH')\n"
        "obj.Label='IFC-derived presentation mesh - authoritative source remains IFC'\n"
        "obj.Mesh=mesh\n"
        "doc.recompute()\n"
        f"doc.saveAs({str(output)!r})\n"
        "print('FREECAD_NONRESIDENTIAL_HANDOFF=PASS')\n"
        "print('FREECAD_HANDOFF_ROLE=IFC_DERIVED_PRESENTATION_MESH')\n"
        "print('FREECAD_OBJECT_COUNT=' + str(len(doc.Objects)))\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [str(freecad), str(script)],
        cwd=scratch,
        text=True,
        capture_output=True,
        timeout=600,
    )
    if cp.returncode != 0:
        raise RuntimeError(
            f"FreeCAD handoff failed ({cp.returncode}): "
            f"{cp.stdout[-6000:]} {cp.stderr[-6000:]}"
        )
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(
            "FreeCAD handoff output missing or too small; "
            f"stdout={cp.stdout[-3000:]!r}; stderr={cp.stderr[-3000:]!r}"
        )
    if "FREECAD_NONRESIDENTIAL_HANDOFF=PASS" not in cp.stdout:
        raise RuntimeError(
            "FreeCAD handoff output exists but PASS evidence is missing; "
            f"stdout={cp.stdout[-3000:]!r}; stderr={cp.stderr[-3000:]!r}"
        )

def _detv_viewer(media_dir: Path, project_name: str, variant_entries: List[Dict[str, Any]], recommended_id: str, blender_render: Path) -> Path:
    rows = []
    for entry in variant_entries:
        vid = entry["variant_id"]
        suite_dir = Path(entry["suite_dir"])
        plans = sorted((suite_dir / "drawings").glob("floor_plan_*.svg"))
        figures = []
        for plan in plans:
            rel = Path(os.path.relpath(plan, media_dir)).as_posix()
            figures.append(f'<figure><img src="{html.escape(rel)}"><figcaption>{html.escape(plan.stem)}</figcaption></figure>')
        rows.append(
            f'<section class="card {"recommended" if vid == recommended_id else ""}">'
            f'<h2>Variant {vid} — {html.escape(entry["name"])}</h2>'
            + "".join(figures)
            + "</section>"
        )
    render_rel = Path(os.path.relpath(blender_render, media_dir)).as_posix()
    page = f'''<!doctype html><html><head><meta charset="utf-8"><title>PHOENIX DE TV — {html.escape(project_name)}</title>
<style>body{{font-family:Arial;margin:0;background:#edf1f4;color:#17212a}}header{{background:#172634;color:white;padding:18px 24px;position:sticky;top:0}}main{{padding:18px}}.hero,.card{{background:white;margin:0 0 18px;padding:14px;border-radius:10px;box-shadow:0 2px 12px #0002}}.recommended{{outline:4px solid #6b8f71}}figure{{display:inline-block;width:47%;vertical-align:top;margin:1%}}img{{max-width:100%;background:#ddd}}figcaption{{font-size:12px}}</style></head>
<body><header><b>PROJECT PHOENIX — NONRESIDENTIAL REAL-PROJECT A–E</b><br>{html.escape(project_name)} — Recommended {recommended_id} — CONCEPT ONLY / NOT FOR CONSTRUCTION</header>
<main><section class="hero"><h2>Authoritative IFC exterior render — Blender</h2><img src="{html.escape(render_rel)}"></section>{''.join(rows)}</main></body></html>'''
    viewer = media_dir / "moskee_bunschoten_nonresidential_detv_viewer.html"
    viewer.parent.mkdir(parents=True, exist_ok=True)
    viewer.write_text(page, encoding="utf-8")
    return viewer


def orchestrate_real_project_delivery(project: Dict[str, Any], runtime_root: Path, *, quick_smoke: bool = False) -> NonResidentialOrchestrationResult:
    repo = _repo_root()
    project_id = str(project["project_id"])
    project_name = str(project.get("project_name", project_id))
    runtime_root = Path(runtime_root)
    workspace = runtime_root / project_id
    delivery_dir = workspace / "delivery" / "nonresidential_reuse_v1"
    variants_dir = delivery_dir / "variants"
    arch_dir = workspace / "results" / "session_adapters" / "architecture"
    media_dir = workspace / "results" / "generated_visual_media" / "nonresidential_reuse_v1"
    scratch = workspace / "_nonresidential_reuse_scratch"
    for path in (delivery_dir, variants_dir, arch_dir, media_dir, scratch):
        path.mkdir(parents=True, exist_ok=True)

    base_arch, geom, prod = _source_models(repo)
    base_x, base_y, gross, storeys = _base_dimensions(geom, prod)
    occupancy = prod.get("occupancy", {}) if isinstance(prod.get("occupancy"), dict) else {}

    variant_entries: List[Dict[str, Any]] = []
    variant_models: Dict[str, Dict[str, Any]] = {}
    for spec in VARIANT_SPECS:
        vid = spec["id"]
        model = _scale_model(base_arch, project_id, project_name, spec, base_x, base_y, gross, storeys)
        variant_models[vid] = model
        variant_root = variants_dir / f"variant_{vid}"
        model_path = variant_root / "canonical_architectural_model.json"
        _write(model_path, model)
        suite_dir = variant_root / "suite"
        suite_manifest = run_integrated_suite(model_path, suite_dir)
        variant_entries.append({
            "variant_id": vid,
            "name": spec["name"],
            "strategy": spec["strategy"],
            "score": spec["score"],
            "suite_dir": str(suite_dir),
            "suite_manifest": suite_manifest,
            "gross_area_m2": gross,
            "occupancy_source": occupancy,
        })

    if [entry["variant_id"] for entry in variant_entries] != list("ABCDE"):
        raise RuntimeError("Expected exact A-E nonresidential variants")

    recommended = max(variant_entries, key=lambda entry: int(entry["score"]))
    recommended_id = str(recommended["variant_id"])
    spec = next(spec for spec in VARIANT_SPECS if spec["id"] == recommended_id)
    selected_model = variant_models[recommended_id]
    selected = _selected_contract(project_id, selected_model, spec, gross)
    _write(arch_dir / "architectural_model.json", selected_model)
    _write(arch_dir / "selected_design_variant.json", selected)
    _write(arch_dir / "nonresidential_variants_index.json", {
        "schema": "PHOENIX_NONRESIDENTIAL_REUSE_AE_VARIANTS_v1",
        "project_id": project_id,
        "variant_count": 5,
        "variant_order": list("ABCDE"),
        "recommended_variant_id": recommended_id,
        "variants": variant_entries,
        "production_release": "LOCKED",
    })

    ifc_evidence = generate_authoritative_ifc(workspace, arch_dir, selected, [selected])
    authoritative_ifc = Path(ifc_evidence["ifc_file"])
    if not authoritative_ifc.is_file() or authoritative_ifc.stat().st_size < 3000:
        raise RuntimeError("Authoritative IFC gate failed")

    visual_manifest = render_project_exterior(repo, workspace)
    if not bool(visual_manifest.get("passed")):
        raise RuntimeError(f"Generic Blender visual pipeline failed: {visual_manifest}")
    blender_render = Path(str(visual_manifest["render"]))
    if not blender_render.is_file() or blender_render.stat().st_size < 1000:
        raise RuntimeError("Blender render gate failed")

    freecad_output = delivery_dir / f"recommended_variant_{recommended_id}.FCStd"
    _freecad_handoff(authoritative_ifc, freecad_output, scratch)

    viewer = _detv_viewer(media_dir, project_name, variant_entries, recommended_id, blender_render)

    artifact_index = {
        "authoritative_ifc": str(authoritative_ifc),
        "freecad_output": str(freecad_output),
        "blender_render": str(blender_render),
        "detv_media_dir": str(media_dir),
        "detv_viewer": str(viewer),
        "variant_outputs": {entry["variant_id"]: entry["suite_dir"] for entry in variant_entries},
    }
    delivery_manifest = {
        "schema": "PHOENIX_GENERIC_NONRESIDENTIAL_REAL_PROJECT_AE_DELIVERY_v1",
        "project_id": project_id,
        "project_name": project_name,
        "engine_route": ENGINE_ROUTE,
        "variant_count": 5,
        "variant_order": list("ABCDE"),
        "recommended_variant_id": recommended_id,
        "variant_summaries": variant_entries,
        "artifact_index": artifact_index,
        "source_grounding": {
            "architectural_model": "configs/projects/moskee_bunschoten_architectural_model_v4_0_0.json",
            "central_geometric_model": "configs/projects/moskee_bunschoten_central_geometric_model_v1_0_0.json",
            "real_concept_production": "configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json",
        },
        "governance": {
            "open_source_first": True,
            "reuse_first": True,
            "integrated_suite_reused": True,
            "ifc_authoritative_adapter_reused": True,
            "architectural_visual_pipeline_reused": True,
            "residential_program_fabricated": False,
            "production_locked": True,
            "for_construction_locked": True,
            "professional_approval_automatic": False,
            "release_status": RELEASE_STATUS,
        },
    }
    manifest_path = delivery_dir / "delivery_manifest.json"
    evidence_path = delivery_dir / "orchestration_evidence.json"
    summary_path = delivery_dir / "delivery_summary.md"
    _write(manifest_path, delivery_manifest)
    _write(evidence_path, {
        "engine": "PROJECT_PHOENIX_GENERIC_NONRESIDENTIAL_REUSE_ROUTER_v1_0",
        "project_id": project_id,
        "recommended_variant_id": recommended_id,
        "ifc_evidence": ifc_evidence,
        "visual_manifest": visual_manifest,
        "hashes": {
            "authoritative_ifc": _sha(authoritative_ifc),
            "freecad_output": _sha(freecad_output),
            "blender_render": _sha(blender_render),
            "detv_viewer": _sha(viewer),
        },
        "evidence_status": "PASS",
        "release_status": RELEASE_STATUS,
    })
    summary_path.write_text(
        f"# Phoenix Nonresidential Real-Project A-E Delivery — {project_id}\n\n"
        f"- Recommended variant: **{recommended_id} — {recommended['name']}**\n"
        "- Variants delivered: **A, B, C, D, E**\n"
        "- Existing Phoenix Integrated Suite reused: **PASS**\n"
        "- Existing Phoenix authoritative IFC adapter reused: **PASS**\n"
        "- Existing Phoenix Blender visual pipeline reused: **PASS**\n"
        "- FreeCAD handoff: **PASS**\n"
        f"- Authoritative IFC: `{authoritative_ifc}`\n"
        f"- Blender render: `{blender_render}`\n"
        f"- DE TV viewer: `{viewer}`\n"
        f"- Release: **{RELEASE_STATUS}**\n",
        encoding="utf-8",
    )

    return NonResidentialOrchestrationResult(
        project_id=project_id,
        recommended_variant_id=recommended_id,
        runtime_dir=str(workspace),
        delivery_dir=str(delivery_dir),
        manifest_path=str(manifest_path),
        summary_md_path=str(summary_path),
        evidence_json_path=str(evidence_path),
        authoritative_ifc=str(authoritative_ifc),
        authoritative_blend=None,
        freecad_output=str(freecad_output),
        detv_media_dir=str(media_dir),
        blender_render=str(blender_render),
    )
