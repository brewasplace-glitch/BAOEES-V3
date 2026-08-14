"""PAT-001 OpenSees live execution, raw evidence, normalization and adapter qualification v1.0."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import argparse, hashlib, json, os, re, shutil, subprocess

VERSION="1.0.1"
ENGINE_ID="PHX-PAT001-OPENSEES-LIVE-EVIDENCE"
PROJECT_ID="PHOENIX-PAT-001"
ADAPTER_ID="PAT001-OPENSEES-LIVE-PROJECT-ADAPTER-v1"
READY="PAT001_OPENSEES_READY_LIVE_EXECUTION_OPT_IN_REQUIRED"
NO_EXE="BLOCKED_OPENSEES_EXECUTABLE_NOT_FOUND"
PROBE_FAIL="BLOCKED_OPENSEES_ENVIRONMENT_PROBE_FAILED"
EXEC_FAIL="BLOCKED_OPENSEES_PROJECT_EXECUTION_FAILED"
NORM_FAIL="BLOCKED_OPENSEES_NORMALIZATION_INCOMPLETE"
QUALIFIED="PAT001_OPENSEES_LIVE_EXECUTION_NORMALIZED_ADAPTER_QUALIFIED"
SAFETY={"source_v8_3_decks_overwritten":False,"live_execution_without_explicit_opt_in":False,"golden_reference_used_as_pat001_evidence":False,"automatic_professional_approval":False,"automatic_code_compliance_claim":False,"independent_verification_claimed":False,"production_release":"LOCKED","for_construction_release":"LOCKED","scia_gap_changed":False}

MEMBER=re.compile(r"^\s*element\s+(?!ShellMITC4\b)\S+\s+(?P<tag>\d+)\b.*?;#\s*(?P<id>M\S+)\s*$",re.I)
SHELL=re.compile(r"^\s*element\s+ShellMITC4\s+(?P<tag>\d+)\b(?P<rest>.*?);#\s*(?P<id>S\S+)\s*$",re.I)
NODE=re.compile(r"^PHX_NODE\s+(?P<id>\S+)\s+DISP\s+(?P<disp>.*?)\s+REACTION\s+(?P<reaction>.*?)\s*$")
EL=re.compile(r"^PHX_ELEMENT_(?P<kind>FORCE|STRESS)\s+(?P<etype>MEMBER|SHELL)\s+(?P<id>\S+)\s+TAG\s+(?P<tag>\d+)\s+VALUES\s+\{(?P<values>.*)\}\s*$")
LOAD=re.compile(r"^\s*load\s+\d+\s+(?P<fx>[-+0-9.eE]+)\s+(?P<fy>[-+0-9.eE]+)\s+(?P<fz>[-+0-9.eE]+)\b.*?;#\s*(?P<id>\S+)\s*$",re.I)

def now(): return datetime.now(timezone.utc).isoformat()
def rj(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding="utf-8-sig"))
    if not isinstance(v,dict): raise ValueError(f"JSON object required: {p}")
    return v
def wj(p:Path,v:Any):
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def rr(p:Path,repo:Path)->str:
    try:return p.resolve().relative_to(repo.resolve()).as_posix()
    except:return str(p.resolve())
def nums(s:str)->list[float]:
    out=[]
    for x in s.replace("{"," ").replace("}"," ").split():
        try:out.append(float(x))
        except ValueError:pass
    return out

def solver_console_output(stdout:str|None,stderr:str|None)->str:
    """Combine OpenSees console streams for semantic parsing while raw streams remain separate."""
    parts=[]
    if stdout: parts.append(stdout)
    if stderr: parts.append(stderr)
    return "\n".join(parts)

def marker_streams(marker:str,stdout:str|None,stderr:str|None)->dict[str,bool]:
    return {
        "stdout": marker in (stdout or ""),
        "stderr": marker in (stderr or ""),
    }

def discover_executable(explicit:str|None=None)->dict[str,Any]:
    c=[]
    if explicit:c.append(("EXPLICIT_ARGUMENT",explicit))
    if os.environ.get("OPENSEES_EXE"):c.append(("ENV_OPENSEES_EXE",os.environ["OPENSEES_EXE"]))
    if os.environ.get("OPENSEES_HOME"):
        h=Path(os.environ["OPENSEES_HOME"]); c += [("ENV_OPENSEES_HOME",str(h/"OpenSees.exe")),("ENV_OPENSEES_HOME",str(h/"bin/OpenSees.exe"))]
    for q in ("OpenSees.exe","OpenSees"):
        x=shutil.which(q)
        if x:c.append(("PATH",x))
    if os.name=="nt": c += [("COMMON_PATH",x) for x in (r"C:\OpenSees\OpenSees.exe",r"C:\OpenSees\bin\OpenSees.exe",r"C:\Program Files\OpenSees\OpenSees.exe",r"C:\Program Files\OpenSees\bin\OpenSees.exe",r"C:\Program Files (x86)\OpenSees\OpenSees.exe")]
    seen=set(); checked=[]
    for source,raw in c:
        p=Path(os.path.abspath(os.path.expandvars(os.path.expanduser(raw)))); k=str(p).lower() if os.name=="nt" else str(p)
        if k in seen:continue
        seen.add(k); checked.append({"source":source,"candidate":str(p),"exists":p.is_file()})
        if p.is_file():return {"status":"OPENSEES_EXECUTABLE_DISCOVERED","path":str(p.resolve()),"sha256":sha(p),"source":source,"checked":checked}
    return {"status":NO_EXE,"path":None,"sha256":None,"source":None,"checked":checked}

def tag_maps(text:str)->dict[str,Any]:
    m={};s={}
    for line in text.splitlines():
        a=MEMBER.match(line); b=SHELL.match(line)
        if a:m[a.group("id")]=int(a.group("tag"))
        elif b:s[b.group("id")]=int(b.group("tag"))
    collisions=sorted(set(m.values())&set(s.values()))
    sx={k:(max(m.values(),default=0)+i if collisions else v) for i,(k,v) in enumerate(sorted(s.items()),1)}
    allv=list(m.values())+list(sx.values())
    if len(allv)!=len(set(allv)):raise ValueError("OpenSees element tags remain non-unique.")
    return {"source_member_tags":m,"source_shell_tags":s,"execution_member_tags":dict(m),"execution_shell_tags":sx,"source_collisions":collisions,"repair_applied":bool(collisions),"repair_method":"DETERMINISTIC_OFFSET_AFTER_MAX_MEMBER_TAG" if collisions else "NOT_REQUIRED"}

def harden_deck(text:str)->tuple[str,dict[str,Any]]:
    t=tag_maps(text); out=[]; patched=0; reactions=False
    for line in text.splitlines():
        b=SHELL.match(line)
        if b:
            sid=b.group("id"); pre=line[:len(line)-len(line.lstrip())]
            line=f"{pre}element ShellMITC4 {t['execution_shell_tags'][sid]}{b.group('rest')} ;# {sid}"; patched+=1
        if not reactions and 'puts "PHX_NODE ' in line: out.append("reactions"); reactions=True
        out.append(line)
    if t["source_shell_tags"] and patched!=len(t["source_shell_tags"]):raise ValueError("Shell patch incomplete.")
    if not reactions:raise ValueError("PHX_NODE capture not found.")
    out += ["","# PHOENIX OPENSEES RAW EVIDENCE HARDENING v1.0"]
    def add(kind,i,tag):
        out.extend(["set phx_force {}",
        f"if {{[catch {{set phx_force [eleResponse {tag} force]}} e1]}} {{ if {{[catch {{set phx_force [eleResponse {tag} forces]}} e2]}} {{ set phx_force {{}} }} }}",
        f'puts "PHX_ELEMENT_FORCE {kind} {i} TAG {tag} VALUES {{$phx_force}}"',
        "set phx_stress {}",
        f"if {{[catch {{set phx_stress [eleResponse {tag} stresses]}} e3]}} {{ if {{[catch {{set phx_stress [eleResponse {tag} stress]}} e4]}} {{ set phx_stress {{}} }} }}",
        f'puts "PHX_ELEMENT_STRESS {kind} {i} TAG {tag} VALUES {{$phx_stress}}"'])
    for i,tag in sorted(t["execution_member_tags"].items()):add("MEMBER",i,tag)
    for i,tag in sorted(t["execution_shell_tags"].items()):add("SHELL",i,tag)
    out.append('puts "PHOENIX_EVIDENCE_CAPTURE_OK"')
    hardened="\n".join(out)+"\n"
    q=tag_maps(hardened); vals=list(q["execution_member_tags"].values())+list(q["execution_shell_tags"].values())
    if len(vals)!=len(set(vals)):raise ValueError("Hardened tags are not unique.")
    t.update({"shell_declarations_patched":patched,"reaction_command_inserted":reactions,"globally_unique_execution_element_tags":True})
    return hardened,t

def applied(text:str)->list[float]:
    total=[0.0,0.0,0.0]
    for line in text.splitlines():
        m=LOAD.match(line)
        if m:
            for i,k in enumerate(("fx","fy","fz")):total[i]+=float(m.group(k))
    return total

def normalize(stdout:str,expected_nodes:Iterable[str],tags:dict[str,Any],deck:str)->dict[str,Any]:
    nodes={}; elements={}; ids=sorted(expected_nodes); nt={x:i+1 for i,x in enumerate(ids)}
    for raw in stdout.splitlines():
        line=raw.strip(); n=NODE.match(line)
        if n:
            i=n.group("id"); nodes[i]={"phoenix_node_id":i,"solver_native_tag":nt.get(i),"displacement":nums(n.group("disp")),"reaction":nums(n.group("reaction"))}; continue
        e=EL.match(line)
        if e:
            i=e.group("id"); rec=elements.setdefault(i,{"phoenix_element_id":i,"element_type":e.group("etype"),"solver_native_tag":int(e.group("tag")),"force":[],"stress":[]}); rec[e.group("kind").lower()]=nums(e.group("values"))
    exp=set(ids); obs=set(nodes); missing=sorted(exp-obs); unexpected=sorted(obs-exp)
    idisp=sorted(i for i in exp&obs if not nodes[i]["displacement"]); ireact=sorted(i for i in exp&obs if not nodes[i]["reaction"])
    for i,tag in tags["execution_member_tags"].items():elements.setdefault(i,{"phoenix_element_id":i,"element_type":"MEMBER","solver_native_tag":tag,"force":[],"stress":[]})
    for i,tag in tags["execution_shell_tags"].items():elements.setdefault(i,{"phoenix_element_id":i,"element_type":"SHELL","solver_native_tag":tag,"force":[],"stress":[]})
    rs=[0.0,0.0,0.0]
    for n in nodes.values():
        for j,v in enumerate((n["reaction"] or [])[:3]):rs[j]+=v
    ld=applied(deck); residual=[ld[i]+rs[i] for i in range(3)]
    complete=not(missing or unexpected or idisp or ireact)
    return {"schema_version":"phoenix.opensees-normalized-results/1.0","solver":"OpenSees","normalization_status":"COMPLETE" if complete else "INCOMPLETE","technical_state":"CALCULATED_UNVERIFIED" if complete else "UNQUALIFIED","node_results":nodes,"element_results":elements,"coverage":{"expected_node_count":len(exp),"observed_node_count":len(obs),"missing_nodes":missing,"unexpected_nodes":unexpected,"incomplete_displacements":idisp,"incomplete_reactions":ireact,"expected_element_count":len(elements),"element_force_response_count":sum(bool(x["force"]) for x in elements.values()),"element_stress_response_count":sum(bool(x["stress"]) for x in elements.values())},"global_equilibrium_evidence":{"applied_force_sum":ld,"reaction_force_sum":rs,"residual_force":residual,"acceptance_tolerance":None,"engineering_acceptance_claimed":False},"professional_verification_claimed":False,"independent_verification_claimed":False}

def case_ok(rc:int,stdout:str,norm:dict[str,Any])->dict[str,Any]:
    q={"returncode_zero":rc==0,"analysis_ok_marker":"PHOENIX_ANALYSIS_OK" in stdout,"evidence_capture_ok_marker":"PHOENIX_EVIDENCE_CAPTURE_OK" in stdout,"normalization_complete":norm.get("normalization_status")=="COMPLETE"}; q["qualified"]=all(q.values()); return q

def sources(repo:Path)->dict[str,Any]:
    root=repo/"projects/runtime"/PROJECT_ID; base=root/"results/session_adapters/structural_engineering/validated_v8_1_to_v8_12/v8_3"
    v83=base/"input.json"; package=base/"solver_package"; contract=root/"structural_identity_v1_3/pat001_structural_input_contract_v1_3.json"
    if not v83.is_file() or not contract.is_file() or not package.is_dir():raise FileNotFoundError("PAT-001 v8.3/contract/solver package prerequisite missing.")
    v=rj(v83)
    if v.get("project_id")!=PROJECT_ID:raise ValueError("PAT-001 project id mismatch.")
    if "opensees" not in [str(x).lower() for x in (v.get("solver_adapters") or [])]:raise ValueError("OpenSees not declared.")
    a=v.get("analytical_model") or {}; ac=v.get("action_load_model") or {}
    nodes=sorted(str(x["id"]) for x in a.get("nodes",[]) if isinstance(x,dict) and x.get("id"))
    cases=sorted(str(x["id"]) for x in ac.get("load_cases",[]) if isinstance(x,dict) and x.get("id"))
    decks=sorted(package.rglob("opensees_*.tcl"))
    dcase=sorted(p.stem[len("opensees_"):] for p in decks)
    if not decks or dcase!=cases:raise ValueError(f"OpenSees deck/load case mismatch: {dcase} vs {cases}")
    return {"v83":v83,"contract":contract,"decks":decks,"nodes":nodes,"cases":cases,"v83_sha256":sha(v83),"contract_sha256":sha(contract)}

def prepare(repo:Path,s:dict[str,Any],out:Path)->list[dict[str,Any]]:
    records=[]
    for src in s["decks"]:
        cid=src.stem[len("opensees_"):]; d=out/"prepared_cases"/cid; d.mkdir(parents=True,exist_ok=True)
        text=src.read_text(encoding="utf-8"); hard,audit=harden_deck(text)
        sp=d/"source_deck.tcl"; ep=d/"execution_deck.tcl"; sp.write_text(text,encoding="utf-8"); ep.write_text(hard,encoding="utf-8")
        rec={"case_id":cid,"source_reference":rr(src,repo),"source_sha256":sha(src),"source_copy_sha256":sha(sp),"execution_deck_sha256":sha(ep),"hardening":audit}; wj(d/"preparation_manifest.json",rec); records.append(rec)
    return records

def run_proc(cmd:list[str],cwd:Path,timeout:int):
    return subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,check=False,timeout=timeout)

def probe(exe:Path,out:Path)->dict[str,Any]:
    d=out/"environment_probe"; d.mkdir(parents=True,exist_ok=True); p=d/"probe.tcl"; p.write_text('puts "PHOENIX_OPENSEES_PROBE_OK"\nexit 0\n',encoding="utf-8")
    try:pr=run_proc([str(exe),str(p)],d,30)
    except subprocess.TimeoutExpired:return {"status":PROBE_FAIL,"passed":False,"returncode":124}
    stdout=pr.stdout or ""; stderr=pr.stderr or ""
    (d/"stdout.txt").write_text(stdout,encoding="utf-8"); (d/"stderr.txt").write_text(stderr,encoding="utf-8")
    combined=solver_console_output(stdout,stderr)
    streams=marker_streams("PHOENIX_OPENSEES_PROBE_OK",stdout,stderr)
    ok=pr.returncode==0 and "PHOENIX_OPENSEES_PROBE_OK" in combined
    r={
        "status":"OPENSEES_ENVIRONMENT_PROBE_PASSED" if ok else PROBE_FAIL,
        "passed":ok,
        "returncode":pr.returncode,
        "marker_streams":streams,
        "semantic_parse_streams":["stdout","stderr"],
        "raw_streams_preserved_separately":True,
        "probe_script":"probe.tcl",
    }
    wj(d/"probe_result.json",r); return r

def run(repo:Path,out:Path,explicit:str|None,allow:bool,timeout:int=180)->dict[str,Any]:
    repo=repo.resolve(); out=out.resolve(); out.mkdir(parents=True,exist_ok=True); s=sources(repo); exe=discover_executable(explicit); prep=prepare(repo,s,out)
    readiness={"schema_version":"phoenix.pat001-opensees-readiness/1.0","project_id":PROJECT_ID,"source_v8_3":rr(s["v83"],repo),"source_v8_3_sha256":s["v83_sha256"],"source_contract":rr(s["contract"],repo),"source_contract_sha256":s["contract_sha256"],"load_cases":s["cases"],"node_count":len(s["nodes"]),"prepared_case_count":len(prep),"executable_discovery":exe,"explicit_live_execution_opt_in":allow,"source_decks_overwritten":False}; wj(out/"pat001_opensees_readiness_v1_0.json",readiness)
    cases=[]; p=None
    if exe["path"] is None:status=NO_EXE
    elif not allow:status=READY
    else:
        p=probe(Path(exe["path"]),out)
        if not p["passed"]:status=PROBE_FAIL
        else:
            status=QUALIFIED
            for rec in prep:
                cid=rec["case_id"]; srcd=out/"prepared_cases"/cid; d=out/"live_cases"/cid; d.mkdir(parents=True,exist_ok=True)
                sp=d/"source_deck.tcl"; ep=d/"execution_deck.tcl"; shutil.copy2(srcd/"source_deck.tcl",sp); shutil.copy2(srcd/"execution_deck.tcl",ep)
                started=now()
                try:pr=run_proc([exe["path"],str(ep)],d,timeout); timed=False
                except subprocess.TimeoutExpired as ex: pr=subprocess.CompletedProcess([exe["path"],str(ep)],124,ex.stdout or "",(ex.stderr or "")+"\nPHOENIX_TIMEOUT"); timed=True
                stdout=pr.stdout or ""; stderr=pr.stderr or ""; (d/"stdout.txt").write_text(stdout,encoding="utf-8"); (d/"stderr.txt").write_text(stderr,encoding="utf-8")
                semantic_output=solver_console_output(stdout,stderr)
                tags=tag_maps(ep.read_text(encoding="utf-8")); norm=normalize(semantic_output,s["nodes"],tags,ep.read_text(encoding="utf-8")); norm.update({"project_id":PROJECT_ID,"case_id":cid,"source_v8_3_sha256":s["v83_sha256"],"source_deck_sha256":sha(sp),"execution_deck_sha256":sha(ep),"semantic_parse_streams":["stdout","stderr"],"raw_streams_preserved_separately":True}); wj(d/"normalized_results.json",norm)
                q=case_ok(pr.returncode,semantic_output,norm); ev={"schema_version":"phoenix.opensees-raw-evidence-case/1.0","project_id":PROJECT_ID,"case_id":cid,"started_at":started,"finished_at":now(),"timed_out":timed,"returncode":pr.returncode,"command":[exe["path"],str(ep)],"executable_sha256":exe["sha256"],"source_deck_sha256":sha(sp),"execution_deck_sha256":sha(ep),"stdout_sha256":sha(d/"stdout.txt"),"stderr_sha256":sha(d/"stderr.txt"),"normalized_results_sha256":sha(d/"normalized_results.json"),"semantic_parse_streams":["stdout","stderr"],"analysis_marker_streams":marker_streams("PHOENIX_ANALYSIS_OK",stdout,stderr),"evidence_marker_streams":marker_streams("PHOENIX_EVIDENCE_CAPTURE_OK",stdout,stderr),"raw_streams_preserved_separately":True,"qualification":q,"hardening":rec["hardening"]}; wj(d/"raw_evidence_manifest.json",ev); cases.append(ev)
            if not all(x["qualification"]["qualified"] for x in cases):
                status=EXEC_FAIL if any(not x["qualification"]["returncode_zero"] for x in cases) else NORM_FAIL
    qualified=status==QUALIFIED
    qual={"schema_version":"phoenix.pat001-opensees-adapter-qualification/1.0","project_id":PROJECT_ID,"adapter_id":ADAPTER_ID if qualified else None,"status":status,"qualified":qualified,"technical_state":"CALCULATED_UNVERIFIED" if qualified else "UNQUALIFIED","case_count":len(cases),"qualified_case_count":sum(x["qualification"]["qualified"] for x in cases),"professional_verification_claimed":False,"independent_verification_claimed":False,"golden_reference_used_as_pat001_evidence":False,"source_contract_overwritten":False,"scia_gap_changed":False,"production_release":"LOCKED","for_construction_release":"LOCKED","safety":SAFETY}; wj(out/"pat001_opensees_adapter_qualification_v1_0.json",qual)
    result={"schema_version":"phoenix.pat001-opensees-live-evidence-result/1.0","engine_id":ENGINE_ID,"engine_version":VERSION,"project_id":PROJECT_ID,"status":status,"adapter_qualified":qualified,"adapter_id":ADAPTER_ID if qualified else None,"technical_state":"CALCULATED_UNVERIFIED" if qualified else "UNQUALIFIED","executable_discovered":exe["path"] is not None,"executable_path":exe["path"],"prepared_case_count":len(prep),"executed_case_count":len(cases),"qualified_case_count":sum(x["qualification"]["qualified"] for x in cases),"live_project_solver_started":bool(allow and p),"source_decks_overwritten":False,"normalization_complete_for_all_cases":qualified,"remaining_pat001_structural_gap_unchanged":"PAT001-GAP-SCIA-MODEL","safety":SAFETY}; wj(out/"pat001_opensees_live_evidence_result_v1_0.json",result); return result

def main():
    q=argparse.ArgumentParser(); q.add_argument("--repository",required=True);q.add_argument("--output",required=True);q.add_argument("--opensees-executable");q.add_argument("--allow-live-execution",action="store_true");q.add_argument("--timeout",type=int,default=180); a=q.parse_args()
    print(json.dumps(run(Path(a.repository),Path(a.output),a.opensees_executable,a.allow_live_execution,a.timeout),indent=2))
if __name__=="__main__":main()
