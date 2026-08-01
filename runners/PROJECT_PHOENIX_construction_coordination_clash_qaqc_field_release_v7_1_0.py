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

def norm_models(profile):
    rows=[]
    for i,m in enumerate(profile.get("discipline_models",[]),1):
        rows.append({
            "model_id":m.get("model_id") or f"MODEL-{i:04d}",
            "discipline":m.get("discipline",""),
            "file_path":m.get("file_path",""),
            "revision":m.get("revision",""),
            "current_revision":bool(m.get("current_revision",False)),
            "coordination_status":m.get("coordination_status","NOT_REVIEWED")
        })
    return rows

def norm_clashes(profile):
    rows=[]
    for i,c in enumerate(profile.get("clashes",[]),1):
        rows.append({
            "clash_id":c.get("clash_id") or f"CLASH-{i:04d}",
            "discipline_a":c.get("discipline_a",""),
            "discipline_b":c.get("discipline_b",""),
            "element_a":c.get("element_a",""),
            "element_b":c.get("element_b",""),
            "severity":c.get("severity","MINOR"),
            "status":c.get("status","OPEN"),
            "owner":c.get("owner",""),
            "resolution_note":c.get("resolution_note","")
        })
    return rows

def norm_issues(profile):
    rows=[]
    for i,x in enumerate(profile.get("issues",[]),1):
        rows.append({
            "issue_id":x.get("issue_id") or f"ISSUE-{i:04d}",
            "category":x.get("category",""),
            "severity":x.get("severity","MINOR"),
            "status":x.get("status","OPEN"),
            "release_blocking":bool(x.get("release_blocking",False)),
            "owner":x.get("owner",""),
            "due_date":x.get("due_date",""),
            "evidence_reference":x.get("evidence_reference","")
        })
    return rows

def norm_qaqc(profile):
    rows=[]
    for i,x in enumerate(profile.get("qaqc_items",[]),1):
        rows.append({
            "qaqc_id":x.get("qaqc_id") or f"QAQC-{i:04d}",
            "discipline":x.get("discipline",""),
            "description":x.get("description",""),
            "mandatory":bool(x.get("mandatory",True)),
            "status":x.get("status","NOT_ASSESSABLE"),
            "evidence_reference":x.get("evidence_reference",""),
            "checked_by":x.get("checked_by","")
        })
    return rows

def norm_work(profile):
    rows=[]
    for i,x in enumerate(profile.get("work_packages",[]),1):
        rows.append({
            "work_package_id":x.get("work_package_id") or f"WP-{i:04d}",
            "title":x.get("title",""),
            "discipline":x.get("discipline",""),
            "revision":x.get("revision",""),
            "current_revision":bool(x.get("current_revision",False)),
            "status":x.get("status","DRAFT"),
            "field_release_required":bool(x.get("field_release_required",True))
        })
    return rows

def norm_inspections(profile):
    rows=[]
    for i,x in enumerate(profile.get("field_inspections",[]),1):
        rows.append({
            "inspection_id":x.get("inspection_id") or f"INSP-{i:04d}",
            "work_package_id":x.get("work_package_id",""),
            "description":x.get("description",""),
            "mandatory":bool(x.get("mandatory",True)),
            "status":x.get("status","NOT_ASSESSABLE"),
            "evidence_reference":x.get("evidence_reference",""),
            "inspected_by":x.get("inspected_by","")
        })
    return rows

def evaluate(profile,models,clashes,issues,qaqc,work,inspections,execution_gate):
    execution_ok=bool(execution_gate and execution_gate.get("status")=="UNLOCKED")
    critical_open=any(c["severity"]=="CRITICAL" and c["status"] not in ("RESOLVED","CLOSED","WAIVED") for c in clashes)
    qaqc_mand=[q for q in qaqc if q["mandatory"]]
    qaqc_ok=bool(qaqc_mand) and all(q["status"]=="PASS" and q["evidence_reference"] for q in qaqc_mand)
    insp_mand=[i for i in inspections if i["mandatory"]]
    inspections_ok=bool(insp_mand) and all(i["status"]=="PASS" and i["evidence_reference"] for i in insp_mand)
    blocking_open=any(i["release_blocking"] and i["status"] not in ("RESOLVED","CLOSED","WAIVED") for i in issues)
    release_work=[w for w in work if w["field_release_required"]]
    work_ok=bool(release_work) and all(w["current_revision"] and w["status"]=="APPROVED_FOR_FIELD" for w in release_work)
    models_ok=bool(models) and all(m["current_revision"] and m["coordination_status"]=="COORDINATED" for m in models)
    professional=bool(profile.get("professional_site_release",{}).get("approved"))

    ready=all([
        execution_ok,
        not critical_open,
        qaqc_ok,
        inspections_ok,
        not blocking_open,
        work_ok,
        models_ok,
        professional
    ])

    return {
        "execution_release_gate_pass":execution_ok,
        "no_open_critical_clashes":not critical_open,
        "all_mandatory_qaqc_items_pass":qaqc_ok,
        "all_mandatory_field_inspections_pass":inspections_ok,
        "all_release_blocking_issues_closed":not blocking_open,
        "work_packages_current_and_approved":work_ok,
        "discipline_models_current_and_coordinated":models_ok,
        "professional_site_release_approved":professional,
        "field_release_ready":ready,
        "automatic_field_release":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--field-profile",required=True)
    ap.add_argument("--execution-gate",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.field_profile)
    execution_gate=readj(q.execution_gate) if q.execution_gate else None

    out=Path(q.output).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("coordination","clashes","issues","qaqc","work_packages","field","reports","digital_twin"):
        (out/d).mkdir(parents=True,exist_ok=True)

    models=norm_models(profile)
    clashes=norm_clashes(profile)
    issues=norm_issues(profile)
    qaqc=norm_qaqc(profile)
    work=norm_work(profile)
    inspections=norm_inspections(profile)
    gate=evaluate(profile,models,clashes,issues,qaqc,work,inspections,execution_gate)

    csvw(out/"coordination/discipline_model_register.csv",
         ["model_id","discipline","file_path","revision","current_revision","coordination_status"],models)
    csvw(out/"clashes/clash_register.csv",
         ["clash_id","discipline_a","discipline_b","element_a","element_b","severity","status","owner","resolution_note"],clashes)
    csvw(out/"issues/issue_register.csv",
         ["issue_id","category","severity","status","release_blocking","owner","due_date","evidence_reference"],issues)
    csvw(out/"qaqc/qaqc_register.csv",
         ["qaqc_id","discipline","description","mandatory","status","evidence_reference","checked_by"],qaqc)
    csvw(out/"work_packages/work_package_register.csv",
         ["work_package_id","title","discipline","revision","current_revision","status","field_release_required"],work)
    csvw(out/"field/field_inspection_register.csv",
         ["inspection_id","work_package_id","description","mandatory","status","evidence_reference","inspected_by"],inspections)

    writej(out/"reports/field_release_matrix.json",{
        "discipline_models":models,
        "clashes":clashes,
        "issues":issues,
        "qaqc_items":qaqc,
        "work_packages":work,
        "field_inspections":inspections,
        "release":gate
    })

    writej(out/"field_release_gate.json",{
        "schema_version":"phoenix.field-release-gate/7.1.0",
        "status":"UNLOCKED" if gate["field_release_ready"] else "LOCKED",
        **gate,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("field_release_ready","automatic_field_release") and v is False]
    })

    writej(out/"digital_twin/construction_coordination_field_release_v7_1_0.json",{
        "schema_version":"phoenix.digital-twin-construction-coordination/7.1.0",
        "project_id":project.get("project_id",""),
        "discipline_model_count":len(models),
        "clash_count":len(clashes),
        "issue_count":len(issues),
        "qaqc_item_count":len(qaqc),
        "work_package_count":len(work),
        "field_inspection_count":len(inspections),
        "field_release_ready":gate["field_release_ready"],
        "automatic_field_release":False
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

    writej(out/"construction_coordination_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "field_release_ready":gate["field_release_ready"],
        "automatic_field_release":False
    })

    print("CONSTRUCTION COORDINATION, CLASH DETECTION, QA/QC AND FIELD RELEASE ENGINE: PASSED")
    print("DISCIPLINE MODEL REGISTER: GENERATED")
    print("CLASH REGISTER: GENERATED")
    print("ISSUE REGISTER: GENERATED")
    print("QA/QC REGISTER: GENERATED")
    print("WORK PACKAGE REGISTER: GENERATED")
    print("FIELD INSPECTION REGISTER: GENERATED")
    print("FIELD RELEASE MATRIX: GENERATED")
    print("CENTRAL DIGITAL TWIN FIELD RELEASE WRITEBACK: PASSED")
    print("AUTOMATIC FIELD RELEASE: DISABLED")
    print("FIELD-READY RELEASE: "+("UNLOCKED" if gate["field_release_ready"] else "LOCKED"))

if __name__=="__main__":
    main()
