"""Phoenix Structural v8.1-v8.12 Validated Session Chain v1.0.

The chain removes the generic cross-version mapping blocker, but never invents:
design actions, code basis, solver properties, analysis results, capacity checks,
stability checks, connection checks, geotechnical data, foundation design,
professional review or release authorization.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .local_material_supply_intelligence import selected_engineering_material_ids
from .structural_action_load_basis import build_structural_action_load_basis

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

    material_selection={}
    if material_selection_path is not None and material_selection_path.is_file():
        try:
            material_selection=_read(material_selection_path)
        except Exception:
            material_selection={}
    if not material_selection.get("all_structural_requirements_engineering_qualified",False):
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block(
            "LOCAL_STRUCTURAL_MATERIAL_AVAILABILITY_REQUIRED",
            "v8.2 kan zijn afgerond, maar vóór solvermateriaalgebruik moeten constructieve producten lokaal of via import beschikbaar, gecertificeerd en technisch engineering-gekwalificeerd zijn.",
            completed,"8.3.0",outputs,register,
            {"material_selection":_repo_ref(material_selection_path,repository) if material_selection_path else None}
        )

    solver_input,solver_source=_section(candidates,"structural_analysis_basis",("solver_basis","element_assignments","solver_adapters","execution_policy"))
    if not solver_input:
        tp=workspace/"inputs"/"structural"/"structural_analysis_basis_REQUIRED.json"
        _write(tp,{
            "schema_version":"phoenix.structural-analysis-basis-template/1.0",
            "structural_analysis_basis":{
                "solver_basis":{"basis":"EXPLICIT_REQUIRED","analysis_type":"LINEAR_STATIC","materials":{},"sections":{}},
                "element_assignments":{"by_id":{},"by_type":{}},
                "solver_adapters":["opensees","calculix"],
                "execution_policy":{"allow_execution":False,"require_explicit_cli_opt_in":True},
            },
            "note":"Materiaalstijfheden, doorsneden en solveruitvoering worden niet door Phoenix verzonnen."
        });outputs.append(_repo_ref(tp,repository))
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block("STRUCTURAL_SOLVER_BASIS_AND_ELEMENT_ASSIGNMENTS_REQUIRED","Expliciete solverbasis, materialen, doorsneden en elementtoewijzingen zijn vereist voor v8.3.",completed,"8.3.0",outputs,register)

    qualified_engineering_ids=selected_engineering_material_ids(material_selection)
    solver_materials=set(str(x) for x in (solver_input.get("solver_basis") or {}).get("materials",{}).keys())
    unconfirmed_solver_materials=sorted(x for x in solver_materials if x not in qualified_engineering_ids)
    if unconfirmed_solver_materials:
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block(
            "STRUCTURAL_SOLVER_MATERIAL_NOT_LOCALLY_CONFIRMED",
            "Solverbasis verwijst naar materialen die niet als geselecteerde, leverbare en engineering-gekwalificeerde materialen zijn bevestigd; de legacy reason-code blijft behouden voor compatibiliteit.",
            completed,"8.3.0",outputs,register,
            {"unconfirmed_material_ids":unconfirmed_solver_materials}
        )

    analytical_for_solver,missing_assignments=_apply_assignments(_read(v81_out),solver_input)
    if missing_assignments:
        register["stages"][2]["status"]="BLOCKED_INPUT"
        return _block("STRUCTURAL_SOLVER_ELEMENT_ASSIGNMENTS_INCOMPLETE","Niet alle analytische elementen hebben expliciete material_id en section_id.",completed,"8.3.0",outputs,register,{"missing_element_ids":missing_assignments[:50]})

    v83_payload={
        "project_id":project_id,
        "analytical_model":analytical_for_solver,
        "solver_basis":solver_input["solver_basis"],
        "action_load_model":_read(v82_out),
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
        "analytical_model":analytical_for_solver,"action_load_model":_read(v82_out),
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
        register["stages"][4]["status"]="BLOCKED_INPUT"
        return _block("STRUCTURAL_CODE_BASIS_AND_MEMBER_VERIFICATION_RULES_REQUIRED","Expliciete codebasis en member-verification regels zijn vereist voor v8.5.",completed,"8.5.0",outputs,register)
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
