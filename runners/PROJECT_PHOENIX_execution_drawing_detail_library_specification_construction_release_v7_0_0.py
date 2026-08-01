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

def normalize_details(profile):
    rows=[]
    for i,d in enumerate(profile.get("details",[]),1):
        rows.append({
            "detail_id":d.get("detail_id") or f"DET-{i:04d}",
            "title":d.get("title",""),
            "category":d.get("category",""),
            "drawing_reference":d.get("drawing_reference",""),
            "revision":d.get("revision",""),
            "mandatory":bool(d.get("mandatory",True)),
            "inputs_complete":bool(d.get("inputs_complete",False)),
            "dimensioned":bool(d.get("dimensioned",False)),
            "coordinated":bool(d.get("coordinated",False)),
            "status":d.get("status","DRAFT")
        })
    return rows

def normalize_documents(profile):
    rows=[]
    for i,d in enumerate(profile.get("execution_documents",[]),1):
        rows.append({
            "document_id":d.get("document_id") or f"EXE-DOC-{i:04d}",
            "title":d.get("title",""),
            "category":d.get("category",""),
            "revision":d.get("revision",""),
            "status":d.get("status","DRAFT"),
            "mandatory":bool(d.get("mandatory",True)),
            "file_path":d.get("file_path",""),
            "approved_for_construction":bool(d.get("approved_for_construction",False))
        })
    return rows

def normalize_specs(profile,key,prefix):
    rows=[]
    for i,s in enumerate(profile.get(key,[]),1):
        rows.append({
            "spec_id":s.get("spec_id") or f"{prefix}-{i:04d}",
            "category":s.get("category",""),
            "description":s.get("description",""),
            "performance_requirement":s.get("performance_requirement",""),
            "reference_standard":s.get("reference_standard",""),
            "manufacturer_product":s.get("manufacturer_product",""),
            "complete":bool(s.get("complete",False)),
            "approved":bool(s.get("approved",False))
        })
    return rows

def normalize_constructability(profile):
    rows=[]
    for i,c in enumerate(profile.get("constructability_checks",[]),1):
        rows.append({
            "check_id":c.get("check_id") or f"CONST-{i:04d}",
            "discipline":c.get("discipline",""),
            "description":c.get("description",""),
            "mandatory":bool(c.get("mandatory",True)),
            "status":c.get("status","NOT_ASSESSABLE"),
            "evidence_reference":c.get("evidence_reference",""),
            "reviewed_by":c.get("reviewed_by","")
        })
    return rows

def evaluate(profile,details,docs,mats,prods,checks,permit_gate):
    mandatory_details=[d for d in details if d["mandatory"]]
    mandatory_docs=[d for d in docs if d["mandatory"]]
    mandatory_checks=[c for c in checks if c["mandatory"]]

    permit_ok=bool(permit_gate and permit_gate.get("status")=="UNLOCKED")
    details_ok=bool(mandatory_details) and all(d["inputs_complete"] and d["dimensioned"] and d["coordinated"] for d in mandatory_details)
    docs_ok=bool(mandatory_docs) and all(
        d["revision"] and
        d["status"]=="APPROVED_FOR_CONSTRUCTION" and
        d["approved_for_construction"] and
        d["file_path"] and Path(d["file_path"]).is_file()
        for d in mandatory_docs
    )
    mats_ok=bool(mats) and all(s["complete"] and s["approved"] for s in mats)
    prods_ok=bool(prods) and all(s["complete"] and s["approved"] for s in prods)
    const_ok=bool(mandatory_checks) and all(c["status"]=="PASS" and c["evidence_reference"] for c in mandatory_checks)
    professional=bool(profile.get("professional_release",{}).get("approved"))

    ready=all([permit_ok,details_ok,docs_ok,mats_ok,prods_ok,const_ok,professional])

    return {
        "permit_dossier_gate_pass":permit_ok,
        "mandatory_details_complete_dimensioned_coordinated":details_ok,
        "mandatory_execution_documents_current_and_approved":docs_ok,
        "material_specifications_complete_and_approved":mats_ok,
        "product_requirements_complete_and_approved":prods_ok,
        "constructability_checks_pass":const_ok,
        "professional_release_approved":professional,
        "execution_ready":ready,
        "automatic_construction_release":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--execution-profile",required=True)
    ap.add_argument("--detail-library",required=True)
    ap.add_argument("--permit-dossier-gate",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.execution_profile)
    library=readj(q.detail_library)
    permit_gate=readj(q.permit_dossier_gate) if q.permit_dossier_gate else None

    out=Path(q.output).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("drawings","details","specifications","registers","reports","digital_twin"):
        (out/d).mkdir(parents=True,exist_ok=True)

    details=normalize_details(profile)
    docs=normalize_documents(profile)
    mats=normalize_specs(profile,"material_specifications","MAT")
    prods=normalize_specs(profile,"product_requirements","PRD")
    checks=normalize_constructability(profile)

    gate=evaluate(profile,details,docs,mats,prods,checks,permit_gate)

    csvw(out/"registers/detail_register.csv",
         ["detail_id","title","category","drawing_reference","revision","mandatory","inputs_complete","dimensioned","coordinated","status"],details)
    csvw(out/"registers/execution_document_register.csv",
         ["document_id","title","category","revision","status","mandatory","file_path","approved_for_construction"],docs)
    csvw(out/"registers/material_specification_register.csv",
         ["spec_id","category","description","performance_requirement","reference_standard","manufacturer_product","complete","approved"],mats)
    csvw(out/"registers/product_requirement_register.csv",
         ["spec_id","category","description","performance_requirement","reference_standard","manufacturer_product","complete","approved"],prods)
    csvw(out/"registers/constructability_check_register.csv",
         ["check_id","discipline","description","mandatory","status","evidence_reference","reviewed_by"],checks)

    writej(out/"details/detail_library_snapshot.json",library)
    writej(out/"reports/execution_release_matrix.json",{
        "details":details,
        "execution_documents":docs,
        "material_specifications":mats,
        "product_requirements":prods,
        "constructability_checks":checks,
        "release":gate
    })

    writej(out/"construction_release_gate.json",{
        "schema_version":"phoenix.construction-release-gate/7.0.0",
        "status":"UNLOCKED" if gate["execution_ready"] else "LOCKED",
        **gate,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("execution_ready","automatic_construction_release") and v is False]
    })

    writej(out/"digital_twin/execution_release_v7_0_0.json",{
        "schema_version":"phoenix.digital-twin-execution-release/7.0.0",
        "project_id":project.get("project_id",""),
        "detail_count":len(details),
        "execution_document_count":len(docs),
        "material_specification_count":len(mats),
        "product_requirement_count":len(prods),
        "constructability_check_count":len(checks),
        "execution_ready":gate["execution_ready"],
        "automatic_construction_release":False
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

    writej(out/"execution_release_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "execution_ready":gate["execution_ready"],
        "automatic_construction_release":False
    })

    print("EXECUTION DRAWING, DETAIL LIBRARY, SPECIFICATION AND CONSTRUCTION RELEASE ENGINE: PASSED")
    print("DETAIL LIBRARY: LOADED")
    print("DETAIL REGISTER: GENERATED")
    print("EXECUTION DOCUMENT REGISTER: GENERATED")
    print("MATERIAL SPECIFICATION REGISTER: GENERATED")
    print("PRODUCT REQUIREMENT REGISTER: GENERATED")
    print("CONSTRUCTABILITY CHECK REGISTER: GENERATED")
    print("EXECUTION RELEASE MATRIX: GENERATED")
    print("CENTRAL DIGITAL TWIN EXECUTION RELEASE WRITEBACK: PASSED")
    print("AUTOMATIC CONSTRUCTION RELEASE: DISABLED")
    print("EXECUTION-READY RELEASE: "+("UNLOCKED" if gate["execution_ready"] else "LOCKED"))

if __name__=="__main__":
    main()
