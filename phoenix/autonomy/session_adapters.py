"""Phoenix Generic Session Adapter Masterpack v1.0.

Seven adapters consume the same project session/workspace contract.
They never fabricate professional approval and never invoke project-specific pilot runners.
"""
from __future__ import annotations
from phoenix.architecture.real_multivariant_design_engine_v1_0 import run_multivariant_design_from_scope as _phoenix_real_multivariant_design
from phoenix.autonomy.material_certification_engineering_mode import (
    cost_certification_block_should_apply as _phoenix_material_mode_cost_gate,
)
from phoenix.autonomy.material_certification_engineering_mode import split_cost_blockers_for_continuation as _phoenix_split_cost_blockers, continue_cost_calculation_with_unresolved_prices as _phoenix_continue_cost_calculation

import json
import re
import shutil
from pathlib import Path
from typing import Any, Callable

from .adapter_runtime import (
    adapter_state,
    discover_json_uploads,
    discover_upload_files,
    finish,
    load_session_context,
    repo_ref,
    resolve_ref,
    read_json,
    run_subprocess,
    python_command,
    write_json,
)
from .architectural_bootstrap import generate_architectural_bootstrap
from .nonresidential_session_architecture_bridge_v1_0 import resolve_nonresidential_session_architecture
from .project_context import generate_project_context
from .selected_project_context_bridge_v1_0 import resolve_selected_project_context, merge_selected_project_facts
from .cost_estimate_artifact_bridge_v1_0 import emit_level_a_cost_estimate_artifact
from .local_cost_intelligence import build_local_cost_market_context, calculate_cost_items
from .structural_profile import generate_structural_project_profile
from .drawing_production import produce_architectural_drawings
from .location_intelligence import resolve_location_intelligence
from .structural_session_chain import run_structural_chain
from .local_material_supply_intelligence import build_local_material_supply_context
from .real_world_data_acquisition import acquire_real_world_data
from .site_parcel_intelligence import analyze_site_drawings
from .level_a_project_zip_artifact_bridge_v1_0 import emit_level_a_project_zip_artifact
from .nl_pdok_site_acquisition_v1_0 import acquire_nl_pdok_site_evidence
from .local_product_qualification import prepare_local_product_qualification_overlay
from .global_material_sourcing import build_global_material_sourcing_context
from .suriname_structural_load_basis import ensure_suriname_structural_load_basis



CAPABILITIES = {
    "architecture": "Architectural Session Adapter",
    "digital_twin": "Digital Twin Session Adapter",
    "structural_engineering": "Structural v8.0–v8.12 Session Adapter",
    "permit": "Permit / BOPA / AERIUS Session Adapter",
    "cost_planning": "Cost & Planning Session Adapter",
    "reporting": "Reporting Session Adapter",
    "closure": "QA/QC / Review / Release Session Adapter",
}


def _architecture_model_candidate(value: dict[str, Any]) -> bool:
    if isinstance(value.get("storeys"), list):
        return True
    model = value.get("architectural_model")
    return isinstance(model, dict) and isinstance(model.get("storeys"), list)


def _detailed_elements_candidate(value: dict[str, Any]) -> bool:
    if isinstance(value.get("storeys"), list):
        for storey in value["storeys"]:
            if isinstance(storey, dict) and (
                isinstance(storey.get("walls"), list)
                or isinstance(storey.get("doors"), list)
                or isinstance(storey.get("windows"), list)
            ):
                return True
    return isinstance(value.get("detailed_elements"), dict)


def _structural_profile_candidate(value: dict[str, Any]) -> bool:
    assumptions = value.get("assumptions")
    if not isinstance(assumptions, dict):
        return False
    required = {
        "minimum_loadbearing_wall_thickness_m",
        "default_wall_material",
        "column_grid_target_m",
        "default_column_material",
        "default_slab_material",
        "maximum_preferred_slab_span_m",
        "default_beam_material",
        "default_roof_material",
    }
    return required.issubset(assumptions)


def _update_project_manifest(ctx: dict[str, Any], updates: dict[str, Any]) -> None:
    manifest=dict(ctx.get("manifest") or {})
    manifest.update(updates)
    manifest["updated_by"]="project_context_structural_profile_drawing_masterpack_v1.0"
    write_json(ctx["manifest_path"],manifest)
    ctx["manifest"]=manifest


def _load_project_context_from_arch_state(ctx: dict[str, Any], arch_outputs: list[str]) -> dict[str, Any] | None:
    ref=next((x for x in arch_outputs if x.endswith("/project_context.json")),None)
    if not ref:
        ref=(ctx.get("manifest") or {}).get("project_context")
    path=resolve_ref(ref,ctx["repository"]) if ref else None
    if path and path.is_file():
        try:return read_json(path)
        except Exception:return None
    return None


def run_architecture(ctx: dict[str, Any]) -> int:
    cap = "architecture"
    label = CAPABILITIES[cap]
    out = ctx["output_dir"]
    uploads = discover_upload_files(ctx)
    json_uploads = discover_json_uploads(ctx)

    intake = {
        "schema_version": "phoenix.architectural-session-intake/1.2",
        "project_id": ctx["project_id"],
        "session_id": ctx["session"].get("session_id"),
        "project_type": ctx["session"].get("project_type"),
        "brief": ctx["session"].get("brief"),
        "desired_outputs": ctx["session"].get("desired_outputs", []),
        "upload_files": [repo_ref(p, ctx["repository"]) for p in uploads],
        "autonomous_text_bootstrap_allowed": str(ctx["session"].get("project_mode") or "").lower() == "autonomous",
        "professional_release": "LOCKED",
    }
    intake_path = out / "architectural_session_intake.json"
    write_json(intake_path, intake)

    model_source = None
    model_value = None
    detail_source = None
    detail_value = None
    profile_source = None
    profile_value = None
    generated = None

    for path, value in json_uploads:
        if model_source is None and _architecture_model_candidate(value):
            model_source, model_value = path, value.get("architectural_model", value)
        if detail_source is None and _detailed_elements_candidate(value):
            detail_source, detail_value = path, value.get("detailed_elements", value)
        if profile_source is None and _structural_profile_candidate(value):
            profile_source, profile_value = path, value

    route_bridge = None
    if model_source is None:
        route_bridge = resolve_nonresidential_session_architecture(ctx)
        if route_bridge.get("matched"):
            if route_bridge.get("status") != "PASSED":
                bridge_outputs = [repo_ref(intake_path, ctx["repository"])]
                evidence_path = route_bridge.get("evidence_path")
                if evidence_path:
                    bridge_outputs.append(repo_ref(evidence_path, ctx["repository"]))
                return finish(
                    ctx,
                    capability_id=cap,
                    label=label,
                    status="BLOCKED_INPUT",
                    outputs=bridge_outputs,
                    blockers=[{
                        "reason": route_bridge.get("reason") or "NONRESIDENTIAL_ARCHITECTURE_ROUTE_BLOCKED",
                        "message": route_bridge.get("message") or "Nonresidential project route kon geen veilig projectgebonden architectuurmodel leveren.",
                        "route": route_bridge.get("route") or "NONRESIDENTIAL_REUSE_V1",
                    }],
                )
            model_source = route_bridge["model_source_path"]
            model_value = route_bridge["model"]
            detail_source = route_bridge["detail_source_path"]
            detail_value = route_bridge["detailed_elements"]
    if model_source is None and str(ctx["session"].get("project_mode") or "").lower() == "autonomous":
        generated = generate_architectural_bootstrap(
            project_id=ctx["project_id"],
            project_type=str(ctx["session"].get("project_type") or ""),
            brief=str(ctx["session"].get("brief") or ""),
            desired_outputs=list(ctx["session"].get("desired_outputs", [])),
        )
        if generated.status == "PASSED":
            model_value = generated.model
            detail_value = generated.detailed_elements

    if model_value is None:
        geometry_formats = sorted(
            {p.suffix.lower() for p in uploads if p.suffix.lower() in {".ifc",".dwg",".dxf",".rvt",".skp"}}
        )
        reason = generated.reason if generated is not None and generated.reason else "DIMENSIONED_ARCHITECTURAL_MODEL_REQUIRED"
        blockers = [{
            "reason": reason,
            "message": (
                "Autonome architectuurbootstrap kon uit deze projectomschrijving geen veilig conceptmodel maken. "
                "Voeg gebruikstype/hoofdmaten toe of lever een gestructureerd/CAD-BIM model aan."
            ),
            "accepted_now": ["duidelijke BOUW-projectomschrijving voor woning", "JSON/GeoJSON met storeys/spaces"],
            "detected_unparsed_geometry_formats": geometry_formats,
        }]
        if geometry_formats:
            blockers.append({
                "reason": "CAD_BIM_IMPORT_ADAPTER_REQUIRED",
                "message": "CAD/BIM-bron is aanwezig, maar moet eerst naar het generieke architectuurmodel worden vertaald.",
            })
        # PHOENIX_REAL_ARCHITECTURAL_MULTI_VARIANT_DESIGN_ENGINE_v1_0
        try:
            _phoenix_real_multivariant_design(locals(), __file__)
        except Exception as _phoenix_design_exc:
            raise RuntimeError(f'REAL_ARCHITECTURAL_MULTI_VARIANT_DESIGN_FAILED: {_phoenix_design_exc}') from _phoenix_design_exc
        return finish(
            ctx, capability_id=cap, label=label, status="BLOCKED_INPUT",
            outputs=[repo_ref(intake_path, ctx["repository"])],
            blockers=blockers,
            metadata={"upload_count": len(uploads), "autonomous_bootstrap_attempted": generated is not None},
        )

    model_path = out / "architectural_model.json"
    write_json(model_path, model_value)
    outputs = [repo_ref(intake_path, ctx["repository"]), repo_ref(model_path, ctx["repository"])]

    metadata = {
        "architectural_model_source": "AUTONOMOUS_TEXT_BOOTSTRAP" if generated is not None else repo_ref(model_source, ctx["repository"]),
        "generation_mode": "AUTONOMOUS_TEXT_CONCEPT" if generated is not None else "PROJECT_INPUT",
        "candidate_only": True,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }

    if detail_value is not None:
        detail_path = out / "detailed_elements.json"
        write_json(detail_path, detail_value)
        outputs.append(repo_ref(detail_path, ctx["repository"]))
        metadata["detailed_elements"] = repo_ref(detail_path, ctx["repository"])

    if generated is not None:
        program_path=out/"architectural_space_program.json"
        assumptions_path=out/"architectural_assumptions_register.json"
        handoff_path=out/"architectural_structural_handoff.json"
        write_json(program_path,generated.program)
        write_json(assumptions_path,generated.assumptions)
        write_json(handoff_path,generated.structural_handoff)
        outputs.extend([
            repo_ref(program_path,ctx["repository"]),
            repo_ref(assumptions_path,ctx["repository"]),
            repo_ref(handoff_path,ctx["repository"]),
        ])
        metadata["assumptions_register"] = repo_ref(assumptions_path,ctx["repository"])
        metadata["space_program"] = repo_ref(program_path,ctx["repository"])
        metadata["structural_handoff"] = repo_ref(handoff_path,ctx["repository"])
        metadata["desired_output_states"] = dict(generated.desired_output_states)
        metadata["autonomous_architectural_bootstrap_version"] = "1.0.0"
    else:
        metadata["desired_output_states"] = {}

    # Central project context: facts remain separate from design assumptions.
    context_result=generate_project_context(
        project_id=ctx["project_id"],
        brief=str(ctx["session"].get("brief") or ""),
        architectural_model=model_value,
    )
    selected_project_context=resolve_selected_project_context(ctx)
    if selected_project_context.get("status") == "PASSED":
        merge_selected_project_facts(context_result.context, selected_project_context)
    location_result=resolve_location_intelligence(
        repository=ctx["repository"],
        project_id=ctx["project_id"],
        brief=str(ctx["session"].get("brief") or ""),
        manifest=ctx.get("manifest") or {},
        project_context=context_result.context,
    )
    context_result.context.setdefault("facts",{}).update(location_result.fact_updates)

    # Acquire explicitly configured / uploaded real-world evidence before
    # material, cost and structural downstream adapters consume it.
    acquisition_result=acquire_real_world_data(
        repository=ctx["repository"],
        project_id=ctx["project_id"],
        project_context=context_result.context,
        manifest=ctx.get("manifest") or {},
        upload_paths=uploads,
    )
    acquisition_path=out/"real_world_data_acquisition_register.json"
    write_json(acquisition_path,acquisition_result.register)

    # Extract site/parcel facts from uploaded machine-readable site drawings.
    site_result=analyze_site_drawings(
        project_id=ctx["project_id"],
        upload_paths=uploads,
        base_site_context=context_result.site_context,
        brief=str(ctx["session"].get("brief") or ""),
        repository=ctx["repository"],
    )
    # Netherlands open-data extension: when uploads did not provide real site geometry,
    # attempt PDOK address -> BRK parcel evidence. This is Level-A candidate evidence
    # only; legal/cadastral validation remains false.
    pdok_result=acquire_nl_pdok_site_evidence(
        project_id=ctx["project_id"],
        project_context=context_result.context,
        base_site_context=site_result.site_context,
        existing_evidence_register=site_result.evidence_register,
        output_dir=out,
    )
    if pdok_result.applied:
        site_result.status=pdok_result.status
        site_result.site_context=pdok_result.site_context
        site_result.evidence_register=pdok_result.evidence_register
        site_result.warnings.extend(pdok_result.warnings)
        for pdok_path in pdok_result.output_files:
            outputs.append(repo_ref(pdok_path,ctx["repository"]))
    elif pdok_result.warnings:
        site_result.warnings.extend(pdok_result.warnings)
    context_result.site_context=site_result.site_context
    site_evidence_path=out/"site_parcel_evidence_register.json"
    write_json(site_evidence_path,site_result.evidence_register)
    context_result.context["site_context_status"]=context_result.site_context.get("status")

    location_path=out/"location_intelligence.json"
    write_json(location_path,location_result.record)
    context_path=out/"project_context.json"
    context_assumptions_path=out/"project_context_assumptions.json"
    site_context_path=out/"site_context.json"
    context_result.site_context["location_intelligence"]=repo_ref(location_path,ctx["repository"])
    write_json(context_path,context_result.context)
    write_json(context_assumptions_path,context_result.assumptions)
    write_json(site_context_path,context_result.site_context)
    outputs.extend([
        repo_ref(context_path,ctx["repository"]),
        repo_ref(context_assumptions_path,ctx["repository"]),
        repo_ref(site_context_path,ctx["repository"]),
        repo_ref(location_path,ctx["repository"]),
        repo_ref(acquisition_path,ctx["repository"]),
        repo_ref(site_evidence_path,ctx["repository"]),
    ])
    metadata["project_context"]=repo_ref(context_path,ctx["repository"])
    metadata["site_context"]=repo_ref(site_context_path,ctx["repository"])
    metadata["project_context_version"]="1.1.0"
    metadata["location_intelligence"]=repo_ref(location_path,ctx["repository"])
    metadata["location_intelligence_status"]=location_result.status
    metadata["real_world_data_acquisition"]=repo_ref(acquisition_path,ctx["repository"])
    metadata["real_world_acquired_count"]=acquisition_result.register.get("acquired_count",0)
    metadata["site_parcel_evidence"]=repo_ref(site_evidence_path,ctx["repository"])
    metadata["site_parcel_intelligence_status"]=site_result.status

    manifest_updates=dict(context_result.manifest_updates)
    manifest_updates.update(location_result.manifest_updates)
    manifest_updates.update({
        "project_context":repo_ref(context_path,ctx["repository"]),
        "site_context":repo_ref(site_context_path,ctx["repository"]),
        "real_world_data_acquisition":repo_ref(acquisition_path,ctx["repository"]),
        "site_parcel_evidence":repo_ref(site_evidence_path,ctx["repository"]),
    })
    _update_project_manifest(ctx,manifest_updates)

    # A concept structural profile is now generated from candidate geometry.
    # It contains no code basis, loads, soil facts, member sizes or approval.
    if profile_value is None:
        profile_value=generate_structural_project_profile(
            project_id=ctx["project_id"],
            architectural_model=model_value,
            project_context=context_result.context,
        )
        profile_source="AUTONOMOUS_CONCEPT_PROFILE"
    profile_path = out / "structural_project_profile.json"
    write_json(profile_path, profile_value)
    outputs.append(repo_ref(profile_path, ctx["repository"]))
    metadata["structural_project_profile"] = repo_ref(profile_path, ctx["repository"])
    metadata["structural_profile_source"] = (
        profile_source if isinstance(profile_source,str)
        else repo_ref(profile_source,ctx["repository"])
    )
    metadata["structural_profile_version"]="1.1.0"

    # Local Product Qualification Overlay. This normalizes only explicit supplier
    # evidence already acquired for this project; it does not invent stock, product
    # class or technical properties. The overlay is written before the material
    # supply engine discovers project-runtime catalogs.
    qualification=prepare_local_product_qualification_overlay(
        ctx,
        project_context=context_result.context,
    )
    qualification_register_ref=qualification.get("register")
    qualification_overlay_ref=qualification.get("overlay")
    if qualification_register_ref:
        outputs.append(str(qualification_register_ref))
    metadata["local_product_qualification_register"]=qualification_register_ref
    metadata["local_product_qualification_overlay"]=qualification_overlay_ref
    metadata["local_product_qualification_version"]="1.0.0"

    # Local Material / Product / Supply Intelligence.
    # Concept geometry may continue when availability is unresolved, but final/release
    # gates and structural material use may not treat unconfirmed products as final.
    material_result=build_local_material_supply_context(
        repository=ctx["repository"],
        project_id=ctx["project_id"],
        architectural_model=model_value,
        structural_profile=profile_value,
        project_context=context_result.context,
        manifest=ctx.get("manifest") or {},
    )
    material_requirements_path=out/"local_material_requirements.json"
    material_selection_path=out/"local_material_selection_register.json"
    material_supply_sources_path=out/"local_material_supply_source_register.json"
    material_change_control_path=out/"material_product_change_control.json"
    write_json(material_requirements_path,material_result.requirements)
    write_json(material_selection_path,material_result.selection_register)
    write_json(material_supply_sources_path,material_result.supply_register)
    write_json(material_change_control_path,material_result.change_control)
    outputs.extend([
        repo_ref(material_requirements_path,ctx["repository"]),
        repo_ref(material_selection_path,ctx["repository"]),
        repo_ref(material_supply_sources_path,ctx["repository"]),
        repo_ref(material_change_control_path,ctx["repository"]),
    ])
    metadata["local_material_supply_intelligence_version"]="1.0.0"
    metadata["local_material_selection_register"]=repo_ref(material_selection_path,ctx["repository"])
    metadata["local_material_supply_gate"]=material_result.status
    metadata["all_structural_materials_locally_confirmed"]=material_result.selection_register.get(
        "all_structural_requirements_locally_confirmed",False
    )
    metadata["all_structural_materials_engineering_qualified"]=material_result.selection_register.get(
        "all_structural_requirements_engineering_qualified",False
    )

    # Global fallback sourcing: local first, then only explicit certified supplier
    # evidence with complete landed-cost evidence to the project destination.
    global_material_result=build_global_material_sourcing_context(
        repository=ctx["repository"], workspace=ctx["workspace"], project_id=ctx["project_id"],
        project_context=context_result.context,
        local_selection_register=material_result.selection_register,
        manifest=ctx.get("manifest") or {},
    )
    global_sourcing_path=out/"global_material_sourcing_register.json"
    global_comparison_path=out/"global_material_candidate_comparison.json"
    landed_cost_path=out/"landed_cost_register.json"
    structural_material_path=out/"structural_material_selection_register.json"
    write_json(global_sourcing_path,global_material_result.sourcing_register)
    write_json(global_comparison_path,global_material_result.candidate_comparison)
    write_json(landed_cost_path,global_material_result.landed_cost_register)
    write_json(structural_material_path,global_material_result.structural_selection_register)
    outputs.extend([
        repo_ref(global_sourcing_path,ctx["repository"]),
        repo_ref(global_comparison_path,ctx["repository"]),
        repo_ref(landed_cost_path,ctx["repository"]),
        repo_ref(structural_material_path,ctx["repository"]),
    ])
    metadata["global_material_sourcing_version"]="1.0.0"
    metadata["global_material_sourcing_register"]=repo_ref(global_sourcing_path,ctx["repository"])
    metadata["landed_cost_register"]=repo_ref(landed_cost_path,ctx["repository"])
    metadata["structural_material_selection_register"]=repo_ref(structural_material_path,ctx["repository"])
    metadata["material_supply_gate"]=global_material_result.status
    metadata["all_material_requirements_supply_confirmed"]=global_material_result.structural_selection_register.get(
        "all_requirements_supply_confirmed",False
    )
    metadata["all_structural_materials_engineering_qualified"]=global_material_result.structural_selection_register.get(
        "all_structural_requirements_engineering_qualified",False
    )

    profile_value.setdefault("local_material_policy",{}).update({
        "status":material_result.status,
        "selection_register":repo_ref(material_selection_path,ctx["repository"]),
        "all_structural_requirements_locally_confirmed":material_result.selection_register.get(
            "all_structural_requirements_locally_confirmed",False
        ),
        "all_structural_requirements_engineering_qualified":material_result.selection_register.get(
            "all_structural_requirements_engineering_qualified",False
        ),
        "automatic_product_substitution":False,
        "material_substitution_requires_recalculation":True,
    })
    write_json(profile_path,profile_value)

    # Produce real drawing artifacts from geometry. They are CONCEPT / TER CONTROLE.
    drawings_dir=out/"drawings"
    drawing_result=produce_architectural_drawings(
        project_id=ctx["project_id"],
        architectural_model=model_value,
        site_context=context_result.site_context,
        output_dir=drawings_dir,
        requested_outputs=list(ctx["session"].get("desired_outputs",[])),
    )
    drawing_register_path=out/"architectural_drawing_register.json"
    drawing_register=dict(drawing_result["register"])
    drawing_register["files"]=[
        {
            **item,
            "path": repo_ref((drawings_dir/item["name"]),ctx["repository"])
        }
        for item in drawing_register.get("files",[])
    ]
    write_json(drawing_register_path,drawing_register)
    outputs.append(repo_ref(drawing_register_path,ctx["repository"]))
    for file_path in drawing_result["files"]:
        outputs.append(repo_ref(file_path,ctx["repository"]))
    metadata["drawing_register"]=repo_ref(drawing_register_path,ctx["repository"])
    metadata["drawing_production_version"]="1.0.0"
    metadata["desired_output_states"].update(drawing_result["coverage"])

    contract = {
        "schema_version": "phoenix.architectural-adapter-contract/1.2",
        "project_id": ctx["project_id"],
        "architectural_model": repo_ref(model_path, ctx["repository"]),
        "detailed_elements": metadata.get("detailed_elements"),
        "structural_project_profile": metadata.get("structural_project_profile"),
        "local_material_selection_register": metadata.get("local_material_selection_register"),
        "structural_material_selection_register": metadata.get("structural_material_selection_register"),
        "global_material_sourcing_register": metadata.get("global_material_sourcing_register"),
        "landed_cost_register": metadata.get("landed_cost_register"),
        "local_material_supply_gate": metadata.get("local_material_supply_gate"),
        "material_supply_gate": metadata.get("material_supply_gate"),
        "project_context":metadata.get("project_context"),
        "site_context":metadata.get("site_context"),
        "drawing_register":metadata.get("drawing_register"),
        "real_world_data_acquisition":metadata.get("real_world_data_acquisition"),
        "site_parcel_evidence":metadata.get("site_parcel_evidence"),
        "generation_mode": metadata["generation_mode"],
        "assumptions_register": metadata.get("assumptions_register"),
        "approval_state": "CANDIDATE_ONLY",
        "production_release": "LOCKED",
    }
    contract_path = out / "architectural_adapter_contract.json"
    write_json(contract_path, contract)
    outputs.append(repo_ref(contract_path, ctx["repository"]))

    warnings=[
        "Architectural model and drawings are concept candidates and require professional/project review before final use.",
        "Structural project profile contains explicit concept hypotheses only; code basis, loads and geotechnical facts remain unresolved.",
    ]
    if context_result.site_context.get("status")=="SCHEMATIC_ASSUMPTION":
        warnings.append("Site plan is schematic only because real plot/location facts were not supplied.")

    # PHOENIX_REAL_ARCHITECTURAL_MULTI_VARIANT_DESIGN_ENGINE_v1_0
    try:
        _phoenix_real_multivariant_design(locals(), __file__)
    except Exception as _phoenix_design_exc:
        raise RuntimeError(f'REAL_ARCHITECTURAL_MULTI_VARIANT_DESIGN_FAILED: {_phoenix_design_exc}') from _phoenix_design_exc
    return finish(
        ctx, capability_id=cap, label=label, status="PASSED",
        outputs=outputs,
        warnings=warnings,
        metadata=metadata,
    )

def run_digital_twin(ctx: dict[str, Any]) -> int:
    cap = "digital_twin"
    label = CAPABILITIES[cap]
    state = adapter_state(ctx["workspace"])
    arch = (state.get("capabilities") or {}).get("architecture") or {}
    arch_outputs = arch.get("outputs") or []

    model_ref = next((x for x in arch_outputs if x.endswith("/architectural_model.json")), None)
    if not model_ref:
        return finish(
            ctx, capability_id=cap, label=label, status="BLOCKED_DEPENDENCY",
            blockers=[{
                "reason": "ARCHITECTURAL_MODEL_NOT_AVAILABLE",
                "message": "Digitale Tweeling wacht op een gestructureerd architectuurmodel.",
            }],
        )
    context_ref=next((x for x in arch_outputs if x.endswith("/project_context.json")),None)
    site_ref=next((x for x in arch_outputs if x.endswith("/site_context.json")),None)
    profile_ref=next((x for x in arch_outputs if x.endswith("/structural_project_profile.json")),None)
    drawing_register_ref=next((x for x in arch_outputs if x.endswith("/architectural_drawing_register.json")),None)
    location_intelligence_ref=next((x for x in arch_outputs if x.endswith("/location_intelligence.json")),None)
    local_material_selection_ref=next((x for x in arch_outputs if x.endswith("/local_material_selection_register.json")),None)
    structural_material_selection_ref=next((x for x in arch_outputs if x.endswith("/structural_material_selection_register.json")),None)
    global_material_sourcing_ref=next((x for x in arch_outputs if x.endswith("/global_material_sourcing_register.json")),None)
    landed_cost_ref=next((x for x in arch_outputs if x.endswith("/landed_cost_register.json")),None)
    real_world_acquisition_ref=next((x for x in arch_outputs if x.endswith("/real_world_data_acquisition_register.json")),None)
    site_parcel_evidence_ref=next((x for x in arch_outputs if x.endswith("/site_parcel_evidence_register.json")),None)

    twin = {
        "schema_version": "phoenix.central-project-digital-twin/1.1",
        "project_id": ctx["project_id"],
        "session_id": ctx["session"].get("session_id"),
        "architectural_model": model_ref,
        "project_context":context_ref,
        "site_context":site_ref,
        "structural_project_profile":profile_ref,
        "architectural_drawing_register":drawing_register_ref,
        "location_intelligence":location_intelligence_ref,
        "local_material_selection_register":local_material_selection_ref,
        "structural_material_selection_register":structural_material_selection_ref,
        "global_material_sourcing_register":global_material_sourcing_ref,
        "landed_cost_register":landed_cost_ref,
        "real_world_data_acquisition":real_world_acquisition_ref,
        "site_parcel_evidence":site_parcel_evidence_ref,
        "structural_model": None,
        "permit_state": None,
        "cost_planning_state": None,
        "traceability": {
            "project_manifest": repo_ref(ctx["manifest_path"], ctx["repository"]),
            "session_file": repo_ref(ctx["session_file"], ctx["repository"]),
        },
        "approval_state": "CANDIDATE_ONLY",
        "production_release": "LOCKED",
    }
    path = ctx["output_dir"] / "central_project_digital_twin.json"
    write_json(path, twin)

    project_twin = ctx["workspace"] / "digital_twin" / "central_project_digital_twin.json"
    write_json(project_twin, twin)

    return finish(
        ctx, capability_id=cap, label=label, status="PASSED",
        outputs=[repo_ref(path, ctx["repository"]), repo_ref(project_twin, ctx["repository"])],
        warnings=["Digitale Tweeling bevat kandidaatcontext/geometrie; professionele vrijgave blijft geblokkeerd."],
        metadata={
            "project_context":context_ref,
            "site_context":site_ref,
            "structural_project_profile":profile_ref,
            "drawing_register":drawing_register_ref,
        },
    )

def run_structural(ctx: dict[str, Any]) -> int:
    cap="structural_engineering"
    label=CAPABILITIES[cap]
    state=adapter_state(ctx["workspace"])
    arch=(state.get("capabilities") or {}).get("architecture") or {}
    arch_outputs=arch.get("outputs") or []

    model_ref=next((x for x in arch_outputs if x.endswith("/architectural_model.json")),None)
    detail_ref=next((x for x in arch_outputs if x.endswith("/detailed_elements.json")),None)
    profile_ref=next((x for x in arch_outputs if x.endswith("/structural_project_profile.json")),None)
    material_selection_ref=(
        next((x for x in arch_outputs if x.endswith("/structural_material_selection_register.json")),None)
        or next((x for x in arch_outputs if x.endswith("/local_material_selection_register.json")),None)
    )
    project_context_ref=next((x for x in arch_outputs if x.endswith("/project_context.json")),None)

    # PHOENIX_NL_NEN_PROFESSIONAL_REVIEW_INTEGRATION_v1_0
    from phoenix.autonomy.nl_nen_professional_review_package_integration import (
        prepare_nl_professional_review_basis,
        build_professional_review_package,
    )
    nl_review_basis=prepare_nl_professional_review_basis(
        repository=ctx["repository"],
        session=ctx["session"],
        workspace=ctx["workspace"],
        output_dir=ctx["output_dir"],
        project_context_path=(ctx["repository"]/project_context_ref) if project_context_ref else None,
    )

    # Install a project-scoped Suriname interim structural load source before the
    # v8.1->v8.12 chain asks the Structural Action & Load Basis Engine for v8.2.
    # Non-Suriname/non-residential projects remain unaffected and no professional
    # approval is implied.
    sr_load_basis=ensure_suriname_structural_load_basis(
        ctx, project_context_ref=project_context_ref
    )

    blockers=[]
    if not model_ref: blockers.append({"reason":"ARCHITECTURAL_MODEL_REQUIRED","message":"Constructieve keten vereist architectuurmodel."})
    if not detail_ref: blockers.append({"reason":"DETAILED_ELEMENTS_REQUIRED","message":"Constructieve afleiding vereist gedetailleerde bouwkundige elementen."})
    if not profile_ref: blockers.append({"reason":"STRUCTURAL_PROJECT_PROFILE_REQUIRED","message":"Projectspecifiek constructief profiel ontbreekt."})

    chain_names=[
        "PROJECT_PHOENIX_architectural_to_structural_model_derivation_v8_0_0.py",
        "PROJECT_PHOENIX_structural_analytical_model_generation_v8_1_0.py",
        "PROJECT_PHOENIX_structural_action_load_model_generation_v8_2_0.py",
        "PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py",
        "PROJECT_PHOENIX_structural_analysis_results_validation_v8_4_0.py",
        "PROJECT_PHOENIX_structural_code_limit_state_member_verification_v8_5_0.py",
        "PROJECT_PHOENIX_structural_global_stability_second_order_robustness_v8_6_0.py",
        "PROJECT_PHOENIX_structural_connection_support_joint_verification_v8_7_0.py",
        "PROJECT_PHOENIX_structural_foundation_interface_soil_support_verification_v8_8_0.py",
        "PROJECT_PHOENIX_structural_foundation_design_reinforcement_detailing_v8_9_0.py",
        "PROJECT_PHOENIX_structural_drawing_calculation_package_engineering_qaqc_v8_10_0.py",
        "PROJECT_PHOENIX_structural_engineering_review_approval_release_control_v8_11_0.py",
        "PROJECT_PHOENIX_structural_revision_change_impact_ifc_package_v8_12_0.py",
    ]
    discovery=[{"runner":x,"available":(ctx["repository"]/"runners"/x).is_file()} for x in chain_names]
    missing=[x["runner"] for x in discovery if not x["available"]]
    if missing:
        blockers.append({"reason":"STRUCTURAL_V8_CHAIN_INCOMPLETE","message":"Niet alle generieke v8.0-v8.12 engines zijn aanwezig.","missing_runners":missing})
    chain_manifest={"schema_version":"phoenix.structural-session-adapter-chain/2.0","project_id":ctx["project_id"],"chain":discovery,
                    "validated_session_chain_version":"1.0.0","legacy_pilot_dependency": False,
                    "local_material_selection_register":material_selection_ref,
                    "material_selection_register":material_selection_ref,
                    "local_material_availability_required":True,
                    "local_or_imported_material_supply_required":True,
                    "automatic_structural_approval":False,"structural_release":"LOCKED"}
    chain_manifest_path=ctx["output_dir"]/"structural_v8_chain_manifest.json";write_json(chain_manifest_path,chain_manifest)
    if blockers:
        return finish(ctx,capability_id=cap,label=label,status="BLOCKED_INPUT",
                      outputs=[repo_ref(chain_manifest_path,ctx["repository"])],blockers=blockers)

    v80=ctx["repository"]/"runners"/chain_names[0]
    v80_out=ctx["output_dir"]/"v8_0_structural_derivation"
    cmd=python_command(v80,
        "--project-profile",str(ctx["repository"]/profile_ref),
        "--architectural-model",str(ctx["repository"]/model_ref),
        "--detailed-elements",str(ctx["repository"]/detail_ref),
        "--output",str(v80_out))
    rc=run_subprocess(cmd,ctx["repository"],ctx["output_dir"]/"v8_0.log")
    v80_model=v80_out/"model"/"structural_candidate_model.json"
    if rc!=0 or not v80_model.is_file():
        return finish(ctx,capability_id=cap,label=label,status="FAILED",
                      outputs=[repo_ref(chain_manifest_path,ctx["repository"])],
                      blockers=[{"reason":"STRUCTURAL_V8_0_EXECUTION_FAILED","message":f"v8.0 stopte met exitcode {rc}."}])

    chain=run_structural_chain(
        repository=ctx["repository"],session=ctx["session"],workspace=ctx["workspace"],
        output_dir=ctx["output_dir"]/"validated_v8_1_to_v8_12",
        project_id=ctx["project_id"],v80_model_path=v80_model,
        architectural_model_path=ctx["repository"]/model_ref,
        detailed_elements_path=ctx["repository"]/detail_ref,
        material_selection_path=(ctx["repository"]/material_selection_ref) if material_selection_ref else None,
        project_context_path=(ctx["repository"]/project_context_ref) if project_context_ref else None,
    )
    stage_path=ctx["output_dir"]/"validated_v8_1_to_v8_12"/"stage_register.json"
    write_json(stage_path,chain.stage_register)
    outputs=[repo_ref(chain_manifest_path,ctx["repository"]),repo_ref(v80_model,ctx["repository"]),repo_ref(stage_path,ctx["repository"])]
    if sr_load_basis.get("register"):
        outputs.append(str(sr_load_basis["register"]))
    if sr_load_basis.get("source"):
        outputs.append(str(sr_load_basis["source"]))
    if nl_review_basis.get("status") != "NOT_APPLICABLE":
        for path in nl_review_basis.get("paths", []):
            outputs.append(repo_ref(Path(path),ctx["repository"]))
    outputs.extend(chain.outputs)
    nl_review_package={"status":"NOT_APPLICABLE","paths":[]}
    if nl_review_basis.get("status") != "NOT_APPLICABLE":
        nl_review_package=build_professional_review_package(
            repository=ctx["repository"],
            workspace=ctx["workspace"],
            output_dir=ctx["output_dir"],
            project_id=ctx["project_id"],
        )
        for path in nl_review_package.get("paths", []):
            outputs.append(repo_ref(Path(path),ctx["repository"]))

    if chain.status=="FAILED":
        return finish(ctx,capability_id=cap,label=label,status="FAILED",outputs=outputs,blockers=chain.blockers,
                      metadata={"completed_through":chain.completed_through,"next_stage":chain.next_stage,"session_chain_version":"1.0.0",
                                "legacy_pilot_dependency":False,"suriname_structural_load_basis":sr_load_basis})
    if chain.status=="BLOCKED":
        return finish(ctx,capability_id=cap,label=label,status="BLOCKED",outputs=outputs,blockers=chain.blockers,warnings=chain.warnings,
                      metadata={"completed_through":chain.completed_through,"next_stage":chain.next_stage,"session_chain_version":"1.0.0",
                                "generic_cross_version_mapping_blocker_removed":True,"legacy_pilot_dependency":False,"suriname_structural_load_basis":sr_load_basis})
    return finish(ctx,capability_id=cap,label=label,status="PASSED",outputs=outputs,warnings=chain.warnings,
                  metadata={"completed_through":"8.12.0","session_chain_version":"1.0.0",
                            "legacy_pilot_dependency":False,"suriname_structural_load_basis":sr_load_basis,
                            "automatic_professional_approval":False,"production_release":"LOCKED"})


def _session_location(ctx: dict[str, Any]) -> str | None:
    for source in (ctx["session"], ctx["manifest"]):
        for key in ("location", "project_location", "address", "site"):
            value = source.get(key) if isinstance(source, dict) else None
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def run_permit(ctx: dict[str, Any]) -> int:
    cap="permit"
    label=CAPABILITIES[cap]
    state=adapter_state(ctx["workspace"])
    arch=(state.get("capabilities") or {}).get("architecture") or {}
    arch_outputs=arch.get("outputs") or []
    context=_load_project_context_from_arch_state(ctx,arch_outputs) or {}
    facts=context.get("facts") if isinstance(context,dict) else {}
    facts=facts if isinstance(facts,dict) else {}
    location=facts.get("project_location") or _session_location(ctx)
    country=facts.get("country_code")
    municipality=facts.get("municipality")
    desired=set(ctx["session"].get("desired_outputs",[]))
    jurisdiction_key=":".join(str(x) for x in (country,municipality) if x)

    scope={
        "schema_version":"phoenix.permit-session-scope/1.1","project_id":ctx["project_id"],
        "location":location,"country_code":country,"municipality":municipality,"jurisdiction_key":jurisdiction_key or None,
        "requested":{"permit_dossier":"permit_dossier" in desired,"permit_analysis":"permit_analysis" in desired,"aerius":"aerius" in desired},
        "jurisdiction_confirmed":False,"automatic_permit_conclusion":False,"release":"LOCKED",
    }
    scope_path=ctx["output_dir"]/"permit_scope.json";write_json(scope_path,scope)
    if not location or not country:
        return finish(ctx,capability_id=cap,label=label,status="BLOCKED_INPUT",
            outputs=[repo_ref(scope_path,ctx["repository"])],
            blockers=[{"reason":"PROJECT_LOCATION_JURISDICTION_REQUIRED",
                       "message":"Expliciete projectlocatie plus betrouwbaar opgelost land/gebiedsdeel zijn vereist voor projectspecifieke vergunningrouting."}])

    checklist={
        "schema_version":"phoenix.permit-session-checklist/1.1","project_id":ctx["project_id"],
        "location":location,"country_code":country,"municipality":municipality,
        "checks":[
            {"id":"jurisdiction","status":"LOCATION_CONTEXT_RESOLVED_RULES_REQUIRE_SOURCE_EVIDENCE"},
            {"id":"planning_environment","status":"REQUIRES_SOURCE_EVIDENCE"},
            {"id":"bopa","status":"IF_APPLICABLE"},
            {"id":"aerius","status":"IF_APPLICABLE"},
            {"id":"participation","status":"IF_APPLICABLE"},
        ],
        "status":"CANDIDATE_ONLY","automatic_legal_conclusion":False,
    }
    checklist_path=ctx["output_dir"]/"permit_checklist.json";write_json(checklist_path,checklist)
    return finish(ctx,capability_id=cap,label=label,status="PASSED",
        outputs=[repo_ref(scope_path,ctx["repository"]),repo_ref(checklist_path,ctx["repository"])],
        warnings=["Locatie/jurisdictie-routing is kandidaatcontext; actuele vergunningregels vereisen bron-evidence."])


def run_cost_planning(ctx: dict[str, Any]) -> int:
    cap="cost_planning"
    label=CAPABILITIES[cap]
    state=adapter_state(ctx["workspace"])
    arch=(state.get("capabilities") or {}).get("architecture") or {}
    arch_outputs=arch.get("outputs") or []
    model_ref=next((x for x in arch_outputs if x.endswith("/architectural_model.json")),None)
    project_context_ref=next((x for x in arch_outputs if x.endswith("/project_context.json")),None)
    local_material_selection_ref=next((x for x in arch_outputs if x.endswith("/local_material_selection_register.json")),None)
    material_selection_ref=(
        next((x for x in arch_outputs if x.endswith("/structural_material_selection_register.json")),None)
        or local_material_selection_ref
    )
    global_sourcing_ref=next((x for x in arch_outputs if x.endswith("/global_material_sourcing_register.json")),None)
    landed_cost_ref=next((x for x in arch_outputs if x.endswith("/landed_cost_register.json")),None)

    project_context={}
    if project_context_ref:
        path=(ctx["repository"]/project_context_ref).resolve()
        if path.is_file():
            try:
                project_context=read_json(path)
            except Exception:
                project_context={}

    market=build_local_cost_market_context(
        repository=ctx["repository"],
        project_id=ctx["project_id"],
        project_context=project_context,
        manifest=ctx["manifest"],
    )

    market_path=ctx["output_dir"]/"local_cost_market_context.json"
    sources_path=ctx["output_dir"]/"local_cost_price_source_register.json"
    write_json(market_path,market.market_context)
    write_json(sources_path,market.source_register)

    currency=(
        market.market_context.get("project_currency")
        or ((market.market_context.get("geography") or {}).get("currency") if isinstance(market.market_context.get("geography"),dict) else None)
        or ctx["manifest"].get("currency")
    )
    if currency and ctx["manifest"].get("currency")!=currency:
        _update_project_manifest(ctx,{"currency":currency,"currency_basis":"LOCAL_COST_INTELLIGENCE_FROM_PROJECT_GEOGRAPHY"})

    register={
        "schema_version":"phoenix.cost-planning-session-input-register/1.1",
        "project_id":ctx["project_id"],
        "architectural_model":model_ref,
        "project_context":project_context_ref,
        "currency":currency,
        "pricing_level":market.market_context.get("selected_pricing_level"),
        "pricing_as_of_date":market.market_context.get("as_of_date"),
        "pricing_gate":market.market_context.get("pricing_gate"),
        "fx_used":market.market_context.get("fx_used",False),
        "market_context":repo_ref(market_path,ctx["repository"]),
        "price_source_register":repo_ref(sources_path,ctx["repository"]),
        "local_material_selection_register":local_material_selection_ref,
        "material_selection_register":material_selection_ref,
        "global_material_sourcing_register":global_sourcing_ref,
        "landed_cost_register":landed_cost_ref,
        "status":"INPUT_CHECK",
    }
    reg_path=ctx["output_dir"]/"cost_planning_input_register.json"
    write_json(reg_path,register)

    blockers=[]
    if not model_ref:
        blockers.append({
            "reason":"ARCHITECTURAL_MODEL_REQUIRED",
            "message":"Kosten/hoeveelheden vereisen een projectmodel of gevalideerde hoeveelheden."
        })
    material_selection={}
    if material_selection_ref:
        try:
            material_selection=read_json((ctx["repository"]/material_selection_ref).resolve())
        except Exception:
            material_selection={}
    material_supply_confirmed=bool(
        material_selection.get("all_requirements_supply_confirmed",False)
        or material_selection.get("all_requirements_locally_confirmed",False)
    )
    if (_phoenix_material_mode_cost_gate(locals())) and (not material_selection_ref or not material_supply_confirmed):
        blockers.append({
            "reason":"LOCAL_MATERIAL_AVAILABILITY_REQUIRED_FOR_COST_PLAN",
            "message":"Kostenplanning vereist bevestigde lokale of geïmporteerde levering; de legacy reason-code blijft behouden voor API/testcompatibiliteit en importopties vereisen complete landed-cost evidence tot Paramaribo.",
        })
    if material_selection.get("all_imported_selections_landed_cost_complete") is False:
        blockers.append({
            "reason":"IMPORTED_MATERIAL_LANDED_COST_EVIDENCE_REQUIRED",
            "message":"Een of meer importselecties missen complete vracht-, invoer-, belasting-, inklarings- of last-mile evidence.",
        })
    _phoenix_market_hard_blockers, _phoenix_unresolved_price_evidence = _phoenix_split_cost_blockers(market.blockers)
    blockers.extend(_phoenix_market_hard_blockers)
    price_evidence_status = "UNRESOLVED" if _phoenix_unresolved_price_evidence else "CONFIRMED"
    register["price_evidence_status"] = price_evidence_status
    register["unresolved_price_evidence"] = _phoenix_unresolved_price_evidence
    register["price_fabricated"] = False
    write_json(reg_path,register)

    outputs=[
        repo_ref(reg_path,ctx["repository"]),
        repo_ref(market_path,ctx["repository"]),
        repo_ref(sources_path,ctx["repository"]),
    ]

    if blockers:
        return finish(
            ctx,capability_id=cap,label=label,status="BLOCKED_INPUT",
            outputs=outputs,blockers=blockers,warnings=market.warnings,
            metadata={
                "local_cost_intelligence_version":"1.0.0",
                "project_currency":currency,
                "pricing_gate":market.market_context.get("pricing_gate"),
                "fx_used":False,
            },
        )

    # If a validated quantity take-off is present, price it immediately.
    quantity_ref=next(
        (x for x in arch_outputs if x.endswith("/quantity_takeoff.json") or x.endswith("/bill_of_quantities.json")),
        None
    )
    calculation_ref=None
    calculation_status=None
    if quantity_ref:
        qpath=(ctx["repository"]/quantity_ref).resolve()
        try:
            qvalue=read_json(qpath)
            quantity_items=qvalue.get("items") if isinstance(qvalue,dict) else None
        except Exception:
            quantity_items=None
        if isinstance(quantity_items,list):
            calc=calculate_cost_items(quantity_items=quantity_items,market_result=market)
            calc,_phoenix_calc_should_block=_phoenix_continue_cost_calculation(calc)
            calculation_status=calc.get("status") if isinstance(calc,dict) else None
            calc_path=ctx["output_dir"]/"local_cost_calculation.json"
            write_json(calc_path,calc)
            outputs.append(repo_ref(calc_path,ctx["repository"]))
            calculation_ref=repo_ref(calc_path,ctx["repository"])
            if _phoenix_calc_should_block:
                return finish(
                    ctx,capability_id=cap,label=label,status="BLOCKED_INPUT",
                    outputs=outputs,blockers=list(calc.get("blockers") or []),warnings=market.warnings,
                    metadata={"local_cost_intelligence_version":"1.0.0","project_currency":currency},
                )

    plan={
        "schema_version":"phoenix.cost-planning-session-plan/1.1",
        "project_id":ctx["project_id"],
        "model":model_ref,
        "project_context":project_context_ref,
        "market_context":repo_ref(market_path,ctx["repository"]),
        "price_source_register":repo_ref(sources_path,ctx["repository"]),
        "currency":currency,
        "pricing_level":market.market_context.get("selected_pricing_level"),
        "primary_ratebook":market.market_context.get("primary_ratebook"),
        "fx_used":False,
        "international_fx_fallback":False,
        "automatic_tax_application":False,
        "local_price_traceability_required":True,
        "local_material_availability_required":True,
        "local_material_selection_register":local_material_selection_ref,
        "local_or_imported_material_supply_required":True,
        "material_selection_register":material_selection_ref,
        "global_material_sourcing_register":global_sourcing_ref,
        "landed_cost_register":landed_cost_ref,
        "cost_calculation":calculation_ref,
        "price_evidence_status":price_evidence_status,
        "unresolved_price_evidence":_phoenix_unresolved_price_evidence,
        "price_fabricated":False,
        "cost_estimate_status":(
            "PARTIAL_UNRESOLVED_PRICES" if calculation_status=="PARTIAL_UNRESOLVED_PRICES"
            else "PRICE_EVIDENCE_UNRESOLVED_ESTIMATE_CONTINUES" if price_evidence_status=="UNRESOLVED"
            else "READY_FOR_LOCAL_MARKET_COST_ENGINE" if calculation_ref is None
            else "LOCAL_COST_CALCULATION_AVAILABLE"
        ),
        "schedule_status":"READY_FOR_PLANNING_ENGINE",
        "professional_review_required":True,
        "production_release":"LOCKED",
    }
    cost_estimate_path=emit_level_a_cost_estimate_artifact(
        output_dir=ctx["output_dir"],
        project_id=ctx["project_id"],
        session_id=ctx["session"].get("session_id"),
        plan=plan,
    )
    plan["cost_estimate_artifact"]=repo_ref(cost_estimate_path,ctx["repository"])
    plan_path=ctx["output_dir"]/"cost_planning_plan.json"
    write_json(plan_path,plan)
    outputs.append(repo_ref(plan_path,ctx["repository"]))
    outputs.append(repo_ref(cost_estimate_path,ctx["repository"]))
    return finish(
        ctx,capability_id=cap,label=label,status="PASSED",
        outputs=outputs,warnings=market.warnings,
        metadata={
            "local_cost_intelligence_version":"1.0.0",
            "project_currency":currency,
            "pricing_level":market.market_context.get("selected_pricing_level"),
            "pricing_as_of_date":market.market_context["as_of_date"],
            "fx_used":False,
        },
    )

def run_reporting(ctx: dict[str, Any]) -> int:
    cap="reporting"
    label=CAPABILITIES[cap]
    state=adapter_state(ctx["workspace"])
    report={
        "schema_version":"phoenix.autonomous-project-status-report/1.0",
        "project_id":ctx["project_id"],
        "session_id":ctx["session"].get("session_id"),
        "project_type":ctx["session"].get("project_type"),
        "brief":ctx["session"].get("brief"),
        "desired_outputs":ctx["session"].get("desired_outputs",[]),
        "capability_state":state.get("capabilities",{}),
        "report_type":"AUTONOMOUS_INTERIM_STATUS",
        "professional_release":False,
    }
    json_path=ctx["output_dir"]/"autonomous_status_report.json"
    write_json(json_path,report)

    md=["# Project Phoenix — Autonomous Status Report","",f"Project: **{ctx['project_id']}**","",
        "## Desired outputs"]
    md += [f"- {x}" for x in ctx["session"].get("desired_outputs",[])]
    md += ["","## Capability status"]
    for cid,value in (state.get("capabilities") or {}).items():
        md.append(f"- {cid}: {value.get('status','UNKNOWN')}")
    md += ["","Production release: **LOCKED**",""]
    md_path=ctx["output_dir"]/"autonomous_status_report.md"
    md_path.write_text("\n".join(md),encoding="utf-8")

    return finish(
        ctx,capability_id=cap,label=label,status="PASSED",
        outputs=[repo_ref(json_path,ctx["repository"]),repo_ref(md_path,ctx["repository"])],
        warnings=["Interim report reflects current orchestration state; it is not a professional release document."],
    )


def run_closure(ctx: dict[str, Any]) -> int:
    cap="closure"
    label=CAPABILITIES[cap]
    state=adapter_state(ctx["workspace"])
    capabilities=state.get("capabilities") or {}
    blockers=[]
    for cid,value in capabilities.items():
        if cid in {"closure"}:
            continue
        if value.get("status") not in {"PASSED"}:
            blockers.append({
                "capability_id":cid,
                "reason":"UPSTREAM_NOT_PASSED",
                "status":value.get("status"),
            })

    arch_value=capabilities.get("architecture") or {}
    arch_outputs=arch_value.get("outputs") or []
    material_ref=(
        next((x for x in arch_outputs if x.endswith("/structural_material_selection_register.json")),None)
        or next((x for x in arch_outputs if x.endswith("/local_material_selection_register.json")),None)
    )
    material_gate={}
    if material_ref:
        try:
            material_gate=read_json((ctx["repository"]/material_ref).resolve())
        except Exception:
            material_gate={}
    material_supply_ok=bool(
        material_gate.get("all_requirements_supply_confirmed",False)
        or material_gate.get("all_requirements_locally_confirmed",False)
    )
    if not material_supply_ok:
        blockers.append({
            "capability_id":"architecture",
            "reason":"LOCAL_MATERIAL_SUPPLY_GATE_NOT_PASSED",
            "status":material_gate.get("status") or "MISSING",
        })
    if not material_gate.get("all_structural_requirements_engineering_qualified",False):
        blockers.append({
            "capability_id":"structural_engineering",
            "reason":"LOCAL_STRUCTURAL_PRODUCT_TECHNICAL_EVIDENCE_REQUIRED",
            "status":"TECHNICAL_PRODUCT_EVIDENCE_REQUIRED",
        })

    gate={
        "schema_version":"phoenix.autonomous-qaqc-release-gate/1.1",
        "project_id":ctx["project_id"],
        "session_id":ctx["session"].get("session_id"),
        "qaqc_status":"BLOCKED" if blockers else "READY_FOR_HUMAN_REVIEW",
        "upstream_blocker_count":len(blockers),
        "upstream_blockers":blockers,
        "human_engineering_review_required":True,
        "automatic_professional_approval":False,
        "production_release":"LOCKED",
        "pat_status":"PENDING",
    }
    gate_path=ctx["output_dir"]/"qaqc_release_gate.json"
    write_json(gate_path,gate)
    project_zip_path,project_zip_manifest_path=emit_level_a_project_zip_artifact(
        workspace=ctx["workspace"],
        output_dir=ctx["output_dir"],
        project_id=ctx["project_id"],
        session_id=ctx["session"].get("session_id"),
        qaqc_gate_path=gate_path,
    )

    # Control adapter itself passed: it correctly enforces the release lock.
    return finish(
        ctx,capability_id=cap,label=label,status="PASSED",
        outputs=[
            repo_ref(gate_path,ctx["repository"]),
            repo_ref(project_zip_path,ctx["repository"]),
            repo_ref(project_zip_manifest_path,ctx["repository"]),
        ],
        warnings=["Release remains locked; human review and successful PAT are mandatory."],
        metadata={"upstream_blocker_count":len(blockers),"release":"LOCKED"},
    )


RUNNERS: dict[str, Callable[[dict[str, Any]], int]] = {
    "architecture":run_architecture,
    "digital_twin":run_digital_twin,
    "structural_engineering":run_structural,
    "permit":run_permit,
    "cost_planning":run_cost_planning,
    "reporting":run_reporting,
    "closure":run_closure,
}


def run_adapter(
    capability_id: str,
    repository: Path,
    session_file: Path,
    workspace: Path,
    output_dir: Path,
) -> int:
    if capability_id not in RUNNERS:
        raise KeyError(f"Unknown Phoenix Session Adapter capability: {capability_id}")
    ctx=load_session_context(repository,session_file,workspace,output_dir)
    return int(RUNNERS[capability_id](ctx))

# PHOENIX_SURINAME_MINIMUM_DELIVERABLE_BASELINE_HOOK_v1_0
# Added by Phoenix Suriname Structural Knowledge & Minimum Deliverable Baseline
# Masterpack v1.0. This hook never grants professional approval or production
# release; it can only preserve an existing result or make a passing closure
# fail-safe BLOCKED when the Suriname minimum-deliverable baseline is incomplete.
try:
    from phoenix.autonomy.suriname_structural_knowledge import (
        is_suriname_building_context as _phx_sr_is_building_context,
        write_suriname_structural_knowledge_register as _phx_sr_write_knowledge_register,
    )
    from phoenix.autonomy.minimum_deliverable_baseline import (
        evaluate_and_write_baseline as _phx_sr_evaluate_minimum_baseline,
    )

    _phx_sr_original_closure_runner = RUNNERS.get("closure")

    if _phx_sr_original_closure_runner is not None:
        def _phx_sr_baseline_closure_runner(ctx):
            original_rc = int(_phx_sr_original_closure_runner(ctx))

            if not _phx_sr_is_building_context(ctx):
                return original_rc

            try:
                _phx_sr_write_knowledge_register(ctx)
                baseline = _phx_sr_evaluate_minimum_baseline(ctx)
            except Exception as exc:
                # Evaluation failures may never become a false PASS.
                workspace = ctx.get("workspace")
                if workspace:
                    from pathlib import Path as _PhxPath
                    import json as _phx_json

                    p = (
                        _PhxPath(workspace)
                        / "results"
                        / "session_adapters"
                        / "closure"
                    )
                    p.mkdir(parents=True, exist_ok=True)
                    (
                        p / "minimum_deliverable_release_gate_overlay.json"
                    ).write_text(
                        _phx_json.dumps(
                            {
                                "schema_version": (
                                    "phoenix.minimum-deliverable-release-gate-overlay/1.0"
                                ),
                                "gate_status": "BLOCKED",
                                "release_ready": False,
                                "baseline_content_complete": False,
                                "reason": "BASELINE_GATE_EVALUATION_ERROR",
                                "detail": str(exc),
                                "automatic_professional_approval": False,
                                "production_release": "LOCKED",
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                return 10 if original_rc == 0 else original_rc

            if baseline and baseline.get("status") != "PASSED":
                return 10 if original_rc == 0 else original_rc

            return original_rc

        RUNNERS["closure"] = _phx_sr_baseline_closure_runner
except Exception:
    # Import-time safety: existing Phoenix remains available. The existing
    # production-release lock remains authoritative.
    pass

# PHOENIX_LANDED_COST_FALSE_PASS_GUARD_v1_0
# Prevent a vacuous PASSED landed-cost gate when imports are required but no complete import exists.
import functools as _phoenix_landed_guard_functools
from phoenix.autonomy.landed_cost_gate_guard import postprocess_adapter_result as _phoenix_landed_guard_postprocess

_phoenix_landed_guard_original_run_architecture = run_architecture

@_phoenix_landed_guard_functools.wraps(_phoenix_landed_guard_original_run_architecture)
def run_architecture(*args, **kwargs):
    _phoenix_landed_result = _phoenix_landed_guard_original_run_architecture(*args, **kwargs)
    return _phoenix_landed_guard_postprocess(_phoenix_landed_result, args=args, kwargs=kwargs)
# END PHOENIX_LANDED_COST_FALSE_PASS_GUARD_v1_0

# PHOENIX_MATERIAL_ENGINEERING_CONTINUATION_v1_1
# FIXED R2: accepts the live public structural adapter alias run_structural and resolves blocker targets repository-wide. Structural material availability
# may be enforced in a dedicated runner instead of directly in session_adapters.py.
# Material certification and availability are orthogonal. Availability never blocks design engineering;
# unresolved supply remains a procurement/release issue. Product properties are never represented
# as verified without evidence.
import functools as _phoenix_material_mode_functools
from phoenix.autonomy.material_certification_engineering_mode import (
    postprocess_architecture_result as _phoenix_material_mode_architecture_postprocess,
    postprocess_structural_result as _phoenix_material_mode_structural_postprocess,
    postprocess_cost_result as _phoenix_material_mode_cost_postprocess,
)

_phoenix_material_mode_original_run_architecture = run_architecture
@_phoenix_material_mode_functools.wraps(_phoenix_material_mode_original_run_architecture)
def run_architecture(*args, **kwargs):
    _result = _phoenix_material_mode_original_run_architecture(*args, **kwargs)
    return _phoenix_material_mode_architecture_postprocess(_result, args=args, kwargs=kwargs)

_phoenix_material_mode_original_run_structural = run_structural
@_phoenix_material_mode_functools.wraps(_phoenix_material_mode_original_run_structural)
def run_structural(*args, **kwargs):
    _result = _phoenix_material_mode_original_run_structural(*args, **kwargs)
    return _phoenix_material_mode_structural_postprocess(_result, args=args, kwargs=kwargs)

_phoenix_material_mode_original_run_cost_planning = run_cost_planning
@_phoenix_material_mode_functools.wraps(_phoenix_material_mode_original_run_cost_planning)
def run_cost_planning(*args, **kwargs):
    _result = _phoenix_material_mode_original_run_cost_planning(*args, **kwargs)
    return _phoenix_material_mode_cost_postprocess(_result, args=args, kwargs=kwargs)
# END PHOENIX_MATERIAL_ENGINEERING_CONTINUATION_v1_1
# PHOENIX_COST_PRICE_RUNTIME_CONTINUATION_FIXED_R4
# RUNNERS was created before the R4 wrappers; rebind public adapters to the wrapped callables.
RUNNERS["architecture"] = run_architecture
RUNNERS["structural_engineering"] = run_structural
RUNNERS["cost_planning"] = run_cost_planning
# Missing current price evidence remains unresolved, never fabricated, and does not block estimate/planning generation.
