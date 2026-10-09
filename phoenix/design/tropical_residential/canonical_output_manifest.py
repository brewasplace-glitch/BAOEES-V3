from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .structural_input_materializer import materialization_eligibility, materialize_structural_adapter_inputs

SCHEMA = "PHOENIX_R8_CANONICAL_OUTPUT_MANIFEST_V1"
HANDOFF_SCHEMA = "PHOENIX_R8_STRUCTURAL_HANDOFF_CONTRACT_V1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _variant_record(variant_id: str, bundle: Mapping[str, Any], ifc_evidence: Mapping[str, Any]) -> dict[str, Any]:
    layout_json = Path(str(bundle["layout_json"]))
    if not layout_json.is_file():
        raise RuntimeError(f"R8_LAYOUT_JSON_MISSING:{variant_id}:{layout_json}")
    svgs = []
    for item in bundle.get("svg_plans") or []:
        p = Path(str(item))
        if not p.is_file():
            raise RuntimeError(f"R8_SVG_MISSING:{variant_id}:{p}")
        svgs.append(_file_record(p))
    ifc_path = Path(str(ifc_evidence["ifc_file"]))
    if not ifc_path.is_file():
        raise RuntimeError(f"R8_IFC_MISSING:{variant_id}:{ifc_path}")
    return {
        "variant_id": variant_id,
        "layout_json": _file_record(layout_json),
        "svg_plans": svgs,
        "ifc": _file_record(ifc_path),
        "ifc_schema": ifc_evidence.get("ifc_schema"),
        "release_status": ifc_evidence.get("release_status", "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"),
    }


def build_structural_handoff_contract(*, project_id: str, recommended_variant_id: str,
                                      canonical_layout_json: Path, authoritative_ifc: Path) -> dict[str, Any]:
    return {
        "schema": HANDOFF_SCHEMA,
        "project_id": project_id,
        "recommended_variant_id": recommended_variant_id,
        "geometry_source": {
            "canonical_layout_json": _file_record(canonical_layout_json),
            "authoritative_ifc": _file_record(authoritative_ifc),
        },
        "existing_consumer": {
            "module": "phoenix.autonomy.session_adapters",
            "function": "run_structural",
            "downstream_chain": "phoenix.autonomy.structural_session_chain.run_structural_chain",
            "v8_0_runner": "runners/PROJECT_PHOENIX_architectural_to_structural_model_derivation_v8_0_0.py",
            "chain": "v8.0-v8.12",
        },
        "required_architecture_adapter_outputs": [
            "architectural_model.json",
            "detailed_elements.json",
            "structural_project_profile.json",
        ],
        "optional_architecture_adapter_outputs": [
            "structural_material_selection_register.json",
            "local_material_selection_register.json",
            "project_context.json",
        ],
        "handoff_status": "CONTRACT_BOUND_INPUTS_REQUIRED",
        "solver_execution_started": False,
        "automatic_design_value_invention": False,
        "automatic_professional_approval": False,
        "production_release": "LOCKED",
        "for_construction": "LOCKED",
        "note": (
            "R8 unifies architectural evidence and binds it to the existing structural "
            "session-adapter contract. It does not bypass required architecture adapter "
            "artifacts or start structural solver execution."
        ),
    }


def write_canonical_output_manifest(*, project: Mapping[str, Any], output_dir: Path,
                                    recommended_variant_id: str,
                                    layout_paths: Mapping[str, Mapping[str, Any]],
                                    ifc_evidence: Mapping[str, Mapping[str, Any]],
                                    authoritative_ifc: Path, tools: Mapping[str, Any],
                                    freecad_result: Mapping[str, Any],
                                    blender_result: Mapping[str, Any]) -> dict[str, Any]:
    output_dir = Path(output_dir)
    authoritative_ifc = Path(authoritative_ifc)
    if not authoritative_ifc.is_file():
        raise RuntimeError(f"R8_AUTHORITATIVE_IFC_MISSING:{authoritative_ifc}")
    ids = sorted(set(layout_paths) | set(ifc_evidence))
    if ids != ["A", "B", "C", "D", "E"]:
        raise RuntimeError(f"R8_VARIANT_SET_DENY:{ids}")
    variants = [_variant_record(vid, layout_paths[vid], ifc_evidence[vid]) for vid in ids]
    canonical_layout = Path(str(layout_paths[recommended_variant_id]["layout_json"]))
    handoff = build_structural_handoff_contract(
        project_id=str(project["project_id"]),
        recommended_variant_id=recommended_variant_id,
        canonical_layout_json=canonical_layout,
        authoritative_ifc=authoritative_ifc,
    )
    eligibility=materialization_eligibility(canonical_layout)
    if eligibility["eligible"]:
        structural_inputs=materialize_structural_adapter_inputs(
            project_id=str(project["project_id"]),
            recommended_variant_id=recommended_variant_id,
            canonical_layout_json=canonical_layout,
            authoritative_ifc=authoritative_ifc,
            output_dir=output_dir / "structural_inputs",
        )
        handoff["materialized_architecture_adapter_outputs"]=structural_inputs["architecture_adapter_outputs"]
        handoff["materialization_evidence"]=structural_inputs["evidence_path"]
        handoff["handoff_status"]=structural_inputs["status"]
        handoff["solver_execution_started"]=False
    else:
        structural_inputs={
            "schema":"PHOENIX_R8_STRUCTURAL_INPUT_MATERIALIZATION_V1",
            "status":"BLOCKED_INPUT",
            "reasons":eligibility["reasons"],
            "solver_execution_started":False,
            "production_release":"LOCKED",
            "for_construction":"LOCKED",
        }
        handoff["materialization_status"]="BLOCKED_INPUT"
        handoff["materialization_blockers"]=eligibility["reasons"]

    handoff_path = output_dir / "structural_handoff_contract.json"
    handoff_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "schema": SCHEMA,
        "project_id": str(project["project_id"]),
        "recommended_variant_id": recommended_variant_id,
        "variants": variants,
        "authoritative": {
            "layout_json": _file_record(canonical_layout),
            "ifc": _file_record(authoritative_ifc),
        },
        "external_tools": dict(tools),
        "freecad_handoff": dict(freecad_result),
        "blender_handoff": dict(blender_result),
        "structural_handoff_contract": _file_record(handoff_path),
        "structural_input_materialization": structural_inputs,
        "governance": {
            "professional_approval": "NOT_AUTOMATIC",
            "code_compliance": "NOT_AUTOMATIC",
            "production": "LOCKED",
            "for_construction": "LOCKED",
        },
        "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
    }
    manifest_path = output_dir / "canonical_output_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "structural_handoff_contract": handoff,
        "structural_handoff_contract_path": str(handoff_path),
    }
