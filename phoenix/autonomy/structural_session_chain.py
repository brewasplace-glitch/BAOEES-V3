"""Phoenix Structural v8.1-v8.12 Validated Session Chain v1.0.

The chain removes the generic cross-version mapping blocker, but never invents:
design actions, code basis, solver properties, analysis results, capacity checks,
stability checks, connection checks, geotechnical data, foundation design,
professional review or release authorization.
"""
from __future__ import annotations
from phoenix.autonomy.autonomous_solver_basis_v8_3 import (
    apply_solver_basis_to_analytical_model as _phoenix_apply_solver_basis_to_analytical_model,
    build_autonomous_solver_basis as _phoenix_build_autonomous_solver_basis,
    normalize_support_candidates_for_solver as _phoenix_normalize_support_candidates_for_solver,
)
from phoenix.autonomy.material_certification_engineering_mode import (
    structural_certification_block_should_apply as _phoenix_material_mode_structural_gate,
)

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .local_material_supply_intelligence import selected_engineering_material_ids
from .structural_action_load_basis import build_structural_action_load_basis

from .autonomous_calculix_results_v8_4 import autonomous_calculix_execution_enabled as _phoenix_v84_calculix_enabled, build_autonomous_calculix_results as _phoenix_build_autonomous_calculix_results
from .autonomous_global_stability_evidence_r9 import build_autonomous_global_stability_evidence as _phoenix_build_r9_global_stability_evidence
from .advanced_global_stability_qualification_r9_1 import build_advanced_stability_qualification as _phoenix_build_r9_1_stability_qualification
from .stability_design_basis_storey_residual_r9_2 import build_stability_design_basis_storey_residual as _phoenix_build_r9_2_stability_design_basis_storey_residual
from .residual_capacity_stability_design_basis_r9_3 import build_residual_capacity_stability_design_basis as _phoenix_build_r9_3_residual_capacity_stability_design_basis
from .normative_applicability_stability_design_basis_r9_4 import build_normative_applicability_stability_design_basis as _phoenix_build_r9_4_normative_applicability_stability_design_basis
from .project_stability_design_basis_decision_r9_5 import build_project_stability_design_basis_decision as _phoenix_build_r9_5_project_stability_design_basis_decision
from .project_stability_design_basis_input_evidence_qualification_r9_5_1 import build_project_stability_design_basis_input_evidence_qualification as _phoenix_build_r9_5_1_project_stability_design_basis_input_evidence_qualification
from .stability_design_basis_decision_dossier_evidence_intake_r9_5_2 import build_stability_design_basis_decision_dossier_evidence_intake as _phoenix_build_r9_5_2_stability_design_basis_decision_dossier_evidence_intake, render_decision_dossier_markdown as _phoenix_render_r9_5_2_decision_dossier_markdown
from .runtime_input_merge_r9_5_requalification_r9_5_2_4 import build_runtime_input_merge_r9_5_requalification as _phoenix_build_r9_5_2_4_runtime_input_merge_r9_5_requalification
from phoenix.autonomy.combined_cde_evidence_intake_r9_5_2_9 import run_combined_cde_evidence_intake_r9_5_2_9 as _phoenix_run_combined_cde_evidence_intake_r9_5_2_9
from .package_e_alternate_path_independent_evidence_r9_5_2_5 import build_package_e_alternate_path_independent_evidence as _phoenix_build_r9_5_2_5_package_e_alternate_path_independent_evidence, render_package_e_dossier_markdown as _phoenix_render_r9_5_2_5_package_e_dossier_markdown
from phoenix.autonomy.package_c_seismic_scope_criteria_r9_5_2_6 import run_package_c_seismic_scope_criteria_r9_5_2_6 as _phoenix_run_package_c_seismic_scope_criteria_r9_5_2_6
from phoenix.autonomy.package_d_weak_storey_screening_review_r9_5_2_7 import run_package_d_weak_storey_screening_review_r9_5_2_7 as _phoenix_run_package_d_weak_storey_screening_review_r9_5_2_7
from phoenix.autonomy.remaining_evidence_gate_consolidation_r9_5_2_8 import run_remaining_evidence_gate_consolidation_r9_5_2_8 as _phoenix_run_remaining_evidence_gate_consolidation_r9_5_2_8
from .stability_ab_project_policy_integration_r9_5_2_2 import apply_ab_project_policy_to_workspace as _phoenix_apply_r9_5_2_2_ab_policy_to_workspace, apply_ab_project_policy_to_r9_5_2_result as _phoenix_apply_r9_5_2_2_ab_policy_to_r9_5_2_result, render_licensed_clause_extract_request as _phoenix_render_r9_5_2_2_licensed_clause_extract_request

VERSION="1.0.0"

STAGES=[
    ("8.1.0","PROJECT_PHOENIX_structural_analytical_model_generation_v8_1_0.py"),
    ("8.2.0","PROJECT_PHOENIX_structural_action_load_model_generation_v8_2_0.py"),
    ("8.3.0","PROJECT_PHOENIX_structural_solver_input_analysis_v8_3_0.py"),
    ("8.4.0","PROJECT_PHOENIX_structural_analysis_results_validation_v8_4_0.py"),
    ("8.5.0","PROJECT_PHOENIX_structural_code_limit_state_member_verification_v8_5_0.py"),
    ("8.6.0","PROJECT_PHOENIX_structural_global_stability_second_order_robustness_v8_6_0.py"),
    ("8.7.0","PROJECT_PHOENIX_structural_connection_support_joint_verification_v8_7_0.py"),
    ("8.8.0","PROJECT_PHOENIX_structural_foundation_interface_soil_support_verification_v8_8_0.py"),
    ("8.9.0","PROJECT_PHOENIX_structural_foundation_design_reinforcement_detailing_v8_9_0.py"),
    ("8.10.0","PROJECT_PHOENIX_structural_drawing_calculation_package_engineering_qaqc_v8_10_0.py"),
    ("8.11.0","PROJECT_PHOENIX_structural_engineering_review_approval_release_control_v8_11_0.py"),
    ("8.12.0","PROJECT_PHOENIX_structural_revision_change_impact_ifc_package_v8_12_0.py"),
]

@dataclass
class ChainResult:
    status:str
    completed_through:str
    next_stage:str|None
    outputs:list[str]
    blockers:list[dict[str,Any]]
    warnings:list[str]
    stage_register:dict[str,Any]

def _read(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"JSON object required: {path}")
    return value

def _write(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _repo_ref(path:Path,repository:Path)->str:
    try:return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:return str(path.resolve())

def _run_json(repository:Path,runner:Path,input_path:Path,output_path:Path,log_path:Path)->int:
    output_path.parent.mkdir(parents=True,exist_ok=True)
    log_path.parent.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,str(runner),"--input",str(input_path),"--output",str(output_path)]
    with log_path.open("w",encoding="utf-8",newline="\n") as log:
        log.write(json.dumps(command,ensure_ascii=False)+"\n\n");log.flush()
        p=subprocess.run(command,cwd=str(repository),stdout=log,stderr=subprocess.STDOUT,text=True,check=False)
    return int(p.returncode)

def _run_v83(repository:Path,runner:Path,input_path:Path,output_dir:Path,log_path:Path)->int:
    output_dir.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,str(runner),"--input",str(input_path),"--output-dir",str(output_dir)]
    with log_path.open("w",encoding="utf-8",newline="\n") as log:
        log.write(json.dumps(command,ensure_ascii=False)+"\n\n");log.flush()
        p=subprocess.run(command,cwd=str(repository),stdout=log,stderr=subprocess.STDOUT,text=True,check=False)
    return int(p.returncode)

def _storey_map(architectural_model:dict[str,Any])->dict[str,dict[str,Any]]:
    return {str(x.get("storey_id")):x for x in architectural_model.get("storeys",[]) if isinstance(x,dict) and x.get("storey_id")}

def _detail_wall_map(detailed:dict[str,Any])->dict[str,dict[str,Any]]:
    out={}
    for storey in detailed.get("storeys",[]):
        if not isinstance(storey,dict): continue
        for wall in storey.get("walls",[]):
            if isinstance(wall,dict) and wall.get("element_id"): out[str(wall["element_id"])]=wall
    return out

def _space_map(architectural_model:dict[str,Any])->dict[str,dict[str,Any]]:
    out={}
    for storey in architectural_model.get("storeys",[]):
        if not isinstance(storey,dict): continue
        for space in storey.get("spaces",[]):
            if isinstance(space,dict) and space.get("space_id"): out[str(space["space_id"])]=space
    return out

def build_v81_input(v80:dict[str,Any],architectural_model:dict[str,Any],detailed:dict[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    storeys=_storey_map(architectural_model)
    walls=_detail_wall_map(detailed)
    spaces=_space_map(architectural_model)
    candidates={"columns":[],"beams":[],"loadbearing_walls":[],"slab_panels":[],"stability_zones":list(v80.get("stability_zones") or [])}
    mapping_warnings=[]

    def zinfo(storey_id:str)->tuple[float,float]:
        s=storeys.get(storey_id,{})
        try:z=float(s.get("elevation_m",0.0));h=float(s.get("height_m",3.0))
        except (TypeError,ValueError):z,h=0.0,3.0
        return z,h

    for item in v80.get("columns",[]):
        if not isinstance(item,dict):continue
        sid=str(item.get("storey_id") or "")
        z,h=zinfo(sid)
        candidates["columns"].append({
            "id":item.get("structural_id"),"base":[item.get("x_m",0),item.get("y_m",0),z],
            "top":[item.get("x_m",0),item.get("y_m",0),z+h],
            "material_candidate":item.get("material_hypothesis"),
            "section_candidate":"AUTO_PRELIMINARY_COLUMN",
            "source_v8_0_id":item.get("structural_id"),
        })

    for item in v80.get("beams",[]):
        if not isinstance(item,dict):continue
        sid=str(item.get("storey_id") or "")
        z,h=zinfo(sid); zz=z+h
        candidates["beams"].append({
            "id":item.get("structural_id"),
            "start":[item.get("start_x_m",0),item.get("start_y_m",0),zz],
            "end":[item.get("end_x_m",0),item.get("end_y_m",0),zz],
            "material_candidate":item.get("material_hypothesis"),
            "section_candidate":"AUTO_PRELIMINARY_BEAM",
            "source_v8_0_id":item.get("structural_id"),
        })

    for item in v80.get("walls",[]):
        if not isinstance(item,dict) or item.get("candidate_type")!="loadbearing_wall":continue
        wall=walls.get(str(item.get("architectural_element_id") or ""))
        if not wall:
            mapping_warnings.append(f"Wall geometry missing for {item.get('structural_id')}")
            continue
        sid=str(item.get("storey_id") or wall.get("storey_id") or "")
        z,h=zinfo(sid)
        x1,y1=wall.get("x1_m",0),wall.get("y1_m",0);x2,y2=wall.get("x2_m",0),wall.get("y2_m",0)
        candidates["loadbearing_walls"].append({
            "id":item.get("structural_id"),
            "polygon":[[x1,y1,z],[x2,y2,z],[x2,y2,z+h],[x1,y1,z+h]],
            "material_candidate":item.get("material_hypothesis"),
            "thickness_candidate":item.get("thickness_m"),
            "source_v8_0_id":item.get("structural_id"),
        })

    for item in v80.get("slabs",[]):
        if not isinstance(item,dict):continue
        space=spaces.get(str(item.get("architectural_space_id") or ""))
        if not space:
            mapping_warnings.append(f"Slab space geometry missing for {item.get('panel_id')}")
            continue
        sid=str(item.get("storey_id") or "")
        z,h=zinfo(sid);zz=z+h
        x=float(space.get("x_m",0));y=float(space.get("y_m",0))
        w=float(space.get("width_m",0));d=float(space.get("depth_m",0))
        candidates["slab_panels"].append({
            "id":item.get("panel_id"),
            "polygon":[[x,y,zz],[x+w,y,zz],[x+w,y+d,zz],[x,y+d,zz]],
            "material_candidate":item.get("material_hypothesis"),
            "thickness_candidate":"EXPLICIT_SOLVER_BASIS_REQUIRED",
            "source_v8_0_id":item.get("panel_id"),
        })

    payload={
        "structural_candidates":candidates,
        "analytical_model_policy":{
            "coordinate_tolerance_m":1e-6,
            "auto_generate_column_base_support_candidates":True,
        },
    }
    mapping={
        "schema_version":"phoenix.structural-v8.0-to-v8.1-mapping/1.0",
        "status":"VALIDATED_GEOMETRIC_MAPPING",
        "source_schema":v80.get("schema_version"),
        "geometry_sources":["v8.0 structural candidate","architectural_model","detailed_elements"],
        "design_values_invented":False,
        "warnings":mapping_warnings,
    }
    return payload,mapping

def _candidate_paths(repository:Path,workspace:Path,session:dict[str,Any],project_id:str)->list[Path]:
    roots=[workspace/"inputs",workspace/"structural_inputs",repository/"inputs"/"structural"/project_id]
    batch=str(session.get("upload_batch") or "").strip()
    if batch:
        roots.append(repository/"inputs"/"runtime"/"official_start_v3_uploads"/batch)
    paths=[]
    for root in roots:
        if root.is_dir():
            paths.extend(p for p in root.rglob("*.json") if p.is_file())
    return sorted(set(paths))

def _all_candidates(repository:Path,workspace:Path,session:dict[str,Any],project_id:str)->list[tuple[str,dict[str,Any]]]:
    result=[("SESSION",session)]
    for path in _candidate_paths(repository,workspace,session,project_id):
        try: result.append((_repo_ref(path,repository),_read(path)))
        except Exception: pass
    return result

def _section(candidates:list[tuple[str,dict[str,Any]]],section_name:str,required_keys:tuple[str,...]=())->tuple[dict[str,Any]|None,str|None]:
    for source,value in candidates:
        direct=value.get(section_name)
        if isinstance(direct,dict) and all(k in direct for k in required_keys):
            return direct,source
        if all(k in value for k in required_keys) and (
            section_name.lower() in source.lower() or value.get("schema_version","").lower().find(section_name.lower().replace("_","-"))>=0
        ):
            return value,source
    return None,None

def _apply_assignments(analytical:dict[str,Any],basis_input:dict[str,Any])->tuple[dict[str,Any],list[str]]:
    model=json.loads(json.dumps(analytical))
    assignments=basis_input.get("element_assignments") or {}
    by_id=assignments.get("by_id") or {}
    by_type=assignments.get("by_type") or {}
    missing=[]
    for collection in ("members","shells"):
        for item in model.get(collection,[]):
            iid=str(item.get("id") or "")
            rule=by_id.get(iid) if isinstance(by_id,dict) else None
            if not isinstance(rule,dict):
                rule=by_type.get(str(item.get("type") or "")) if isinstance(by_type,dict) else None
            if isinstance(rule,dict):
                item["material_id"]=rule.get("material_id")
                item["section_id"]=rule.get("section_id")
            if not item.get("material_id") or not item.get("section_id"):
                missing.append(iid or f"{collection}:UNKNOWN")
    supports=model.get("support_candidates")
    if isinstance(supports,list) and "supports" not in model:
        model["supports"]=[{
            "id":x.get("id"),"node_id":x.get("node_id"),
            "dofs":["UX","UY","UZ","RX","RY","RZ"] if "FIXED" in str(x.get("type","")).upper() else ["UX","UY","UZ"]
        } for x in supports if isinstance(x,dict)]
    return model,missing

def _block(reason:str,message:str,completed:str,next_stage:str,outputs:list[str],register:dict[str,Any],extra:dict[str,Any]|None=None)->ChainResult:
    blocker={"reason":reason,"message":message}
    if extra:blocker.update(extra)
    return ChainResult("BLOCKED",completed,next_stage,outputs,[blocker],[],register)

def run_structural_chain(
    *,
    repository:Path,
    session:dict[str,Any],
    workspace:Path,
    output_dir:Path,
    project_id:str,
    v80_model_path:Path,
    architectural_model_path:Path,
    detailed_elements_path:Path,
    material_selection_path:Path|None=None,
    project_context_path:Path|None=None,
)->ChainResult:
    repository=repository.resolve();workspace=workspace.resolve();output_dir=output_dir.resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    register={
        "schema_version":"phoenix.structural-session-chain/1.0",
        "chain_version":VERSION,
        "project_id":project_id,
        "stages":[],
        "automatic_design_value_invention":False,
        "automatic_professional_approval":False,
        "production_release":"LOCKED",
    }
    outputs=[]
    for version,runner_name in STAGES:
        runner=repository/"runners"/runner_name
        register["stages"].append({"version":version,"runner":runner_name,"available":runner.is_file(),"status":"PENDING"})
    missing=[x["runner"] for x in register["stages"] if not x["available"]]
    if missing:
        return _block("STRUCTURAL_V8_CHAIN_INCOMPLETE","Niet alle generieke v8.1-v8.12 engines zijn aanwezig.","8.0.0","8.1.0",outputs,register,{"missing_runners":missing})

    v80=_read(v80_model_path);arch=_read(architectural_model_path);detail=_read(detailed_elements_path)
    v81_input,mapping=build_v81_input(v80,arch,detail)
    v81_in=output_dir/"v8_1"/"input.json";v81_out=output_dir/"v8_1"/"analytical_model.json";map_path=output_dir/"v8_1"/"validated_mapping.json"
    _write(v81_in,v81_input);_write(map_path,mapping)
    rc=_run_json(repository,repository/"runners"/STAGES[0][1],v81_in,v81_out,output_dir/"v8_1"/"runner.log")
    if rc!=0 or not v81_out.is_file():
        return ChainResult("FAILED","8.0.0","8.1.0",outputs,[{"reason":"STRUCTURAL_V8_1_EXECUTION_FAILED","message":f"v8.1 stopte met exitcode {rc}."}],[],register)
    register["stages"][0]["status"]="PASSED"
    outputs.extend([_repo_ref(v81_out,repository),_repo_ref(map_path,repository)])
    completed="8.1.0"

    candidates=_all_candidates(repository,workspace,session,project_id)

    action_input,action_source=_section(candidates,"action_load_input",("basis","unit_system","actions","combinations"))
    if not action_input or not action_input.get("actions") or not action_input.get("combinations"):
        project_context={}
        if project_context_path is not None and project_context_path.is_file():
            try:project_context=_read(project_context_path)
            except Exception:project_context={}
        acquired_basis=build_structural_action_load_basis(
            repository=repository,
            project_id=project_id,
            project_context=project_context,
        )
        basis_register_path=output_dir/"v8_2"/"structural_action_load_source_register.json"
        _write(basis_register_path,acquired_basis.source_register)
        outputs.append(_repo_ref(basis_register_path,repository))
        if acquired_basis.status=="PASSED" and acquired_basis.action_load_input:
            action_input=acquired_basis.action_load_input
            action_source=(acquired_basis.source_register.get("selected") or {}).get("source_reference") or "AUTONOMOUS_REAL_WORLD_LOAD_BASIS"
        else:
            template={
                "schema_version":"phoenix.structural-action-load-input-template/1.1",
                "action_load_input":{
                    "basis":"REQUIRED_EXPLICIT_PROJECT_OR_CURRENT_NORMATIVE_BASIS",
                    "unit_system":{"length":"m","force":"kN","moment":"kNm","stress":"kPa","mass":"kg"},
                    "actions":[],
                    "combinations":[],
                },
                "note":"Phoenix vult belastingswaarden en normatieve combinatiefactoren niet stilzwijgend in."
            }
            tp=workspace/"inputs"/"structural"/"action_load_input_REQUIRED.json";_write(tp,template);outputs.append(_repo_ref(tp,repository))
            register["stages"][1]["status"]="BLOCKED_INPUT"
            blocker=acquired_basis.blockers[0] if acquired_basis.blockers else {
                "reason":"CURRENT_STRUCTURAL_ACTION_LOAD_BASIS_REQUIRED",
                "message":"Actuele projectspecifieke belastings-/combinatiebasis vereist voor v8.2."
            }
            return _block(blocker["reason"],blocker["message"],completed,"8.2.0",outputs,register,blocker)

    v82_payload={"analytical_model":_read(v81_out),"action_load_input":action_input}
    v82_in=output_dir/"v8_2"/"input.json";v82_out=output_dir/"v8_2"/"action_load_model.json"
    _write(v82_in,v82_payload)
    rc=_run_json(repository,repository/"runners"/STAGES[1][1],v82_in,v82_out,output_dir/"v8_2"/"runner.log")
    if rc!=0 or not v82_out.is_file():
        return ChainResult("FAILED",completed,"8.2.0",outputs,[{"reason":"STRUCTURAL_V8_2_EXECUTION_FAILED","message":f"v8.2 stopte met exitcode {rc}."}],[],register)
    register["stages"][1].update({"status":"PASSED","input_source":action_source});outputs.append(_repo_ref(v82_out,repository));completed="8.2.0"

    # PHOENIX_R8_2_1_RUNTIME_CHAIN_INTEGRITY_FIX_V1_1
    # v8.2 generated the authoritative action/load model for all downstream
    # solver-basis, topology, meshing, solver-package and v8.4 evidence paths.
    action_load_for_solver=_read(v82_out)

    material_selection={}
    if material_selection_path is not None and material_selection_path.is_file():
        try:
            material_selection=_read(material_selection_path)
        except Exception:
            material_selection={}
    if (_phoenix_material_mode_structural_gate(locals())) and (not material_selection.get("all_structural_requirements_engineering_qualified",False)):
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block(
            "LOCAL_STRUCTURAL_MATERIAL_AVAILABILITY_REQUIRED",
            "v8.2 kan zijn afgerond, maar vóór solvermateriaalgebruik moeten constructieve producten lokaal of via import beschikbaar, gecertificeerd en technisch engineering-gekwalificeerd zijn.",
            completed,"8.3.0",outputs,register,
            {"material_selection":_repo_ref(material_selection_path,repository) if material_selection_path else None}
        )

    solver_input,solver_source=_section(candidates,"structural_analysis_basis",("solver_basis","element_assignments","solver_adapters","execution_policy"))
    # PHOENIX_V8_3_IGNORE_STALE_REQUIRED_TEMPLATE_V1_0
    # A durable *_REQUIRED template from an earlier blocked PAT is not engineering input.
    # Ignore only the canonical empty EXPLICIT_REQUIRED placeholder so autonomous
    # generation can run. Explicit/manual non-placeholder solver bases are preserved.
    if solver_input:
        _phoenix_solver_basis_probe = solver_input.get("solver_basis") or {}
        _phoenix_assignment_probe = solver_input.get("element_assignments") or {}
        _phoenix_is_stale_required_template = (
            str(_phoenix_solver_basis_probe.get("basis") or "").upper() == "EXPLICIT_REQUIRED"
            and not (_phoenix_solver_basis_probe.get("materials") or {})
            and not (_phoenix_solver_basis_probe.get("sections") or {})
            and not (_phoenix_assignment_probe.get("by_id") or {})
            and not (_phoenix_assignment_probe.get("by_type") or {})
        )
        if _phoenix_is_stale_required_template:
            solver_input = None
            solver_source = None
    # PHOENIX_V8_3_AUTONOMOUS_SOLVER_BASIS_V1_0
    if not solver_input:
        _phoenix_autonomous_basis = _phoenix_build_autonomous_solver_basis(
            repository=repository,
            workspace=workspace,
            project_id=project_id,
            analytical_model=_read(v81_out),
            action_load_model=action_load_for_solver,
            material_selection=material_selection,
            candidates=candidates,
        )
        _phoenix_basis_register = _phoenix_autonomous_basis.get("register") or {}
        _phoenix_basis_register_path = output_dir/"v8_3"/"autonomous_solver_basis_register.json"
        _write(_phoenix_basis_register_path,_phoenix_basis_register)
        outputs.append(_repo_ref(_phoenix_basis_register_path,repository))
        if _phoenix_autonomous_basis.get("status") == "PASSED":
            solver_input = _phoenix_autonomous_basis["structural_analysis_basis"]
            solver_source = "AUTONOMOUS_SOLVER_BASIS_V1_0"
            _phoenix_basis_path = output_dir/"v8_3"/"autonomous_structural_analysis_basis.json"
            _write(_phoenix_basis_path,{
                "schema_version":"phoenix.structural-analysis-basis-autonomous/1.0",
                "structural_analysis_basis":solver_input,
                "provenance":_phoenix_basis_register,
            })
            outputs.append(_repo_ref(_phoenix_basis_path,repository))
        else:
            tp=workspace/"inputs"/"structural"/"structural_analysis_basis_REQUIRED.json"
            _write(tp,{
                "schema_version":"phoenix.structural-analysis-basis-template/1.1",
                "structural_analysis_basis":_phoenix_autonomous_basis.get("structural_analysis_basis") or {
                    "solver_basis":{"basis":"EXPLICIT_REQUIRED","analysis_type":"LINEAR_STATIC","materials":{},"sections":{}},
                    "element_assignments":{"by_id":{},"by_type":{}},
                    "solver_adapters":["opensees","calculix"],
                    "execution_policy":{"allow_execution":False,"require_explicit_cli_opt_in":True},
                },
                "blockers":_phoenix_autonomous_basis.get("blockers") or [],
                "note":"Phoenix invents no missing solver material properties, design classes or element sections.",
            })
            outputs.append(_repo_ref(tp,repository))
            register["stages"][2]["status"]="BLOCKED_INPUT"
            _phoenix_blockers=_phoenix_autonomous_basis.get("blockers") or [{
                "reason":"STRUCTURAL_SOLVER_BASIS_AND_ELEMENT_ASSIGNMENTS_REQUIRED",
                "message":"Traceable solver materials, sections and element assignments are required for v8.3.",
            }]
            _phoenix_primary=_phoenix_blockers[0]
            return _block(
                _phoenix_primary.get("reason") or "STRUCTURAL_SOLVER_BASIS_AND_ELEMENT_ASSIGNMENTS_REQUIRED",
                _phoenix_primary.get("message") or "Traceable solver basis required for v8.3.",
                completed,"8.3.0",outputs,register,_phoenix_primary
            )
    qualified_engineering_ids=selected_engineering_material_ids(material_selection)
    solver_materials=set(str(x) for x in (solver_input.get("solver_basis") or {}).get("materials",{}).keys())
    unconfirmed_solver_materials=sorted(x for x in solver_materials if x not in qualified_engineering_ids)
    if (_phoenix_material_mode_structural_gate(locals())) and unconfirmed_solver_materials:
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block(
            "STRUCTURAL_SOLVER_MATERIAL_NOT_LOCALLY_CONFIRMED",
            "Solverbasis verwijst naar materialen die niet als geselecteerde, leverbare en engineering-gekwalificeerde materialen zijn bevestigd; de legacy reason-code blijft behouden voor compatibiliteit.",
            completed,"8.3.0",outputs,register,
            {"unconfirmed_material_ids":unconfirmed_solver_materials}
        )

    if solver_source == "AUTONOMOUS_SOLVER_BASIS_V1_0":
        analytical_for_solver,missing_assignments=_phoenix_apply_solver_basis_to_analytical_model(_read(v81_out),solver_input)
    else:
        analytical_for_solver,missing_assignments=_apply_assignments(_read(v81_out),solver_input)
    analytical_for_solver=_phoenix_normalize_support_candidates_for_solver(analytical_for_solver)
    if missing_assignments:
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block("STRUCTURAL_SOLVER_ELEMENT_ASSIGNMENTS_INCOMPLETE","Niet alle analytische elementen hebben expliciete material_id en section_id.",completed,"8.3.0",outputs,register,{"missing_element_ids":missing_assignments[:50]})

    # PHOENIX_R8_1_STRUCTURAL_TOPOLOGY_SUPPORT_REPAIR_GATE_V1_0
    from phoenix.autonomy.autonomous_structural_topology_support_repair_v8_1_r81 import (
        repair_structural_topology_for_solver,
    )
    _phx_r81_policy=_read(
        repository/"configs"/"phoenix"/"structural"/
        "autonomous_structural_topology_support_repair_policy_r8_1.json"
    )
    _phx_r81=repair_structural_topology_for_solver(
        project_id=project_id,
        analytical_model=analytical_for_solver,
        policy=_phx_r81_policy,
    )
    analytical_for_solver=_phx_r81["analytical_model"]
    _phx_r81_register_path=(
        output_dir/"v8_2"/
        "structural_topology_support_repair_r8_1.json"
    )
    _write(_phx_r81_register_path,_phx_r81["register"])
    outputs.append(
        _repo_ref(_phx_r81_register_path,repository)
    )
    # PHOENIX_R8_2_GEOMETRY_GROUNDED_INTERFACE_MESHING_V1_0
    if _phx_r81.get("status")!="PASSED":
        _phx_r81_blockers=_phx_r81.get("blockers") or []
        _phx_r81_reasons={
            str(x.get("reason") or "")
            for x in _phx_r81_blockers
            if isinstance(x,dict)
        }
        _phx_r82_allowed_reasons={
            "STRUCTURAL_LOAD_PATH_UNRESOLVED",
            "STRUCTURAL_UNANCHORED_COMPONENTS",
        }
        _phx_r82_may_repair=(
            "STRUCTURAL_LOAD_PATH_UNRESOLVED" in _phx_r81_reasons
            and _phx_r81_reasons.issubset(_phx_r82_allowed_reasons)
        )
        if not _phx_r82_may_repair:
            register["stages"][2]["status"]="BLOCKED_INPUT"
            _phx_r81_primary=(_phx_r81_blockers or [{
                "reason":"STRUCTURAL_LOAD_PATH_UNRESOLVED",
                "message":"Structurele load path is niet opgelost.",
            }])[0]
            return _block(
                _phx_r81_primary.get("reason")
                or "STRUCTURAL_LOAD_PATH_UNRESOLVED",
                _phx_r81_primary.get("message")
                or "Structurele load path is niet opgelost.",
                completed,"8.3.0",outputs,register,_phx_r81_primary
            )

        from phoenix.autonomy.autonomous_structural_interface_meshing_v8_1_r82 import (
            repair_geometry_grounded_interfaces,
        )
        _phx_r82_policy=_read(
            repository/"configs"/"phoenix"/"structural"/
            "autonomous_structural_interface_meshing_policy_r8_2.json"
        )
        _phx_r82=repair_geometry_grounded_interfaces(
            project_id=project_id,
            analytical_model=analytical_for_solver,
            action_load_model=action_load_for_solver,
            r8_1_register=_phx_r81["register"],
            policy=_phx_r82_policy,
        )
        _phx_r82_register_path=(
            output_dir/"v8_2"/"structural_interface_meshing_r8_2.json"
        )
        _write(_phx_r82_register_path,_phx_r82["register"])
        outputs.append(_repo_ref(_phx_r82_register_path,repository))

        if _phx_r82.get("status")!="PASSED":
            register["stages"][2]["status"]="BLOCKED_INPUT"
            _phx_r82_blockers=_phx_r82.get("blockers") or [{
                "reason":"STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                "message":"R8.2 kon de interface niet met bestaande geometrische evidence meshen.",
            }]
            _phx_r82_primary=_phx_r82_blockers[0]
            return _block(
                _phx_r82_primary.get("reason")
                or "STRUCTURAL_INTERFACE_GEOMETRY_EVIDENCE_REQUIRED",
                _phx_r82_primary.get("message")
                or "Geometrische interface-evidence vereist.",
                completed,"8.3.0",outputs,register,_phx_r82_primary
            )

        analytical_for_solver=_phx_r82["analytical_model"]
        action_load_for_solver=_phx_r82["action_load_model"]
        _phx_r82_action_path=(
            output_dir/"v8_2"/"action_load_model_for_solver_r8_2.json"
        )
        _write(_phx_r82_action_path,action_load_for_solver)
        outputs.append(_repo_ref(_phx_r82_action_path,repository))

        # Re-run the conservative R8.1 topology gate on the repaired mesh.
        _phx_r81_post=repair_structural_topology_for_solver(
            project_id=project_id,
            analytical_model=analytical_for_solver,
            policy=_phx_r81_policy,
        )
        analytical_for_solver=_phx_r81_post["analytical_model"]
        _phx_r81_post_path=(
            output_dir/"v8_2"/
            "structural_topology_support_repair_r8_1_post_r8_2.json"
        )
        _write(_phx_r81_post_path,_phx_r81_post["register"])
        outputs.append(_repo_ref(_phx_r81_post_path,repository))
        if _phx_r81_post.get("status")!="PASSED":
            register["stages"][2]["status"]="BLOCKED_INPUT"
            _phx_post_blockers=_phx_r81_post.get("blockers") or [{
                "reason":"STRUCTURAL_LOAD_PATH_UNRESOLVED",
                "message":"Post-R8.2 topology-validatie blijft geblokkeerd.",
            }]
            _phx_post_primary=_phx_post_blockers[0]
            return _block(
                _phx_post_primary.get("reason")
                or "STRUCTURAL_LOAD_PATH_UNRESOLVED",
                _phx_post_primary.get("message")
                or "Post-R8.2 structurele load path is niet opgelost.",
                completed,"8.3.0",outputs,register,_phx_post_primary
            )

    v83_payload={
        "project_id":project_id,
        "analytical_model":analytical_for_solver,
        "solver_basis":solver_input["solver_basis"],
        "action_load_model":action_load_for_solver,
        "solver_adapters":solver_input["solver_adapters"],
        "execution_policy":solver_input["execution_policy"],
    }
    v83_in=output_dir/"v8_3"/"input.json";v83_dir=output_dir/"v8_3"/"solver_package"
    _write(v83_in,v83_payload)
    rc=_run_v83(repository,repository/"runners"/STAGES[2][1],v83_in,v83_dir,output_dir/"v8_3"/"runner.log")
    manifest=v83_dir/"PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
    if rc!=0 or not manifest.is_file():
        return ChainResult("FAILED",completed,"8.3.0",outputs,[{"reason":"STRUCTURAL_V8_3_EXECUTION_FAILED","message":f"v8.3 stopte met exitcode {rc}."}],[],register)
    register["stages"][2].update({"status":"PASSED","input_source":solver_source});outputs.append(_repo_ref(manifest,repository));completed="8.3.0"

    results_input,results_source=_section(candidates,"structural_analysis_results",("analysis_result_sets","validation_policy"))
    # PHOENIX_V8_4_AUTONOMOUS_CALCULIX_RESULTS_V1_0
    # A durable *_REQUIRED v8.4 template is not real solver evidence.
    if results_input:
        _phx_v84_sets = results_input.get("analysis_result_sets") or []
        _phx_v84_policy = results_input.get("validation_policy") or {}
        _phx_v84_expected = results_input.get("expected_case_resultants_kN") or {}
        if not _phx_v84_sets and not _phx_v84_policy and not _phx_v84_expected:
            results_input = None
            results_source = None

    if not results_input and _phoenix_v84_calculix_enabled(session):
        _phx_v84_auto = _phoenix_build_autonomous_calculix_results(
            repository=repository,
            project_id=project_id,
            analytical_model=analytical_for_solver,
            action_load_model=action_load_for_solver,
            solver_package_dir=v83_dir,
            output_dir=output_dir/"v8_4",
        )
        for _phx_artifact in (_phx_v84_auto.get("artifacts") or []):
            if _phx_artifact not in outputs:
                outputs.append(_phx_artifact)
        if _phx_v84_auto.get("status") == "PASSED" and _phx_v84_auto.get("structural_analysis_results"):
            results_input = _phx_v84_auto["structural_analysis_results"]
            results_source = "AUTONOMOUS_CALCULIX_RESULTS_V1_0"
        else:
            register["stages"][3]["status"]="BLOCKED_INPUT"
            _phx_blockers = _phx_v84_auto.get("blockers") or [{
                "reason":"CALCULIX_AUTONOMOUS_RESULTS_REQUIRED",
                "message":"Echte CalculiX-resultaten en traceerbare normalisatie zijn vereist voor v8.4.",
            }]
            _phx_primary = _phx_blockers[0]
            return _block(
                _phx_primary.get("reason") or "CALCULIX_AUTONOMOUS_RESULTS_REQUIRED",
                _phx_primary.get("message") or "Echte CalculiX-resultaten vereist.",
                completed,"8.4.0",outputs,register,_phx_primary
            )

    if not results_input:
        tp=workspace/"inputs"/"structural"/"structural_analysis_results_REQUIRED.json"
        _write(tp,{
            "schema_version":"phoenix.structural-analysis-results-template/1.0",
            "structural_analysis_results":{
                "analysis_result_sets":[],
                "validation_policy":{},
                "expected_case_resultants_kN":{},
            },
            "note":"Genormaliseerde solverresultaten met raw-solver evidence zijn vereist; Phoenix verzint geen analyseresultaten."
        });outputs.append(_repo_ref(tp,repository))
        register["stages"][3]["status"]="BLOCKED_INPUT"
        return _block("NORMALIZED_SOLVER_RESULTS_REQUIRED","v8.3 solverpakket is gegenereerd; genormaliseerde solverresultaten en validatiebeleid zijn vereist voor v8.4.",completed,"8.4.0",outputs,register)

    v84_payload={
        "project_id":project_id,"source_engine":"PHX-STRUCT-SOLVER-INPUT-ANALYSIS-V8.3.0",
        "analytical_model":analytical_for_solver,"action_load_model":action_load_for_solver,
        "analysis_result_sets":results_input["analysis_result_sets"],
        "validation_policy":results_input["validation_policy"],
        "expected_case_resultants_kN":results_input.get("expected_case_resultants_kN",{}),
    }
    v84_in=output_dir/"v8_4"/"input.json";v84_out=output_dir/"v8_4"/"analysis_validation.json";_write(v84_in,v84_payload)
    rc=_run_json(repository,repository/"runners"/STAGES[3][1],v84_in,v84_out,output_dir/"v8_4"/"runner.log")
    if rc!=0 or not v84_out.is_file(): return ChainResult("FAILED",completed,"8.4.0",outputs,[{"reason":"STRUCTURAL_V8_4_EXECUTION_FAILED","message":f"v8.4 stopte met exitcode {rc}."}],[],register)
    register["stages"][3].update({"status":"PASSED","input_source":results_source});outputs.append(_repo_ref(v84_out,repository));completed="8.4.0"

    member_input,member_source=_section(candidates,"member_verification_input",("code_basis","verification_rules","verification_policy"))
    if not member_input:
        from phoenix.autonomy.autonomous_rc_design_candidate_v8_5_r8 import (
            AutonomousRCDesignBlocked,
            derive_rc_design_candidate,
        )
        try:
            v84_for_r8=_read(v84_out)
            v83_for_r8=_read(output_dir/"v8_3"/"input.json")
            r8_policy=_read(repository/"configs"/"phoenix"/"structural"/"autonomous_rc_design_candidate_policy_v8_5_r8.json")
            r8_candidate=derive_rc_design_candidate(
                project_id=project_id,
                analytical_model=analytical_for_solver,
                solver_basis=v83_for_r8.get("solver_basis",{}),
                combination_results=v84_for_r8.get("synthesized_combination_results",{}),
                analysis_validation_state=v84_for_r8.get("validation_state",""),
                policy=r8_policy,
            )
        except AutonomousRCDesignBlocked as exc:
            prerequisite_path=output_dir/"v8_5"/"member_verification_input_requirement.json"
            prerequisite={
                "schema_version":"phoenix.autonomous-rc-design-candidate-blocker/1.0",
                "project_id":project_id,
                "status":"BLOCKED_INPUT",
                "reason":exc.reason,
                "message":exc.message,
                "evidence":exc.evidence,
                "automatic_code_compliance_claim":False,
                "automatic_structural_approval":False,
                "production_release":"LOCKED",
            }
            _write(prerequisite_path,prerequisite)
            outputs.append(_repo_ref(prerequisite_path,repository))
            register["stages"][4]["status"]="BLOCKED_INPUT"
            return _block(exc.reason,exc.message,completed,"8.5.0",outputs,register)

        r8_path=output_dir/"v8_5"/"rc_design_candidate.json"
        _write(r8_path,r8_candidate)
        outputs.append(_repo_ref(r8_path,repository))
        member_input=r8_candidate["member_verification_input"]
        member_source=_repo_ref(r8_path,repository)
    v84=_read(v84_out)
    v85_payload={
        "project_id":project_id,"source_engine":"PHX-STRUCT-ANALYSIS-RESULTS-VALIDATION-V8.4.0",
        "analysis_validation_state":v84.get("validation_state"),"code_basis":member_input["code_basis"],
        "analytical_model":analytical_for_solver,
        "combination_results":v84.get("synthesized_combination_results",{}),
        "verification_rules":member_input["verification_rules"],"verification_policy":member_input["verification_policy"],
    }
    v85_in=output_dir/"v8_5"/"input.json";v85_out=output_dir/"v8_5"/"member_verification.json";_write(v85_in,v85_payload)
    rc=_run_json(repository,repository/"runners"/STAGES[4][1],v85_in,v85_out,output_dir/"v8_5"/"runner.log")
    if rc!=0 or not v85_out.is_file(): return ChainResult("FAILED",completed,"8.5.0",outputs,[{"reason":"STRUCTURAL_V8_5_EXECUTION_FAILED","message":f"v8.5 stopte met exitcode {rc}."}],[],register)
    register["stages"][4].update({"status":"PASSED","input_source":member_source});outputs.append(_repo_ref(v85_out,repository));completed="8.5.0"

    # v8.6-v8.12 require explicit engineering evidence packages. Each stage is
    # wired and executable, but no engineering check values or approvals are fabricated.
    definitions=[
        ("8.6.0","global_stability_input",("stability_basis","stability_checks","stability_policy"),"GLOBAL_STABILITY_ENGINEERING_INPUT_REQUIRED","v8_6","stability_report.json"),
        ("8.7.0","connection_verification_input",("connection_basis","structural_model","verification_checks","verification_policy"),"CONNECTION_SUPPORT_VERIFICATION_INPUT_REQUIRED","v8_7","connection_report.json"),
        ("8.8.0","foundation_interface_input",("foundation_geotechnical_basis","foundation_model","support_foundation_interfaces","verification_checks","verification_policy"),"FOUNDATION_GEOTECHNICAL_INTERFACE_INPUT_REQUIRED","v8_8","foundation_interface_report.json"),
        ("8.9.0","foundation_design_input",("foundation_design_basis","materials","foundation_elements","reinforcement_groups","drawing_details","verification_checks","verification_policy"),"FOUNDATION_DESIGN_REINFORCEMENT_INPUT_REQUIRED","v8_9","foundation_design_report.json"),
        ("8.10.0","engineering_package_input",("engineering_package_basis","qaqc_policy","source_layers","drawings","calculation_sections","verification_registers","assumptions","qaqc_checks","human_engineering_review_gate"),"ENGINEERING_PACKAGE_QAQC_INPUT_REQUIRED","v8_10","engineering_package_qaqc.json"),
        ("8.11.0","engineering_review_release_input",("engineering_package","human_engineering_review","release_authorization","release_policy"),"HUMAN_ENGINEERING_REVIEW_AND_RELEASE_AUTHORIZATION_REQUIRED","v8_11","engineering_review_release.json"),
        ("8.12.0","revision_ifc_input",("revision_policy","baseline_release","current_revision","current_v8_11_release_record","documents"),"REVISION_IFC_PACKAGE_INPUT_REQUIRED","v8_12","revision_ifc_package.json"),
    ]
    prior_outputs={"8.5.0":_read(v85_out)}
    for offset,(version,section_name,required,reason,folder,filename) in enumerate(definitions,start=5):
        section,source=_section(candidates,section_name,required)
        # PHOENIX_R9_GLOBAL_STABILITY_EVIDENCE_V1_0
        if not section and version=="8.6.0":
            _phx_r9=_phoenix_build_r9_global_stability_evidence(
                repository=repository,
                project_id=project_id,
                analytical_model=analytical_for_solver,
                action_load_model=action_load_for_solver,
                analysis_validation=_read(v84_out),
                member_verification=prior_outputs["8.5.0"],
                architecture=arch,
                candidates=candidates,
                v84_evidence_dir=output_dir/"v8_4"/"solver_evidence"/"calculix",
                output_dir=output_dir/"v8_6"/"r9_evidence",
                policy_path=repository/"configs"/"phoenix"/"structural"/"autonomous_global_stability_evidence_policy_r9.json",
            )
            _phx_r9_path=output_dir/"v8_6"/"r9_global_stability_evidence.json"
            _write(_phx_r9_path,_phx_r9)
            outputs.append(_repo_ref(_phx_r9_path,repository))
            if _phx_r9.get("status")=="PASSED" and isinstance(_phx_r9.get("global_stability_input"),dict):
                section=_phx_r9["global_stability_input"]
                source="AUTONOMOUS_GLOBAL_STABILITY_EVIDENCE_R9"
            else:
                # PHOENIX_R9_1_ADVANCED_STABILITY_QUALIFICATION_V1_0
                _phx_r91_solver_manifest_path=output_dir/"v8_3"/"solver_package"/"PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
                _phx_r91_solver_package=_read(_phx_r91_solver_manifest_path) if _phx_r91_solver_manifest_path.is_file() else {}
                _phx_r91=_phoenix_build_r9_1_stability_qualification(
                    repository=repository,
                    project_id=project_id,
                    analytical_model=analytical_for_solver,
                    architecture=arch,
                    solver_package=_phx_r91_solver_package,
                    r9_evidence=_phx_r9,
                    candidates=candidates,
                    v84_evidence_dir=output_dir/"v8_4"/"solver_evidence"/"calculix",
                    output_dir=output_dir/"v8_6"/"r9_1_evidence",
                    policy_path=repository/"configs"/"phoenix"/"structural"/"advanced_global_stability_qualification_policy_r9_1.json",
                )
                _phx_r91_path=output_dir/"v8_6"/"r9_1_global_stability_qualification.json"
                _write(_phx_r91_path,_phx_r91)
                outputs.append(_repo_ref(_phx_r91_path,repository))
                if _phx_r91.get("status")=="PASSED" and isinstance(_phx_r91.get("global_stability_input"),dict):
                    section=_phx_r91["global_stability_input"]
                    source="ADVANCED_GLOBAL_STABILITY_QUALIFICATION_R9_1"
                else:
                    # PHOENIX_R9_2_STABILITY_DESIGN_BASIS_STOREY_COMPLETENESS_RESIDUAL_V1_0
                    _phx_r92_solver_manifest_path=output_dir/"v8_3"/"solver_package"/"PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
                    _phx_r92_solver_package=_read(_phx_r92_solver_manifest_path) if _phx_r92_solver_manifest_path.is_file() else {}
                    _phx_r92=_phoenix_build_r9_2_stability_design_basis_storey_residual(
                        repository=repository,
                        project_id=project_id,
                        analytical_model=analytical_for_solver,
                        architecture=arch,
                        solver_package=_phx_r92_solver_package,
                        analysis_validation=_read(v84_out),
                        r9_evidence=_phx_r9,
                        r91_qualification=_phx_r91,
                        candidates=candidates,
                        policy_path=repository/"configs"/"phoenix"/"structural"/"stability_design_basis_storey_residual_policy_r9_2.json",
                    )
                    _phx_r92_path=output_dir/"v8_6"/"r9_2_stability_design_basis_storey_residual.json"
                    _write(_phx_r92_path,_phx_r92)
                    outputs.append(_repo_ref(_phx_r92_path,repository))
                    if _phx_r92.get("status")=="PASSED" and isinstance(_phx_r92.get("global_stability_input"),dict):
                        section=_phx_r92["global_stability_input"]
                        source="STABILITY_DESIGN_BASIS_STOREY_RESIDUAL_R9_2"
                    else:
                        # PHOENIX_R9_3_RESIDUAL_CAPACITY_STABILITY_DESIGN_BASIS_QUALIFICATION_V1_0
                        _phx_r92_blockers=_phx_r92.get("blockers") or [{"reason":"R9_2_STABILITY_DESIGN_BASIS_OR_RESIDUAL_EVIDENCE_REQUIRED","message":"R9.2 stability design-basis/storey residual evidence is incomplete."}]
                        _phx_r92_primary=_phx_r92_blockers[0]
                        if _phx_r92_primary.get("reason")!="R9_2_STABILITY_DESIGN_BASIS_OR_RESIDUAL_EVIDENCE_REQUIRED":
                            _phx_r92_template=workspace/"inputs"/"structural"/"global_stability_engineering_input_REQUIRED.json"
                            _write(_phx_r92_template,_phx_r92.get("required_input_template") or _phx_r91.get("required_input_template") or _phx_r9.get("required_input_template") or {})
                            outputs.append(_repo_ref(_phx_r92_template,repository))
                            register["stages"][offset]["status"]="BLOCKED_INPUT"
                            return _block(
                                _phx_r92_primary.get("reason") or "R9_2_STABILITY_DESIGN_BASIS_OR_RESIDUAL_EVIDENCE_REQUIRED",
                                _phx_r92_primary.get("message") or "R9.2 stability design-basis/storey residual evidence is incomplete.",
                                completed,version,outputs,register,_phx_r92_primary
                            )
                        _phx_r93_rc_path=output_dir/"v8_5"/"rc_design_candidate.json"
                        _phx_r93_mv_path=output_dir/"v8_5"/"member_verification.json"
                        _phx_r93_rc=_read(_phx_r93_rc_path) if _phx_r93_rc_path.is_file() else {}
                        _phx_r93_mv=_read(_phx_r93_mv_path) if _phx_r93_mv_path.is_file() else {}
                        _phx_r93=_phoenix_build_r9_3_residual_capacity_stability_design_basis(
                            project_id=project_id,
                            r91_qualification=_phx_r91,
                            r92_qualification=_phx_r92,
                            rc_design_candidate=_phx_r93_rc,
                            member_verification=_phx_r93_mv,
                            candidates=candidates,
                            policy_path=repository/"configs"/"phoenix"/"structural"/"residual_capacity_stability_design_basis_policy_r9_3.json",
                        )
                        _phx_r93_path=output_dir/"v8_6"/"r9_3_residual_capacity_stability_design_basis.json"
                        _write(_phx_r93_path,_phx_r93)
                        outputs.append(_repo_ref(_phx_r93_path,repository))
                        if _phx_r93.get("status")=="PASSED" and isinstance(_phx_r93.get("global_stability_input"),dict):
                            section=_phx_r93["global_stability_input"]
                            source="RESIDUAL_CAPACITY_STABILITY_DESIGN_BASIS_R9_3"
                        else:
                            # PHOENIX_R9_4_NORMATIVE_APPLICABILITY_STABILITY_DESIGN_BASIS_QUALIFICATION_V1_0
                            _phx_r93_blockers=_phx_r93.get("blockers") or [{"reason":"R9_3_STABILITY_DESIGN_BASIS_QUALIFICATION_REQUIRED","message":"R9.3 residual-capacity/stability design-basis qualification is incomplete."}]
                            _phx_r93_primary=_phx_r93_blockers[0]
                            if _phx_r93_primary.get("reason")!="R9_3_STABILITY_DESIGN_BASIS_QUALIFICATION_REQUIRED":
                                _phx_r93_template=workspace/"inputs"/"structural"/"global_stability_engineering_input_REQUIRED.json"
                                _write(_phx_r93_template,_phx_r93.get("required_input_template") or _phx_r92.get("required_input_template") or {})
                                outputs.append(_repo_ref(_phx_r93_template,repository))
                                register["stages"][offset]["status"]="BLOCKED_INPUT"
                                return _block(
                                    _phx_r93_primary.get("reason") or "R9_3_STABILITY_DESIGN_BASIS_QUALIFICATION_REQUIRED",
                                    _phx_r93_primary.get("message") or "R9.3 residual-capacity/stability design-basis qualification is incomplete.",
                                    completed,version,outputs,register,_phx_r93_primary
                                )
                            _phx_r94=_phoenix_build_r9_4_normative_applicability_stability_design_basis(
                                project_id=project_id,
                                r93_qualification=_phx_r93,
                                candidates=candidates,
                                policy_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_stability_design_basis_policy_r9_4.json",
                                source_registry_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_public_source_registry_r9_4.json",
                            )
                            _phx_r94_path=output_dir/"v8_6"/"r9_4_normative_applicability_stability_design_basis.json"
                            _write(_phx_r94_path,_phx_r94)
                            outputs.append(_repo_ref(_phx_r94_path,repository))
                            if _phx_r94.get("status")=="PASSED" and isinstance(_phx_r94.get("global_stability_input"),dict):
                                section=_phx_r94["global_stability_input"]
                                source="NORMATIVE_APPLICABILITY_STABILITY_DESIGN_BASIS_R9_4"
                            else:
                                # PHOENIX_R9_5_PROJECT_STABILITY_DESIGN_BASIS_DECISION_LICENSED_SOURCE_QUALIFICATION_V1_0
                                _phx_r94_blockers=_phx_r94.get("blockers") or [{"reason":"R9_4_NORMATIVE_APPLICABILITY_OR_DESIGN_BASIS_INPUT_REQUIRED","message":"R9.4 normative applicability/stability design-basis qualification is incomplete."}]
                                _phx_r94_primary=_phx_r94_blockers[0]
                                if _phx_r94_primary.get("reason")!="R9_4_NORMATIVE_APPLICABILITY_OR_DESIGN_BASIS_INPUT_REQUIRED":
                                    _phx_r94_template=workspace/"inputs"/"structural"/"global_stability_engineering_input_REQUIRED.json"
                                    _write(_phx_r94_template,_phx_r94.get("required_input_template") or _phx_r93.get("required_input_template") or {})
                                    outputs.append(_repo_ref(_phx_r94_template,repository))
                                    register["stages"][offset]["status"]="BLOCKED_INPUT"
                                    return _block(
                                        _phx_r94_primary.get("reason") or "R9_4_NORMATIVE_APPLICABILITY_OR_DESIGN_BASIS_INPUT_REQUIRED",
                                        _phx_r94_primary.get("message") or "R9.4 normative applicability/stability design-basis qualification is incomplete.",
                                        completed,version,outputs,register,_phx_r94_primary
                                    )
                                _phx_r9522_pre=_phoenix_apply_r9_5_2_2_ab_policy_to_workspace(workspace=workspace,policy_path=repository/"configs"/"phoenix"/"structural"/"stability_ab_project_policy_r9_5_2_2.json")  # PHOENIX_R9_5_2_2_AB_PROJECT_POLICY_PRE_R9_5_V1_1
                                _phx_r95=_phoenix_build_r9_5_project_stability_design_basis_decision(
                                    project_id=project_id,
                                    r93_qualification=_phx_r93,
                                    r94_initial=_phx_r94,
                                    candidates=candidates,
                                    policy_path=repository/"configs"/"phoenix"/"structural"/"project_stability_design_basis_decision_policy_r9_5.json",
                                    suriname_rule_registry_path=repository/"configs"/"phoenix"/"jurisdictions"/"suriname"/"suriname_structural_rule_registry_v1_0.json",
                                    suriname_source_registry_path=repository/"outputs"/"bib"/"index"/"suriname_regulatory_source_registry_v1_0.json",
                                    r94_policy_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_stability_design_basis_policy_r9_4.json",
                                    r94_public_source_registry_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_public_source_registry_r9_4.json",
                                    repository_root=repository,
                                )
                                _phx_r95_path=output_dir/"v8_6"/"r9_5_project_stability_design_basis_decision.json"
                                _write(_phx_r95_path,_phx_r95)
                                outputs.append(_repo_ref(_phx_r95_path,repository))
                                if _phx_r95.get("status")=="PASSED" and isinstance(_phx_r95.get("global_stability_input"),dict):
                                    section=_phx_r95["global_stability_input"]
                                    source="PROJECT_STABILITY_DESIGN_BASIS_DECISION_R9_5"
                                else:
                                    # PHOENIX_R9_5_1_PROJECT_STABILITY_DESIGN_BASIS_INPUT_EVIDENCE_QUALIFICATION_V1_0
                                    _phx_r951=_phoenix_build_r9_5_1_project_stability_design_basis_input_evidence_qualification(
                                        project_id=project_id,
                                        r95_result=_phx_r95,
                                        policy_path=repository/"configs"/"phoenix"/"structural"/"project_stability_design_basis_input_evidence_qualification_policy_r9_5_1.json",
                                    )
                                    _phx_r951_path=output_dir/"v8_6"/"r9_5_1_project_stability_design_basis_input_evidence_qualification.json"
                                    _write(_phx_r951_path,_phx_r951)
                                    outputs.append(_repo_ref(_phx_r951_path,repository))
                                    _phx_r95_template=workspace/"inputs"/"structural"/"global_stability_engineering_input_REQUIRED.json"
                                    _write(
                                        _phx_r95_template,
                                        _phx_r951.get("prefilled_project_input")
                                        or _phx_r95.get("required_input_template")
                                        or _phx_r94.get("required_input_template")
                                        or {},
                                    )
                                    outputs.append(_repo_ref(_phx_r95_template,repository))
                                    register["stages"][offset]["status"]="BLOCKED_INPUT"
                                    # PHOENIX_R9_5_2_STABILITY_DESIGN_BASIS_DECISION_DOSSIER_EVIDENCE_INTAKE_V1_0
                                    _phx_r952_intake_path=workspace/"inputs"/"structural"/"stability_design_basis_evidence_intake_REQUIRED.json"
                                    _phx_r952_existing_intake=_read(_phx_r952_intake_path) if _phx_r952_intake_path.is_file() else {}
                                    _phx_r952=_phoenix_build_r9_5_2_stability_design_basis_decision_dossier_evidence_intake(
                                        project_id=project_id,
                                        r951_result=_phx_r951,
                                        policy_path=repository/"configs"/"phoenix"/"structural"/"stability_design_basis_decision_dossier_evidence_intake_policy_r9_5_2.json",
                                        existing_intake=_phx_r952_existing_intake,
                                    )
                                    _phx_r952=_phoenix_apply_r9_5_2_2_ab_policy_to_r9_5_2_result(r952_result=_phx_r952,policy_path=repository/"configs"/"phoenix"/"structural"/"stability_ab_project_policy_r9_5_2_2.json")  # PHOENIX_R9_5_2_2_AB_PROJECT_POLICY_POST_R9_5_2_V1_1
                                    _phx_r9522_request_path=workspace/"inputs"/"structural"/"licensed_ec2_clause_extract_REQUIRED.md"
                                    _phx_r9522_request_path.parent.mkdir(parents=True,exist_ok=True)
                                    _phx_r9522_request_path.write_text(_phoenix_render_r9_5_2_2_licensed_clause_extract_request(_phx_r952),encoding='utf-8')
                                    outputs.append(_repo_ref(_phx_r9522_request_path,repository))
                                    _phx_r952_path=output_dir/"v8_6"/"r9_5_2_stability_design_basis_decision_dossier_evidence_intake.json"
                                    _write(_phx_r952_path,_phx_r952)
                                    outputs.append(_repo_ref(_phx_r952_path,repository))
                                    _write(_phx_r952_intake_path,_phx_r952.get("evidence_intake") or {})
                                    outputs.append(_repo_ref(_phx_r952_intake_path,repository))
                                    _phx_r952_dossier_path=workspace/"inputs"/"structural"/"stability_design_basis_decision_dossier_REQUIRED.md"
                                    _phx_r952_dossier_path.parent.mkdir(parents=True,exist_ok=True)
                                    _phx_r952_dossier_path.write_text(_phoenix_render_r9_5_2_decision_dossier_markdown(_phx_r952),encoding='utf-8')
                                    outputs.append(_repo_ref(_phx_r952_dossier_path,repository))
                                    # PHOENIX_R9_5_2_4_RUNTIME_INPUT_MERGE_R9_5_REQUALIFICATION_V1_0
                                    _phx_r9524=_phoenix_build_r9_5_2_4_runtime_input_merge_r9_5_requalification(
                                        project_id=project_id,
                                        workspace=workspace,
                                        repository_root=repository,
                                        r93_qualification=_phx_r93,
                                        r94_initial=_phx_r94,
                                        r95_initial=_phx_r95,
                                        r951_initial=_phx_r951,
                                        r952_initial=_phx_r952,
                                        r95_policy_path=repository/"configs"/"phoenix"/"structural"/"project_stability_design_basis_decision_policy_r9_5.json",
                                        r951_policy_path=repository/"configs"/"phoenix"/"structural"/"project_stability_design_basis_input_evidence_qualification_policy_r9_5_1.json",
                                        r952_policy_path=repository/"configs"/"phoenix"/"structural"/"stability_design_basis_decision_dossier_evidence_intake_policy_r9_5_2.json",
                                        ab_policy_path=repository.joinpath("configs","phoenix","structural","stability_ab_project_policy_r9_5_2_2.json"),
                                        package_b_registry_path=repository/"configs"/"phoenix"/"structural"/"package_b_licensed_source_traceability_r9_5_2_3.json",
                                        suriname_rule_registry_path=repository/"configs"/"phoenix"/"jurisdictions"/"suriname"/"suriname_structural_rule_registry_v1_0.json",
                                        suriname_source_registry_path=repository/"outputs"/"bib"/"index"/"suriname_regulatory_source_registry_v1_0.json",
                                        r94_policy_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_stability_design_basis_policy_r9_4.json",
                                        r94_public_source_registry_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_public_source_registry_r9_4.json",
                                    )
                                    _phx_r9524_path=output_dir/"v8_6"/"r9_5_2_4_runtime_input_merge_r9_5_requalification.json"
                                    _write(_phx_r9524_path,_phx_r9524)
                                    outputs.append(_repo_ref(_phx_r9524_path,repository))
                                    _phx_r95_requalified=_phx_r9524.get('r9_5_requalified') or _phx_r95
                                    _write(_phx_r95_path,_phx_r95_requalified)
                                    _phx_r951_requalified=_phx_r9524.get('r9_5_1_requalified')
                                    if isinstance(_phx_r951_requalified,dict):
                                        _write(_phx_r951_path,_phx_r951_requalified)
                                    _phx_r952_requalified=_phx_r9524.get('r9_5_2_requalified')
                                    if isinstance(_phx_r952_requalified,dict):
                                        _phx_r952=_phx_r952_requalified
                                        _write(_phx_r952_path,_phx_r952)
                                        _write(_phx_r952_intake_path,_phx_r952.get('evidence_intake') or {})
                                        _phx_r952_dossier_path.write_text(_phoenix_render_r9_5_2_decision_dossier_markdown(_phx_r952),encoding='utf-8')
                                    if _phx_r9524.get('status')=='PASSED' and isinstance(_phx_r95_requalified.get('global_stability_input'),dict):
                                        _phx_r95=_phx_r95_requalified
                                        section=_phx_r95['global_stability_input']
                                        source="PROJECT_STABILITY_DESIGN_BASIS_DECISION_R9_5_2_4_REQUALIFIED"
                                    else:
                                        # PHOENIX_R9_5_2_5_PACKAGE_E_ALTERNATE_PATH_INDEPENDENT_EVIDENCE_V1_0
                                        _phoenix_r9_5_2_9_intake = _phoenix_run_combined_cde_evidence_intake_r9_5_2_9(locals())
                                        _phx_r9525=_phoenix_build_r9_5_2_5_package_e_alternate_path_independent_evidence(
                                            project_id=project_id,
                                            workspace=workspace,
                                            repository_root=repository,
                                            r93_qualification=_phx_r93,
                                            r94_initial=_phx_r94,
                                            r9524_result=_phx_r9524,
                                            r952_result=_phx_r952,
                                            r95_policy_path=repository/"configs"/"phoenix"/"structural"/"project_stability_design_basis_decision_policy_r9_5.json",
                                            package_e_policy_path=repository/"configs"/"phoenix"/"structural"/"package_e_alternate_path_independent_evidence_policy_r9_5_2_5.json",
                                            suriname_rule_registry_path=repository/"configs"/"phoenix"/"jurisdictions"/"suriname"/"suriname_structural_rule_registry_v1_0.json",
                                            suriname_source_registry_path=repository/"outputs"/"bib"/"index"/"suriname_regulatory_source_registry_v1_0.json",
                                            r94_policy_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_stability_design_basis_policy_r9_4.json",
                                            r94_public_source_registry_path=repository/"configs"/"phoenix"/"structural"/"normative_applicability_public_source_registry_r9_4.json",
                                        )
                                        _phx_r9525_path=output_dir/"v8_6"/"r9_5_2_5_package_e_alternate_path_independent_evidence.json"
                                        _write(_phx_r9525_path,_phx_r9525)
                                        outputs.append(_repo_ref(_phx_r9525_path,repository))
                                        _phx_r9525_dossier_path=output_dir/"v8_6"/"r9_5_2_5_package_e_alternate_path_independent_evidence.md"
                                        _phx_r9525_dossier_path.write_text(_phoenix_render_r9_5_2_5_package_e_dossier_markdown(_phx_r9525),encoding='utf-8')
                                        _phoenix_package_c_r9_5_2_6 = _phoenix_run_package_c_seismic_scope_criteria_r9_5_2_6(locals())
                                        _phoenix_package_d_r9_5_2_7 = _phoenix_run_package_d_weak_storey_screening_review_r9_5_2_7(locals())
                                        _phoenix_r9_5_2_8 = _phoenix_run_remaining_evidence_gate_consolidation_r9_5_2_8(locals(), requalification_callable=_phoenix_build_r9_5_2_4_runtime_input_merge_r9_5_requalification)
                                        outputs.append(_repo_ref(_phx_r9525_dossier_path,repository))
                                        _phx_r95_e=_phx_r9525.get('r9_5_requalified')
                                        if isinstance(_phx_r95_e,dict):
                                            _write(_phx_r95_path,_phx_r95_e)
                                        _phx_r952_e=_phx_r9525.get('r9_5_2_requalified')
                                        if isinstance(_phx_r952_e,dict):
                                            _phx_r952=_phx_r952_e
                                            _write(_phx_r952_path,_phx_r952)
                                            _write(_phx_r952_intake_path,_phx_r952.get('evidence_intake') or {})
                                            _phx_r952_dossier_path.write_text(_phoenix_render_r9_5_2_decision_dossier_markdown(_phx_r952),encoding='utf-8')
                                        register["stages"][offset]["status"]="BLOCKED_INPUT"
                                        _phx_r9525_blockers=_phx_r9525.get("blockers") or [{"reason":"R9_5_2_5_PACKAGE_E_OR_REMAINING_INPUT_REQUIRED","message":"R9.5.2.5 Package E or remaining stability input is required."}]
                                        _phx_r9525_primary=_phx_r9525_blockers[0]
                                        return _block(
                                            _phx_r9525_primary.get("reason") or "R9_5_2_5_PACKAGE_E_OR_REMAINING_INPUT_REQUIRED",
                                            _phx_r9525_primary.get("message") or "R9.5.2.5 Package E or remaining stability input is required.",
                                            completed,version,outputs,register,_phx_r9525_primary
                                        )
        if not section:
            register["stages"][offset]["status"]="BLOCKED_INPUT"
            message={
                "8.6.0":"Expliciete globale stabiliteits-/tweede-orde-/robuustheidscontroles zijn vereist.",
                "8.7.0":"Expliciete verbinding-, oplegging- en joint-verificatiegegevens zijn vereist.",
                "8.8.0":"Projectspecifieke geotechnische/funderingsinterfacegegevens zijn vereist.",
                "8.9.0":"Projectspecifiek funderingsontwerp, wapening en verificatie-evidence zijn vereist.",
                "8.10.0":"Compleet engineering package en QA/QC-evidence zijn vereist.",
                "8.11.0":"Echte menselijke engineering review en release-autorisatie zijn vereist.",
                "8.12.0":"Revisie-, release-record- en IFC-documentcontrolgegevens zijn vereist.",
            }[version]
            return _block(reason,message,completed,version,outputs,register)

        payload=dict(section)
        payload["project_id"]=project_id
        if version=="8.6.0":
            payload.setdefault("source_engine","PHX-STRUCT-CODE-LIMIT-STATE-MEMBER-VERIFICATION-V8.5.0")
            payload.setdefault("member_verification_state",prior_outputs["8.5.0"].get("verification_state"))
            payload.setdefault("analytical_model",{
                "nodes":analytical_for_solver.get("nodes",[]),
                "supports":analytical_for_solver.get("supports",[]),
                "storeys":[{"id":s.get("storey_id"),"elevation_m":s.get("elevation_m"),"height_m":s.get("height_m")} for s in arch.get("storeys",[])],
            })
        elif version=="8.7.0":
            payload.setdefault("source_engine","PHX-STRUCT-GLOBAL-STABILITY-SECOND-ORDER-ROBUSTNESS-V8.6.0")
            payload.setdefault("global_stability_state",prior_outputs["8.6.0"].get("verification_state"))
        elif version=="8.8.0":
            payload.setdefault("source_engine","PHX-STRUCT-CONNECTION-SUPPORT-JOINT-VERIFICATION-V8.7.0")
            payload.setdefault("connection_support_joint_state",prior_outputs["8.7.0"].get("verification_state"))
        elif version=="8.9.0":
            payload.setdefault("source_engine","PHX-STRUCT-FOUNDATION-INTERFACE-SOIL-SUPPORT-VERIFICATION-V8.8.0")
            payload.setdefault("foundation_interface_soil_support_state",prior_outputs["8.8.0"].get("verification_state"))
        elif version=="8.10.0":
            payload.setdefault("source_engine","PHX-STRUCT-FOUNDATION-DESIGN-REINFORCEMENT-DETAILING-V8.9.0")
            payload.setdefault("foundation_design_reinforcement_detailing_state",prior_outputs["8.9.0"].get("verification_state"))
        elif version=="8.11.0":
            payload.setdefault("source_engine","PHX-STRUCT-DRAWING-CALC-PACKAGE-ENGINEERING-QAQC-V8.10.0")
            payload.setdefault("engineering_package_qaqc_state",prior_outputs["8.10.0"].get("verification_state"))
        elif version=="8.12.0":
            payload.setdefault("source_engine","PHX-STRUCT-ENGINEERING-REVIEW-APPROVAL-RELEASE-CONTROL-V8.11.0")

        inp=output_dir/folder/"input.json";outp=output_dir/folder/filename;_write(inp,payload)
        rc=_run_json(repository,repository/"runners"/STAGES[offset][1],inp,outp,output_dir/folder/"runner.log")
        if rc!=0 or not outp.is_file():
            return ChainResult("FAILED",completed,version,outputs,[{"reason":f"STRUCTURAL_V{version.replace('.','_')}_EXECUTION_FAILED","message":f"v{version} stopte met exitcode {rc}."}],[],register)
        value=_read(outp);prior_outputs[version]=value
        register["stages"][offset].update({"status":"PASSED","input_source":source});outputs.append(_repo_ref(outp,repository));completed=version

    return ChainResult("PASSED","8.12.0",None,outputs,[],[],register)
