from __future__ import annotations
import argparse,csv,hashlib,json,shutil,zipfile
from pathlib import Path
from datetime import datetime,timezone

def readj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def writej(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(p):
    x=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): x.update(c)
    return x.hexdigest()
def csvw(p,fields,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise")
        w.writeheader();w.writerows(rows)

def normalize_docs(profile):
    rows=[]
    for i,d in enumerate(profile.get("document_requirements",[]),1):
        rows.append({
            "document_id":d.get("document_id") or f"DOC-{i:04d}",
            "title":d.get("title",""),
            "category":d.get("category",""),
            "source_path":d.get("source_path",""),
            "revision":d.get("revision",""),
            "status":d.get("status","DRAFT"),
            "required_for_submission":bool(d.get("required_for_submission",True)),
            "professional_approval":bool(d.get("professional_approval",False)),
            "approved_by":d.get("approved_by",""),
            "approval_date":d.get("approval_date","")
        })
    return rows

def evaluate(profile,docs,permit_gate):
    mandatory=[d for d in docs if d["required_for_submission"]]
    files_present=bool(mandatory) and all(d["source_path"] and Path(d["source_path"]).is_file() for d in mandatory)
    revisions=bool(mandatory) and all(bool(d["revision"]) for d in mandatory)
    approved=bool(mandatory) and all(d["status"]=="APPROVED_FOR_SUBMISSION" and d["professional_approval"] for d in mandatory)
    signoff=bool(profile.get("professional_signoff",{}).get("approved"))
    permit_ready=bool(permit_gate and permit_gate.get("permit_ready"))
    submission_ready=all([permit_ready,files_present,revisions,approved,signoff])
    return {
        "permit_evidence_gate_pass":permit_ready,
        "mandatory_documents_present":files_present,
        "mandatory_revisions_present":revisions,
        "mandatory_documents_approved_for_submission":approved,
        "professional_signoff_approved":signoff,
        "submission_ready":submission_ready,
        "automatic_authority_submission":False,
        "execution_ready":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--dossier-profile",required=True)
    ap.add_argument("--permit-gate",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.dossier_profile)
    permit_gate=readj(q.permit_gate) if q.permit_gate else None
    out=Path(q.output).resolve()

    if out.exists(): shutil.rmtree(out)
    for d in ("dossier","registers","submission","evidence","digital_twin"):
        (out/d).mkdir(parents=True,exist_ok=True)

    docs=normalize_docs(profile)
    gate=evaluate(profile,docs,permit_gate)

    csvw(out/"registers/document_register.csv",
         ["document_id","title","category","source_path","revision","status","required_for_submission","professional_approval","approved_by","approval_date"],
         docs)

    revisions=[
        {
            "document_id":d["document_id"],
            "revision":d["revision"],
            "status":d["status"],
            "approved_by":d["approved_by"],
            "approval_date":d["approval_date"]
        } for d in docs
    ]
    csvw(out/"registers/revision_register.csv",
         ["document_id","revision","status","approved_by","approval_date"],revisions)

    dossier_index={
        "schema_version":"phoenix.permit-dossier-index/6.9.0",
        "dossier_id":profile.get("dossier_id",""),
        "project_id":project.get("project_id",""),
        "generated_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "submission":profile.get("submission",{}),
        "documents":docs,
        "release":gate
    }
    writej(out/"dossier/dossier_index.json",dossier_index)
    writej(out/"dossier/document_control.json",{
        "document_count":len(docs),
        "required_count":sum(d["required_for_submission"] for d in docs),
        "approved_for_submission_count":sum(d["status"]=="APPROVED_FOR_SUBMISSION" for d in docs),
        "professional_approval_count":sum(d["professional_approval"] for d in docs)
    })

    package_dir=out/"submission/package"
    package_dir.mkdir(parents=True,exist_ok=True)
    copied=[]
    for d in docs:
        src=Path(d["source_path"]) if d["source_path"] else None
        if d["required_for_submission"] and src and src.is_file():
            safe=f'{d["document_id"]}__R{d["revision"]}__{src.name}'
            dest=package_dir/safe
            shutil.copy2(src,dest)
            copied.append({
                "document_id":d["document_id"],
                "revision":d["revision"],
                "filename":safe,
                "sha256":sha(dest),
                "size_bytes":dest.stat().st_size
            })

    writej(out/"submission/submission_manifest.json",{
        "schema_version":"phoenix.submission-manifest/6.9.0",
        "project_id":project.get("project_id",""),
        "dossier_id":profile.get("dossier_id",""),
        "files":copied,
        "submission_ready":gate["submission_ready"],
        "automatic_authority_submission":False
    })

    zip_path=out/"submission/permit_submission_package.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(package_dir.rglob("*")):
            if p.is_file():
                zf.write(p,p.relative_to(package_dir).as_posix())

    writej(out/"permit_dossier_release_gate.json",{
        "schema_version":"phoenix.permit-dossier-release-gate/6.9.0",
        "status":"UNLOCKED" if gate["submission_ready"] else "LOCKED",
        **gate,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("submission_ready","automatic_authority_submission","execution_ready") and v is False]
    })

    writej(out/"digital_twin/permit_dossier_v6_9_0.json",{
        "schema_version":"phoenix.digital-twin-permit-dossier/6.9.0",
        "project_id":project.get("project_id",""),
        "dossier_id":profile.get("dossier_id",""),
        "document_count":len(docs),
        "submission_package_created":True,
        "submission_ready":gate["submission_ready"],
        "automatic_authority_submission":False
    })

    artifacts=[]
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="artifact_manifest.json":
            artifacts.append({"path":p.relative_to(out).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha(p)})
    writej(out/"artifact_manifest.json",{"artifact_count":len(artifacts),"artifacts":artifacts})

    writej(out/"permit_dossier_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "document_count":len(docs),
        "submission_ready":gate["submission_ready"],
        "automatic_authority_submission":False,
        "execution_ready":False
    })

    print("PERMIT DOSSIER ASSEMBLY, DOCUMENT CONTROL AND SUBMISSION PACKAGE ENGINE: PASSED")
    print("DOCUMENT REGISTER: GENERATED")
    print("REVISION REGISTER: GENERATED")
    print("DOSSIER INDEX: GENERATED")
    print("SUBMISSION MANIFEST: GENERATED")
    print("SUBMISSION PACKAGE ZIP: GENERATED")
    print("SHA-256 ARTIFACT MANIFEST: GENERATED")
    print("CENTRAL DIGITAL TWIN PERMIT DOSSIER WRITEBACK: PASSED")
    print("AUTOMATIC AUTHORITY SUBMISSION: DISABLED")
    print("SUBMISSION-READY RELEASE: "+("UNLOCKED" if gate["submission_ready"] else "LOCKED"))
    print("EXECUTION-READY RELEASE: LOCKED")

if __name__=="__main__":
    main()
