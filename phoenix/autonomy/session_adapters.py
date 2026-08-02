"""Phoenix Generic Session Adapter Masterpack v1.0.

Seven adapters consume the same project session/workspace contract.
They never fabricate professional approval and never invoke project-specific pilot runners.
"""
from __future__ import annotations

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
    run_subprocess,
    python_command,
    write_json,
)


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


def run_architecture(ctx: dict[str, Any]) -> int:
    cap = "architecture"
    label = CAPABILITIES[cap]
    out = ctx["output_dir"]
    uploads = discover_upload_files(ctx)
    json_uploads = discover_json_uploads(ctx)

    intake = {
        "schema_version": "phoenix.architectural-session-intake/1.0",
        "project_id": ctx["project_id"],
        "session_id": ctx["session"].get("session_id"),
        "project_type": ctx["session"].get("project_type"),
        "brief": ctx["session"].get("brief"),
        "desired_outputs": ctx["session"].get("desired_outputs", []),
        "upload_files": [repo_ref(p, ctx["repository"]) for p in uploads],
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

    for path, value in json_uploads:
        if model_source is None and _architecture_model_candidate(value):
            model_source, model_value = path, value.get("architectural_model", value)
        if detail_source is None and _detailed_elements_candidate(value):
            detail_source, detail_value = path, value.get("detailed_elements", value)
        if profile_source is None and _structural_profile_candidate(value):
            profile_source, profile_value = path, value

    if model_source is None:
        geometry_formats = sorted(
            {p.suffix.lower() for p in uploads if p.suffix.lower() in {".ifc",".dwg",".dxf",".rvt",".skp"}}
        )
        blockers = [{
            "reason": "DIMENSIONED_ARCHITECTURAL_MODEL_REQUIRED",
            "message": (
                "Geen gestructureerd maatvoerend architectuurmodel gevonden. "
                "Phoenix genereert geen willekeurige gebouwgeometrie uit alleen vrije tekst."
            ),
            "accepted_now": ["JSON/GeoJSON met storeys/spaces"],
            "detected_unparsed_geometry_formats": geometry_formats,
        }]
        if geometry_formats:
            blockers.append({
                "reason": "CAD_BIM_IMPORT_ADAPTER_REQUIRED",
                "message": "CAD/BIM-bron is aanwezig, maar moet eerst naar het generieke architectuurmodel worden vertaald.",
            })
        return finish(
            ctx, capability_id=cap, label=label, status="BLOCKED_INPUT",
            outputs=[repo_ref(intake_path, ctx["repository"])],
            blockers=blockers,
            metadata={"upload_count": len(uploads)},
        )

    model_path = out / "architectural_model.json"
    write_json(model_path, model_value)

    outputs = [
        repo_ref(intake_path, ctx["repository"]),
        repo_ref(model_path, ctx["repository"]),
    ]
    metadata = {
        "architectural_model_source": repo_ref(model_source, ctx["repository"]),
        "candidate_only": True,
    }

    if detail_value is not None:
        detail_path = out / "detailed_elements.json"
        write_json(detail_path, detail_value)
        outputs.append(repo_ref(detail_path, ctx["repository"]))
        metadata["detailed_elements"] = repo_ref(detail_path, ctx["repository"])

    if profile_value is not None:
        profile_path = out / "structural_project_profile.json"
        write_json(profile_path, profile_value)
        outputs.append(repo_ref(profile_path, ctx["repository"]))
        metadata["structural_project_profile"] = repo_ref(profile_path, ctx["repository"])

    contract = {
        "schema_version": "phoenix.architectural-adapter-contract/1.0",
        "project_id": ctx["project_id"],
        "architectural_model": repo_ref(model_path, ctx["repository"]),
        "detailed_elements": metadata.get("detailed_elements"),
        "structural_project_profile": metadata.get("structural_project_profile"),
        "approval_state": "CANDIDATE_ONLY",
    }
    contract_path = out / "architectural_adapter_contract.json"
    write_json(contract_path, contract)
    outputs.append(repo_ref(contract_path, ctx["repository"]))

    return finish(
        ctx, capability_id=cap, label=label, status="PASSED",
        outputs=outputs,
        warnings=["Architectural model is candidate input and requires professional review."],
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
                "message": "Digital Twin wacht op een gestructureerd architectuurmodel.",
            }],
        )

    twin = {
        "schema_version": "phoenix.central-project-digital-twin/1.0",
        "project_id": ctx["project_id"],
        "session_id": ctx["session"].get("session_id"),
        "architectural_model": model_ref,
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
        warnings=["Digital Twin geometry remains candidate-only until discipline review."],
    )


def run_structural(ctx: dict[str, Any]) -> int:
    cap = "structural_engineering"
    label = CAPABILITIES[cap]
    state = adapter_state(ctx["workspace"])
    arch = (state.get("capabilities") or {}).get("architecture") or {}
    arch_outputs = arch.get("outputs") or []

    model_ref = next((x for x in arch_outputs if x.endswith("/architectural_model.json")), None)
    detail_ref = next((x for x in arch_outputs if x.endswith("/detailed_elements.json")), None)
    profile_ref = next((x for x in arch_outputs if x.endswith("/structural_project_profile.json")), None)

    blockers = []
    if not model_ref:
        blockers.append({"reason":"ARCHITECTURAL_MODEL_REQUIRED","message":"Constructieve keten vereist architectuurmodel."})
    if not detail_ref:
        blockers.append({"reason":"DETAILED_ELEMENTS_REQUIRED","message":"Constructieve afleiding vereist gedetailleerde bouwkundige elementen."})
    if not profile_ref:
        blockers.append({
            "reason":"STRUCTURAL_PROJECT_PROFILE_REQUIRED",
            "message":"Geen projectspecifiek constructief profiel gevonden; Phoenix vult normen/materialen/belastingsaannames niet stilzwijgend in.",
        })

    chain = [
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
    discovery = [{
        "version": f"8.{i}.0" if i <= 9 else f"8.{i}.0",
        "runner": name,
        "available": (ctx["repository"] / "runners" / name).is_file(),
    } for i, name in enumerate(chain)]

    chain_manifest = {
        "schema_version": "phoenix.structural-session-adapter-chain/1.0",
        "project_id": ctx["project_id"],
        "chain": discovery,
        "legacy_pilot_dependency": False,
        "automatic_structural_approval": False,
        "structural_release": "LOCKED",
    }
    chain_path = ctx["output_dir"] / "structural_v8_chain_manifest.json"
    write_json(chain_path, chain_manifest)

    missing_runners = [x["runner"] for x in discovery if not x["available"]]
    if missing_runners:
        blockers.append({
            "reason":"STRUCTURAL_V8_CHAIN_INCOMPLETE",
            "message":"Niet alle generieke v8.0–v8.12 runners zijn aanwezig.",
            "missing_runners": missing_runners,
        })

    if blockers:
        return finish(
            ctx, capability_id=cap, label=label, status="BLOCKED_INPUT",
            outputs=[repo_ref(chain_path, ctx["repository"])],
            blockers=blockers,
            metadata={"v8_chain_discovered": len(discovery) - len(missing_runners), "v8_chain_total": len(discovery)},
        )

    # Safe first hand-off: v8.0 has an explicit, known generic CLI contract.
    # Later v8 stages remain governed by their own release gates and are not
    # called until their input contracts are present/validated.
    v80 = ctx["repository"] / "runners" / chain[0]
    v80_out = ctx["output_dir"] / "v8_0_structural_derivation"
    cmd = python_command(
        v80,
        "--project-profile", str(ctx["repository"] / profile_ref),
        "--architectural-model", str(ctx["repository"] / model_ref),
        "--detailed-elements", str(ctx["repository"] / detail_ref),
        "--output", str(v80_out),
    )
    rc = run_subprocess(cmd, ctx["repository"], ctx["output_dir"] / "v8_0.log")
    if rc != 0:
        return finish(
            ctx, capability_id=cap, label=label, status="FAILED",
            outputs=[repo_ref(chain_path, ctx["repository"])],
            blockers=[{
                "reason":"STRUCTURAL_V8_0_EXECUTION_FAILED",
                "message":f"v8.0 runner stopte met exitcode {rc}.",
            }],
        )

    v80_model = v80_out / "model" / "structural_candidate_model.json"
    if not v80_model.is_file():
        return finish(
            ctx, capability_id=cap, label=label, status="FAILED",
            blockers=[{"reason":"STRUCTURAL_V8_0_OUTPUT_MISSING","message":"v8.0 produceerde geen structural_candidate_model.json."}],
        )

    # The adapter is connected to the full chain registry, but it refuses to
    # invent cross-version transformations. It records the exact next contract.
    handoff = {
        "schema_version":"phoenix.structural-session-handoff/1.0",
        "project_id":ctx["project_id"],
        "completed_through":"8.0.0",
        "next_stage":"8.1.0",
        "source_structural_candidate_model":repo_ref(v80_model,ctx["repository"]),
        "v8_chain_registry":repo_ref(chain_path,ctx["repository"]),
        "status":"READY_FOR_VALIDATED_V8_1_INPUT_MAPPING",
        "automatic_structural_approval":False,
        "release":"LOCKED",
    }
    handoff_path = ctx["output_dir"] / "structural_session_handoff.json"
    write_json(handoff_path,handoff)

    return finish(
        ctx, capability_id=cap, label=label, status="BLOCKED",
        outputs=[
            repo_ref(chain_path, ctx["repository"]),
            repo_ref(v80_model, ctx["repository"]),
            repo_ref(handoff_path, ctx["repository"]),
        ],
        blockers=[{
            "reason":"V8_1_TO_V8_12_VALIDATED_INPUT_MAPPING_REQUIRED",
            "message":"Session Adapter heeft v8.0 veilig uitgevoerd; v8.1–v8.12 blijven geblokkeerd totdat iedere tussenversie-input expliciet gevalideerd kan worden doorgegeven.",
        }],
        metadata={"completed_through":"8.0.0","chain_target":"8.12.0"},
    )


def _session_location(ctx: dict[str, Any]) -> str | None:
    for source in (ctx["session"], ctx["manifest"]):
        for key in ("location", "project_location", "address", "site"):
            value = source.get(key) if isinstance(source, dict) else None
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def run_permit(ctx: dict[str, Any]) -> int:
    cap = "permit"
    label = CAPABILITIES[cap]
    location = _session_location(ctx)
    desired = set(ctx["session"].get("desired_outputs", []))

    scope = {
        "schema_version":"phoenix.permit-session-scope/1.0",
        "project_id":ctx["project_id"],
        "location":location,
        "requested":{
            "permit_dossier":"permit_dossier" in desired,
            "permit_analysis":"permit_analysis" in desired,
            "aerius":"aerius" in desired,
        },
        "jurisdiction_confirmed":False,
        "automatic_permit_conclusion":False,
        "release":"LOCKED",
    }
    scope_path=ctx["output_dir"]/"permit_scope.json"
    write_json(scope_path,scope)

    if not location:
        return finish(
            ctx, capability_id=cap, label=label, status="BLOCKED_INPUT",
            outputs=[repo_ref(scope_path,ctx["repository"])],
            blockers=[{
                "reason":"PROJECT_LOCATION_JURISDICTION_REQUIRED",
                "message":"Vergunning/BOPA/AERIUS kan niet projectspecifiek worden bepaald zonder locatie/jurisdictie.",
            }],
        )

    checklist = {
        "schema_version":"phoenix.permit-session-checklist/1.0",
        "project_id":ctx["project_id"],
        "location":location,
        "checks":[
            {"id":"jurisdiction","status":"REQUIRES_VALIDATION"},
            {"id":"planning_environment","status":"REQUIRES_SOURCE_EVIDENCE"},
            {"id":"bopa","status":"IF_APPLICABLE"},
            {"id":"aerius","status":"IF_APPLICABLE"},
            {"id":"participation","status":"IF_APPLICABLE"},
        ],
        "status":"CANDIDATE_ONLY",
    }
    checklist_path=ctx["output_dir"]/"permit_checklist.json"
    write_json(checklist_path,checklist)
    return finish(
        ctx,capability_id=cap,label=label,status="PASSED",
        outputs=[repo_ref(scope_path,ctx["repository"]),repo_ref(checklist_path,ctx["repository"])],
        warnings=["Permit checklist is routing metadata, not a permit approval or AERIUS result."],
    )


def run_cost_planning(ctx: dict[str, Any]) -> int:
    cap="cost_planning"
    label=CAPABILITIES[cap]
    state=adapter_state(ctx["workspace"])
    arch=(state.get("capabilities") or {}).get("architecture") or {}
    arch_outputs=arch.get("outputs") or []
    model_ref=next((x for x in arch_outputs if x.endswith("/architectural_model.json")),None)

    ratebook_candidates=list((ctx["repository"]/"configs"/"phoenix").rglob("*ratebook*.json")) if (ctx["repository"]/"configs"/"phoenix").is_dir() else []
    register={
        "schema_version":"phoenix.cost-planning-session-input-register/1.0",
        "project_id":ctx["project_id"],
        "architectural_model":model_ref,
        "ratebook_candidates":[repo_ref(x,ctx["repository"]) for x in ratebook_candidates[:30]],
        "currency":ctx["manifest"].get("currency"),
        "status":"INPUT_CHECK",
    }
    reg_path=ctx["output_dir"]/"cost_planning_input_register.json"
    write_json(reg_path,register)

    blockers=[]
    if not model_ref:
        blockers.append({"reason":"ARCHITECTURAL_MODEL_REQUIRED","message":"Kosten/hoeveelheden vereisen een projectmodel of gevalideerde hoeveelheden."})
    if not ratebook_candidates:
        blockers.append({"reason":"RATEBOOK_REQUIRED","message":"Geen generiek Phoenix-ratebook gevonden."})
    if not ctx["manifest"].get("currency"):
        blockers.append({"reason":"CURRENCY_REQUIRED","message":"Projectvaluta is niet vastgelegd."})

    if blockers:
        return finish(
            ctx,capability_id=cap,label=label,status="BLOCKED_INPUT",
            outputs=[repo_ref(reg_path,ctx["repository"])],blockers=blockers,
        )

    plan={
        "schema_version":"phoenix.cost-planning-session-plan/1.0",
        "project_id":ctx["project_id"],
        "model":model_ref,
        "ratebook":repo_ref(ratebook_candidates[0],ctx["repository"]),
        "currency":ctx["manifest"]["currency"],
        "cost_estimate_status":"READY_FOR_COST_ENGINE",
        "schedule_status":"READY_FOR_PLANNING_ENGINE",
        "professional_review_required":True,
    }
    plan_path=ctx["output_dir"]/"cost_planning_plan.json"
    write_json(plan_path,plan)
    return finish(
        ctx,capability_id=cap,label=label,status="PASSED",
        outputs=[repo_ref(reg_path,ctx["repository"]),repo_ref(plan_path,ctx["repository"])],
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

    gate={
        "schema_version":"phoenix.autonomous-qaqc-release-gate/1.0",
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

    # Control adapter itself passed: it correctly enforces the release lock.
    return finish(
        ctx,capability_id=cap,label=label,status="PASSED",
        outputs=[repo_ref(gate_path,ctx["repository"])],
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
