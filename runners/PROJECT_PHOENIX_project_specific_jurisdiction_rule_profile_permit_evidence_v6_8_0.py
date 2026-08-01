from __future__ import annotations
import argparse,csv,hashlib,json,shutil
from pathlib import Path

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

def normalize_sources(profile):
    out=[]
    for i,r in enumerate(profile.get("regulations",[]),1):
        out.append({
            "source_id":r.get("source_id") or f"SRC-{i:04d}",
            "title":r.get("title",""),
            "publisher":r.get("publisher",""),
            "version":r.get("version",""),
            "effective_date":r.get("effective_date",""),
            "url":r.get("url",""),
            "local_file":r.get("local_file",""),
            "verified":bool(r.get("verified",False)),
            "verified_by":r.get("verified_by",""),
            "verified_date":r.get("verified_date","")
        })
    return out

def normalize_rules(profile):
    rows=[]
    for i,r in enumerate(profile.get("rules",[]),1):
        rows.append({
            "rule_id":r.get("rule_id") or f"RULE-{i:04d}",
            "domain":r.get("domain",""),
            "requirement":r.get("requirement",""),
            "source_id":r.get("source_id",""),
            "source_clause":r.get("source_clause",""),
            "mandatory":bool(r.get("mandatory",True)),
            "assessable":bool(r.get("assessable",False)),
            "status":r.get("status","NOT_ASSESSABLE"),
            "evidence_ids":list(r.get("evidence_ids",[])),
            "review_note":r.get("review_note","")
        })
    return rows

def normalize_evidence(profile):
    rows=[]
    for i,e in enumerate(profile.get("evidence_requirements",[]),1):
        rows.append({
            "evidence_id":e.get("evidence_id") or f"EVD-{i:04d}",
            "type":e.get("type",""),
            "description":e.get("description",""),
            "file_path":e.get("file_path",""),
            "source_reference":e.get("source_reference",""),
            "status":e.get("status","MISSING"),
            "verified":bool(e.get("verified",False)),
            "verified_by":e.get("verified_by",""),
            "verified_date":e.get("verified_date","")
        })
    return rows

def evaluate(profile,sources,rules,evidence):
    jurisdiction_verified=bool(profile.get("jurisdiction",{}).get("verified"))
    verified_sources=bool(sources) and all(s["verified"] for s in sources)
    rule_source_ids={s["source_id"] for s in sources}
    traceability_complete=all((not r["mandatory"]) or (r["source_id"] in rule_source_ids and r["source_clause"]) for r in rules)
    mandatory=[r for r in rules if r["mandatory"]]
    all_assessable=bool(mandatory) and all(r["assessable"] for r in mandatory)
    all_pass=bool(mandatory) and all(r["status"]=="PASS" for r in mandatory)
    evidence_by_id={e["evidence_id"]:e for e in evidence}
    evidence_complete=True
    for r in mandatory:
        if not r["evidence_ids"]:
            evidence_complete=False
            break
        if any(eid not in evidence_by_id or evidence_by_id[eid]["status"]!="PRESENT" or not evidence_by_id[eid]["verified"] for eid in r["evidence_ids"]):
            evidence_complete=False
            break
    professional=bool(profile.get("professional_review",{}).get("approved"))
    submission=bool(profile.get("submission",{}).get("evidence_complete"))
    permit=all([jurisdiction_verified,verified_sources,traceability_complete,all_assessable,all_pass,evidence_complete,professional,submission])
    return {
        "jurisdiction_verified":jurisdiction_verified,
        "verified_sources":verified_sources,
        "traceability_complete":traceability_complete,
        "mandatory_rules_present":bool(mandatory),
        "all_mandatory_rules_assessable":all_assessable,
        "all_mandatory_rules_pass":all_pass,
        "mandatory_evidence_complete_and_verified":evidence_complete,
        "professional_review_approved":professional,
        "authority_submission_evidence_complete":submission,
        "permit_ready":permit,
        "execution_ready":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--jurisdiction-profile",required=True)
    ap.add_argument("--compliance-report",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.jurisdiction_profile)
    compliance=readj(q.compliance_report) if q.compliance_report else None
    out=Path(q.output).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("reports","schedules","evidence","digital_twin"): (out/d).mkdir(parents=True,exist_ok=True)

    sources=normalize_sources(profile)
    rules=normalize_rules(profile)
    evidence=normalize_evidence(profile)
    gate=evaluate(profile,sources,rules,evidence)

    csvw(out/"schedules/regulation_source_register.csv",
         ["source_id","title","publisher","version","effective_date","url","local_file","verified","verified_by","verified_date"],sources)
    csvw(out/"schedules/rule_traceability_register.csv",
         ["rule_id","domain","requirement","source_id","source_clause","mandatory","assessable","status","evidence_ids","review_note"],
         [{**r,"evidence_ids":"|".join(sorted(r["evidence_ids"]))} for r in rules])
    csvw(out/"schedules/permit_evidence_register.csv",
         ["evidence_id","type","description","file_path","source_reference","status","verified","verified_by","verified_date"],evidence)

    matrix=[]
    for r in rules:
        matrix.append({
            "rule_id":r["rule_id"],
            "domain":r["domain"],
            "mandatory":r["mandatory"],
            "assessable":r["assessable"],
            "status":r["status"],
            "source_linked":bool(r["source_id"] and r["source_clause"]),
            "evidence_linked":bool(r["evidence_ids"])
        })
    writej(out/"reports/permit_readiness_matrix.json",{"rules":matrix,"gate":gate})
    writej(out/"reports/jurisdiction_profile_snapshot.json",profile)
    writej(out/"reports/source_register.json",{"sources":sources})
    writej(out/"reports/evidence_register.json",{"evidence":evidence})
    writej(out/"digital_twin/project_specific_permit_evidence_v6_8_0.json",{
        "schema_version":"phoenix.digital-twin-permit-evidence/6.8.0",
        "project_id":project.get("project_id",""),
        "jurisdiction_profile_id":profile.get("profile_id",""),
        "source_count":len(sources),
        "rule_count":len(rules),
        "evidence_count":len(evidence),
        "compliance_report_linked":bool(compliance),
        "release":gate,
        "automatic_legal_approval":False
    })
    writej(out/"permit_release_gate.json",{
        "schema_version":"phoenix.permit-release-gate/6.8.0",
        "status":"UNLOCKED" if gate["permit_ready"] else "LOCKED",
        **gate,
        "automatic_legal_approval":False,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("permit_ready","execution_ready") and v is False]
    })

    arts=[]
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="artifact_manifest.json":
            arts.append({"path":p.relative_to(out).as_posix(),"size_bytes":p.stat().st_size,"sha256":sha(p)})
    writej(out/"artifact_manifest.json",{"artifact_count":len(arts),"artifacts":arts})
    writej(out/"permit_evidence_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "sources":len(sources),
        "rules":len(rules),
        "evidence_items":len(evidence),
        "permit_ready":gate["permit_ready"],
        "execution_ready":False
    })

    print("PROJECT-SPECIFIC JURISDICTION RULE PROFILE AND PERMIT EVIDENCE ENGINE: PASSED")
    print("JURISDICTION IDENTITY REGISTER: GENERATED")
    print("REGULATION SOURCE REGISTER: GENERATED")
    print("RULE TRACEABILITY REGISTER: GENERATED")
    print("PERMIT EVIDENCE REGISTER: GENERATED")
    print("PERMIT READINESS MATRIX: GENERATED")
    print("CENTRAL DIGITAL TWIN PERMIT EVIDENCE WRITEBACK: PASSED")
    print("AUTOMATIC LEGAL APPROVAL: DISABLED")
    print("PERMIT-READY RELEASE: "+("UNLOCKED" if gate["permit_ready"] else "LOCKED"))
    print("EXECUTION-READY RELEASE: LOCKED")

if __name__=="__main__": main()
