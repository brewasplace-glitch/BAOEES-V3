from __future__ import annotations
import argparse,csv,hashlib,json,shutil
from pathlib import Path

def readj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def writej(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def csvw(p,fields,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise")
        w.writeheader();w.writerows(rows)

def norm_progress(profile):
    rows=[]
    for i,x in enumerate(profile.get("progress_records",[]),1):
        rows.append({
            "progress_id":x.get("progress_id") or f"PROG-{i:04d}",
            "work_package_id":x.get("work_package_id",""),
            "period":x.get("period",""),
            "planned_percent":x.get("planned_percent"),
            "actual_percent":x.get("actual_percent"),
            "status":x.get("status","NOT_REPORTED"),
            "evidence_reference":x.get("evidence_reference","")
        })
    return rows

def norm_daily(profile):
    rows=[]
    for i,x in enumerate(profile.get("daily_site_records",[]),1):
        rows.append({
            "record_id":x.get("record_id") or f"DAY-{i:04d}",
            "date":x.get("date",""),
            "weather":x.get("weather",""),
            "workforce":x.get("workforce"),
            "activities":x.get("activities",""),
            "delays":x.get("delays",""),
            "safety_events":x.get("safety_events",""),
            "recorded_by":x.get("recorded_by","")
        })
    return rows

def norm_evidence(profile):
    rows=[]
    for i,x in enumerate(profile.get("site_evidence",[]),1):
        rows.append({
            "evidence_id":x.get("evidence_id") or f"SITE-EVD-{i:04d}",
            "type":x.get("type",""),
            "file_path":x.get("file_path",""),
            "date":x.get("date",""),
            "location_reference":x.get("location_reference",""),
            "related_record_id":x.get("related_record_id",""),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_ncr(profile):
    rows=[]
    for i,x in enumerate(profile.get("ncrs",[]),1):
        rows.append({
            "ncr_id":x.get("ncr_id") or f"NCR-{i:04d}",
            "severity":x.get("severity","MINOR"),
            "description":x.get("description",""),
            "status":x.get("status","OPEN"),
            "mandatory_close":bool(x.get("mandatory_close",True)),
            "corrective_action":x.get("corrective_action",""),
            "verification_evidence":x.get("verification_evidence",""),
            "verified_by":x.get("verified_by","")
        })
    return rows

def norm_changes(profile):
    rows=[]
    for i,x in enumerate(profile.get("changes_and_deviations",[]),1):
        rows.append({
            "change_id":x.get("change_id") or f"CHG-{i:04d}",
            "type":x.get("type",""),
            "description":x.get("description",""),
            "origin":x.get("origin",""),
            "status":x.get("status","OPEN"),
            "approved":bool(x.get("approved",False)),
            "approval_reference":x.get("approval_reference",""),
            "as_built_impact":bool(x.get("as_built_impact",False))
        })
    return rows

def norm_punch(profile):
    rows=[]
    for i,x in enumerate(profile.get("punch_items",[]),1):
        rows.append({
            "punch_id":x.get("punch_id") or f"PUNCH-{i:04d}",
            "location":x.get("location",""),
            "description":x.get("description",""),
            "mandatory":bool(x.get("mandatory",True)),
            "status":x.get("status","OPEN"),
            "closure_evidence":x.get("closure_evidence",""),
            "verified_by":x.get("verified_by","")
        })
    return rows

def norm_commissioning(profile):
    rows=[]
    for i,x in enumerate(profile.get("commissioning_items",[]),1):
        rows.append({
            "commissioning_id":x.get("commissioning_id") or f"COMM-{i:04d}",
            "system":x.get("system",""),
            "test":x.get("test",""),
            "mandatory":bool(x.get("mandatory",True)),
            "status":x.get("status","NOT_ASSESSABLE"),
            "result_reference":x.get("result_reference",""),
            "witnessed_by":x.get("witnessed_by","")
        })
    return rows

def norm_docs(profile,key,prefix):
    rows=[]
    for i,x in enumerate(profile.get(key,[]),1):
        rows.append({
            "document_id":x.get("document_id") or f"{prefix}-{i:04d}",
            "title":x.get("title",""),
            "revision":x.get("revision",""),
            "file_path":x.get("file_path",""),
            "mandatory":bool(x.get("mandatory",True)),
            "status":x.get("status","DRAFT"),
            "verified":bool(x.get("verified",False)),
            "verified_by":x.get("verified_by","")
        })
    return rows

def evaluate(profile,ncrs,punch,commissioning,asbuilt,handover,field_gate):
    field_ok=bool(field_gate and field_gate.get("status")=="UNLOCKED")
    critical_open=any(n["severity"]=="CRITICAL" and n["status"]!="CLOSED" for n in ncrs)
    mandatory_ncr=[n for n in ncrs if n["mandatory_close"]]
    ncr_ok=all(n["status"]=="CLOSED" and n["verification_evidence"] for n in mandatory_ncr) if mandatory_ncr else True

    mandatory_punch=[p for p in punch if p["mandatory"]]
    punch_ok=all(p["status"]=="CLOSED" and p["closure_evidence"] for p in mandatory_punch) if mandatory_punch else True

    mandatory_comm=[c for c in commissioning if c["mandatory"]]
    commissioning_ok=bool(mandatory_comm) and all(c["status"]=="PASS" and c["result_reference"] for c in mandatory_comm)

    mandatory_asbuilt=[d for d in asbuilt if d["mandatory"]]
    asbuilt_ok=bool(mandatory_asbuilt) and all(
        d["revision"] and d["file_path"] and Path(d["file_path"]).is_file() and d["status"]=="FINAL" and d["verified"]
        for d in mandatory_asbuilt
    )

    mandatory_handover=[d for d in handover if d["mandatory"]]
    handover_ok=bool(mandatory_handover) and all(
        d["revision"] and d["file_path"] and Path(d["file_path"]).is_file() and d["status"]=="FINAL" and d["verified"]
        for d in mandatory_handover
    )

    professional=bool(profile.get("professional_completion_release",{}).get("approved"))
    ready=all([field_ok,not critical_open,ncr_ok,punch_ok,commissioning_ok,asbuilt_ok,handover_ok,professional])

    return {
        "field_release_gate_pass":field_ok,
        "no_open_critical_ncrs":not critical_open,
        "all_mandatory_ncrs_closed":ncr_ok,
        "all_mandatory_punch_items_closed":punch_ok,
        "commissioning_complete_and_passed":commissioning_ok,
        "as_built_documents_complete_and_verified":asbuilt_ok,
        "handover_documents_complete_and_verified":handover_ok,
        "professional_completion_release_approved":professional,
        "completion_and_handover_ready":ready,
        "automatic_handover_release":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--handover-profile",required=True)
    ap.add_argument("--field-release-gate",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.handover_profile)
    field_gate=readj(q.field_release_gate) if q.field_release_gate else None

    out=Path(q.output).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("progress","site_records","evidence","ncr","changes","punch","commissioning","as_built","handover","reports","digital_twin"):
        (out/d).mkdir(parents=True,exist_ok=True)

    progress=norm_progress(profile)
    daily=norm_daily(profile)
    evidence=norm_evidence(profile)
    ncrs=norm_ncr(profile)
    changes=norm_changes(profile)
    punch=norm_punch(profile)
    commissioning=norm_commissioning(profile)
    asbuilt=norm_docs(profile,"as_built_documents","ASB")
    handover=norm_docs(profile,"handover_documents","HND")

    gate=evaluate(profile,ncrs,punch,commissioning,asbuilt,handover,field_gate)

    csvw(out/"progress/progress_register.csv",
         ["progress_id","work_package_id","period","planned_percent","actual_percent","status","evidence_reference"],progress)
    csvw(out/"site_records/daily_site_record_register.csv",
         ["record_id","date","weather","workforce","activities","delays","safety_events","recorded_by"],daily)
    csvw(out/"evidence/site_evidence_register.csv",
         ["evidence_id","type","file_path","date","location_reference","related_record_id","verified"],evidence)
    csvw(out/"ncr/ncr_register.csv",
         ["ncr_id","severity","description","status","mandatory_close","corrective_action","verification_evidence","verified_by"],ncrs)
    csvw(out/"changes/change_deviation_register.csv",
         ["change_id","type","description","origin","status","approved","approval_reference","as_built_impact"],changes)
    csvw(out/"punch/punch_list_register.csv",
         ["punch_id","location","description","mandatory","status","closure_evidence","verified_by"],punch)
    csvw(out/"commissioning/commissioning_register.csv",
         ["commissioning_id","system","test","mandatory","status","result_reference","witnessed_by"],commissioning)
    csvw(out/"as_built/as_built_document_register.csv",
         ["document_id","title","revision","file_path","mandatory","status","verified","verified_by"],asbuilt)
    csvw(out/"handover/handover_document_register.csv",
         ["document_id","title","revision","file_path","mandatory","status","verified","verified_by"],handover)

    writej(out/"reports/completion_handover_matrix.json",{
        "progress_records":progress,
        "daily_site_records":daily,
        "site_evidence":evidence,
        "ncrs":ncrs,
        "changes_and_deviations":changes,
        "punch_items":punch,
        "commissioning_items":commissioning,
        "as_built_documents":asbuilt,
        "handover_documents":handover,
        "release":gate
    })

    writej(out/"completion_handover_gate.json",{
        "schema_version":"phoenix.completion-handover-gate/7.2.0",
        "status":"UNLOCKED" if gate["completion_and_handover_ready"] else "LOCKED",
        **gate,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("completion_and_handover_ready","automatic_handover_release") and v is False]
    })

    writej(out/"digital_twin/construction_handover_v7_2_0.json",{
        "schema_version":"phoenix.digital-twin-construction-handover/7.2.0",
        "project_id":project.get("project_id",""),
        "progress_record_count":len(progress),
        "site_record_count":len(daily),
        "site_evidence_count":len(evidence),
        "ncr_count":len(ncrs),
        "change_count":len(changes),
        "punch_item_count":len(punch),
        "commissioning_item_count":len(commissioning),
        "as_built_document_count":len(asbuilt),
        "handover_document_count":len(handover),
        "completion_and_handover_ready":gate["completion_and_handover_ready"],
        "automatic_handover_release":False
    })

    artifacts=[]
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="artifact_manifest.json":
            artifacts.append({
                "path":p.relative_to(out).as_posix(),
                "size_bytes":p.stat().st_size,
                "sha256":sha(p)
            })
    writej(out/"artifact_manifest.json",{"artifact_count":len(artifacts),"artifacts":artifacts})

    writej(out/"construction_handover_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "completion_and_handover_ready":gate["completion_and_handover_ready"],
        "automatic_handover_release":False
    })

    print("CONSTRUCTION PROGRESS, SITE RECORDS, NCR, HANDOVER AND AS-BUILT ENGINE: PASSED")
    print("CONSTRUCTION PROGRESS REGISTER: GENERATED")
    print("DAILY SITE RECORD REGISTER: GENERATED")
    print("SITE EVIDENCE REGISTER: GENERATED")
    print("NCR REGISTER: GENERATED")
    print("CHANGE AND DEVIATION REGISTER: GENERATED")
    print("PUNCH LIST REGISTER: GENERATED")
    print("COMMISSIONING REGISTER: GENERATED")
    print("AS-BUILT DOCUMENT REGISTER: GENERATED")
    print("HANDOVER DOCUMENT REGISTER: GENERATED")
    print("COMPLETION AND HANDOVER MATRIX: GENERATED")
    print("CENTRAL DIGITAL TWIN HANDOVER WRITEBACK: PASSED")
    print("AUTOMATIC HANDOVER RELEASE: DISABLED")
    print("COMPLETION/HANDOVER-READY RELEASE: "+("UNLOCKED" if gate["completion_and_handover_ready"] else "LOCKED"))

if __name__=="__main__":
    main()
