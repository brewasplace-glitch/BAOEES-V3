"""Phoenix architectural visual-design pipeline v1.0."""
from __future__ import annotations
import json
from pathlib import Path
from phoenix.engines.adapters.blender_visual_adapter_v1_0 import render_ifc,capability_state as blender_state

VERSION="1.0.0"

def resolve_authoritative_ifc(workspace:Path)->Path:
    workspace=Path(workspace).resolve()
    arch=workspace/"results"/"session_adapters"/"architecture"
    model_path=arch/"architectural_model.json"
    if model_path.exists():
        data=json.loads(model_path.read_text(encoding="utf-8-sig"))
        raw=data.get("authoritative_ifc")
        if raw and Path(raw).exists():
            return Path(raw).resolve()
    candidates=sorted((arch/"ifc").glob("*_architectural_authoritative.ifc")) if (arch/"ifc").exists() else []
    if len(candidates)==1:return candidates[0].resolve()
    if not candidates:raise RuntimeError("AUTHORITATIVE_IFC_NOT_FOUND")
    raise RuntimeError("AUTHORITATIVE_IFC_AMBIGUOUS")

def render_project_exterior(repository:Path,workspace:Path)->dict:
    repository=Path(repository).resolve();workspace=Path(workspace).resolve()
    ifc_path=resolve_authoritative_ifc(workspace)
    state=blender_state(repository)
    if not state["available"]:
        return {"status":"SKIPPED","reason":"BLENDER_NOT_AVAILABLE","authoritative_ifc":str(ifc_path)}
    out=workspace/"results"/"generated_visual_media"/"blender_exterior"
    out.mkdir(parents=True,exist_ok=True)
    png=out/"phoenix_ifc_exterior.png"
    result=render_ifc(repository,ifc_path,png)
    manifest={
      "schema_version":"phoenix.architectural-visual-presentation/1.0",
      "pipeline_version":VERSION,
      "project_id":workspace.name,
      "authoritative_geometry":"IFC",
      "source_ifc":str(ifc_path),
      "renderer":"Blender",
      "render":str(png),
      "passed":bool(result.get("passed")),
      "presentation_only":True,
      "professional_review_required":True,
      "production_release":"LOCKED"
    }
    (out/"phoenix_ifc_exterior_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest
