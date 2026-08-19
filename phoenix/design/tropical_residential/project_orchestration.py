from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

from phoenix.design.tropical_residential.engine import generate_variants, select_balanced
from phoenix.design.tropical_residential.tropical_3d_detv_pipeline import (
    generate_tropical_real_3d_detv_package,
)


RELEASE_STATUS = "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"


@dataclass
class OrchestrationResult:
    project_id: str
    recommended_variant_id: str
    runtime_dir: str
    delivery_dir: str
    manifest_path: str
    summary_md_path: str
    evidence_json_path: str
    authoritative_ifc: str
    authoritative_blend: str
    freecad_output: str
    detv_media_dir: str
    release_status: str = RELEASE_STATUS

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _require_file(path: Path, minimum_bytes: int = 1) -> str:
    if not path.is_file():
        raise RuntimeError(f"Required delivery artifact is missing: {path}")
    size = path.stat().st_size
    if size < minimum_bytes:
        raise RuntimeError(f"Delivery artifact is too small ({size} bytes): {path}")
    return str(path)


def _load_presentation_manifest(detv_media_dir: Path) -> Dict[str, Any]:
    path = detv_media_dir / "tropical_residential_presentation_manifest.json"
    if not path.is_file():
        raise RuntimeError(f"DE TV presentation manifest is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _variant_dicts(variants: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for variant in variants:
        if hasattr(variant, "to_dict"):
            out.append(variant.to_dict())
        else:
            out.append({
                "variant_id": getattr(variant, "variant_id", "?"),
                "strategy": getattr(variant, "strategy", None),
            })
    return out


def orchestrate_real_project_delivery(
    project: Dict[str, Any],
    runtime_root: Path,
    *,
    quick_smoke: bool = False,
) -> OrchestrationResult:
    runtime_root = Path(runtime_root)
    project_id = str(project["project_id"])
    project_dir = runtime_root / project_id
    delivery_dir = project_dir / "delivery" / "architectural_ae_v1_0"

    variants = generate_variants(project)
    if len(variants) != 5:
        raise RuntimeError(f"Expected exactly five A-E variants; got {len(variants)}")
    if [getattr(v, "variant_id", None) for v in variants] != list("ABCDE"):
        raise RuntimeError("Variant identity contract failed; expected A,B,C,D,E")

    recommended = select_balanced(variants)

    # The proven R6 pipeline already performs:
    # spatial layout -> authoritative IFC -> FreeCAD -> Blender -> DE TV.
    # Orchestration calls it exactly once so the same project-scoped runtime tree
    # remains authoritative and no expensive duplicate geometry/render pass occurs.
    media_summary = generate_tropical_real_3d_detv_package(
        project,
        runtime_root,
        quick=quick_smoke,
    )

    if int(media_summary.get("variant_count", 0)) != 5:
        raise RuntimeError("R6 delivery pipeline did not return five variants")
    if int(media_summary.get("render_count", 0)) != 20:
        raise RuntimeError("R6 delivery pipeline did not return twenty renders")
    if media_summary.get("freecad_status") != "PASS":
        raise RuntimeError("FreeCAD delivery evidence is not PASS")
    if media_summary.get("blender_status") != "PASS":
        raise RuntimeError("Blender delivery evidence is not PASS")
    if media_summary.get("blender_render_engine") != "CYCLES":
        raise RuntimeError("Blender delivery engine is not CYCLES")
    if media_summary.get("blender_render_device") != "CPU":
        raise RuntimeError("Blender delivery device is not CPU")
    if not bool(media_summary.get("blender_cycles_cpu_proven")):
        raise RuntimeError("Blender Cycles CPU A-E evidence is missing")
    if bool(media_summary.get("detv_core_player_modified")):
        raise RuntimeError("DE TV core player was unexpectedly modified")
    if media_summary.get("release_status") != RELEASE_STATUS:
        raise RuntimeError("Release-governance contract failed")

    pipeline_recommended = str(media_summary["recommended_variant_id"])
    if pipeline_recommended != str(recommended.variant_id):
        raise RuntimeError(
            f"Recommendation mismatch: foundation={recommended.variant_id}, "
            f"delivery={pipeline_recommended}"
        )

    authoritative_ifc = Path(media_summary["authoritative_ifc"])
    authoritative_blend = Path(media_summary["authoritative_blend"])
    detv_media_dir = Path(media_summary["detv_media_dir"])

    _require_file(authoritative_ifc, 3000)
    _require_file(authoritative_blend, 1000)

    presentation = _load_presentation_manifest(detv_media_dir)
    freecad_handoff = presentation.get("freecad_handoff", {})
    if freecad_handoff.get("status") != "PASS":
        raise RuntimeError("Presentation manifest FreeCAD handoff is not PASS")
    freecad_output = Path(str(freecad_handoff["output"]))
    _require_file(freecad_output, 1000)

    canonical = media_summary.get("detv_canonical", {})
    expected_views = {
        "exterior_front",
        "exterior_rear",
        "bird_view",
        "interior_cutaway",
    }
    if set(canonical) != expected_views:
        raise RuntimeError(
            f"DE TV canonical view contract failed: {sorted(canonical)}"
        )
    for view_name, view in canonical.items():
        path = Path(view["file"])
        _require_file(path, 2000)
        if view.get("animation") != "APNG":
            raise RuntimeError(f"{view_name} is not APNG")
        if int(view.get("frame_count", 0)) != 5:
            raise RuntimeError(f"{view_name} does not contain five A-E frames")

    variant_outputs = presentation.get("variant_outputs", {})
    if set(variant_outputs) != set("ABCDE"):
        raise RuntimeError("Presentation manifest does not contain A-E variant outputs")

    variant_summaries = _variant_dicts(variants)
    artifact_index = {
        "authoritative_ifc": str(authoritative_ifc),
        "authoritative_blend": str(authoritative_blend),
        "freecad_output": str(freecad_output),
        "detv_media_dir": str(detv_media_dir),
        "detv_canonical": canonical,
        "variant_outputs": variant_outputs,
    }

    delivery_manifest = {
        "schema": "PHOENIX_AUTONOMOUS_ARCHITECTURAL_REAL_PROJECT_AE_DELIVERY_v1",
        "project_id": project_id,
        "project_name": project.get("project_name", project_id),
        "runtime_dir": str(project_dir),
        "variant_count": 5,
        "variant_order": list("ABCDE"),
        "recommended_variant_id": str(recommended.variant_id),
        "variant_summaries": variant_summaries,
        "artifact_index": artifact_index,
        "governance": {
            "open_source_first": True,
            "production_locked": True,
            "for_construction_locked": True,
            "professional_approval_automatic": False,
            "release_status": RELEASE_STATUS,
        },
    }

    evidence = {
        "engine": "PROJECT_PHOENIX_AUTONOMOUS_ARCHITECTURAL_PROJECT_ORCHESTRATION_REAL_PROJECT_AE_DELIVERY_v1_0",
        "project_id": project_id,
        "quick_smoke": bool(quick_smoke),
        "r6_delivery_summary": media_summary,
        "presentation_manifest": presentation,
        "delivery_manifest": delivery_manifest,
        "evidence_status": "PASS",
    }

    manifest_path = delivery_dir / "delivery_manifest.json"
    evidence_path = delivery_dir / "orchestration_evidence.json"
    summary_path = delivery_dir / "delivery_summary.md"

    _write_json(manifest_path, delivery_manifest)
    _write_json(evidence_path, evidence)

    summary_lines = [
        f"# Phoenix A-E Delivery Summary — {project_id}",
        "",
        f"- Recommended variant: **{recommended.variant_id}**",
        "- Variants delivered: **A, B, C, D, E**",
        "- Blender renders: **20**",
        "- Blender engine/device: **Cycles / CPU**",
        "- FreeCAD: **PASS**",
        "- DE TV canonical presentations: **4 × APNG, each 5 A-E frames**",
        f"- Authoritative IFC: `{authoritative_ifc}`",
        f"- Authoritative Blend: `{authoritative_blend}`",
        f"- FreeCAD output: `{freecad_output}`",
        f"- DE TV media: `{detv_media_dir}`",
        f"- Release: **{RELEASE_STATUS}**",
        "",
        "Production and for-construction release remain locked.",
    ]
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return OrchestrationResult(
        project_id=project_id,
        recommended_variant_id=str(recommended.variant_id),
        runtime_dir=str(project_dir),
        delivery_dir=str(delivery_dir),
        manifest_path=str(manifest_path),
        summary_md_path=str(summary_path),
        evidence_json_path=str(evidence_path),
        authoritative_ifc=str(authoritative_ifc),
        authoritative_blend=str(authoritative_blend),
        freecad_output=str(freecad_output),
        detv_media_dir=str(detv_media_dir),
    )
