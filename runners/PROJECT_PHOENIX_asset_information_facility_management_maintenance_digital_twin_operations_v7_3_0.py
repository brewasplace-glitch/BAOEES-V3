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

def norm_assets(profile):
    rows=[]
    for i,x in enumerate(profile.get("assets",[]),1):
        rows.append({
            "asset_id":x.get("asset_id") or f"AST-{i:05d}",
            "name":x.get("name",""),
            "category":x.get("category",""),
            "location":x.get("location",""),
            "manufacturer":x.get("manufacturer",""),
            "model":x.get("model",""),
            "serial_number":x.get("serial_number",""),
            "commissioning_date":x.get("commissioning_date",""),
            "status":x.get("status","COMMISSIONED"),
            "criticality":x.get("criticality","NORMAL"),
            "mandatory":bool(x.get("mandatory",True))
        })
    return rows

def norm_docs(profile,key,prefix):
    rows=[]
    for i,x in enumerate(profile.get(key,[]),1):
        rows.append({
            "record_id":x.get("record_id") or f"{prefix}-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "title":x.get("title",""),
            "file_path":x.get("file_path",""),
            "revision":x.get("revision",""),
            "mandatory":bool(x.get("mandatory",True)),
            "verified":bool(x.get("verified",False)),
            "verified_by":x.get("verified_by","")
        })
    return rows

def norm_warranties(profile):
    rows=[]
    for i,x in enumerate(profile.get("warranties",[]),1):
        rows.append({
            "warranty_id":x.get("warranty_id") or f"WAR-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "provider":x.get("provider",""),
            "start_date":x.get("start_date",""),
            "end_date":x.get("end_date",""),
            "reference":x.get("reference",""),
            "mandatory":bool(x.get("mandatory",True)),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_maintenance(profile):
    rows=[]
    for i,x in enumerate(profile.get("maintenance_plans",[]),1):
        rows.append({
            "maintenance_id":x.get("maintenance_id") or f"MNT-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "task":x.get("task",""),
            "interval":x.get("interval",""),
            "responsible_party":x.get("responsible_party",""),
            "procedure_reference":x.get("procedure_reference",""),
            "mandatory":bool(x.get("mandatory",True)),
            "complete":bool(x.get("complete",False))
        })
    return rows

def norm_inspections(profile):
    rows=[]
    for i,x in enumerate(profile.get("inspections",[]),1):
        rows.append({
            "inspection_id":x.get("inspection_id") or f"INSP-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "inspection_type":x.get("inspection_type",""),
            "date":x.get("date",""),
            "status":x.get("status","NOT_ASSESSABLE"),
            "result_reference":x.get("result_reference",""),
            "inspected_by":x.get("inspected_by",""),
            "initial_required":bool(x.get("initial_required",False))
        })
    return rows

def norm_faults(profile):
    rows=[]
    for i,x in enumerate(profile.get("faults",[]),1):
        rows.append({
            "fault_id":x.get("fault_id") or f"FLT-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "reported_date":x.get("reported_date",""),
            "severity":x.get("severity","MINOR"),
            "description":x.get("description",""),
            "status":x.get("status","OPEN"),
            "resolution_reference":x.get("resolution_reference","")
        })
    return rows

def norm_service(profile):
    rows=[]
    for i,x in enumerate(profile.get("service_history",[]),1):
        rows.append({
            "service_id":x.get("service_id") or f"SRV-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "date":x.get("date",""),
            "activity":x.get("activity",""),
            "provider":x.get("provider",""),
            "result":x.get("result",""),
            "document_reference":x.get("document_reference","")
        })
    return rows

def norm_spares(profile):
    rows=[]
    for i,x in enumerate(profile.get("spare_parts",[]),1):
        rows.append({
            "spare_id":x.get("spare_id") or f"SPR-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "part_number":x.get("part_number",""),
            "description":x.get("description",""),
            "minimum_stock":x.get("minimum_stock"),
            "critical":bool(x.get("critical",False)),
            "supplier":x.get("supplier","")
        })
    return rows

def norm_replacement(profile):
    rows=[]
    for i,x in enumerate(profile.get("replacement_cycles",[]),1):
        rows.append({
            "replacement_id":x.get("replacement_id") or f"RPL-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "expected_life_years":x.get("expected_life_years"),
            "replacement_year":x.get("replacement_year"),
            "budget_reference":x.get("budget_reference",""),
            "strategy":x.get("strategy","")
        })
    return rows

def evaluate(profile,assets,docs,warranties,maintenance,inspections,spares,handover_gate):
    handover_ok=bool(handover_gate and handover_gate.get("status")=="UNLOCKED")

    mandatory_assets=[a for a in assets if a["mandatory"]]
    assets_ok=bool(mandatory_assets) and all(
        a["asset_id"] and a["name"] and a["category"] and a["location"] and a["status"] in ("COMMISSIONED","IN_SERVICE")
        for a in mandatory_assets
    )

    mandatory_docs=[d for d in docs if d["mandatory"]]
    docs_ok=bool(mandatory_docs) and all(
        d["file_path"] and Path(d["file_path"]).is_file() and d["revision"] and d["verified"]
        for d in mandatory_docs
    )

    mandatory_warranties=[w for w in warranties if w["mandatory"]]
    warranties_ok=bool(mandatory_warranties) and all(
        w["provider"] and w["start_date"] and w["end_date"] and w["reference"] and w["verified"]
        for w in mandatory_warranties
    )

    mandatory_maintenance=[m for m in maintenance if m["mandatory"]]
    maintenance_ok=bool(mandatory_maintenance) and all(
        m["task"] and m["interval"] and m["responsible_party"] and m["procedure_reference"] and m["complete"]
        for m in mandatory_maintenance
    )

    initial=[i for i in inspections if i["initial_required"]]
    inspections_ok=bool(initial) and all(i["status"]=="PASS" and i["result_reference"] for i in initial)

    critical_assets={a["asset_id"] for a in assets if a["criticality"]=="CRITICAL"}
    if critical_assets:
        spares_ok=all(any(s["asset_id"]==aid and s["critical"] and s["part_number"] for s in spares) for aid in critical_assets)
    else:
        spares_ok=True

    professional=bool(profile.get("professional_operations_acceptance",{}).get("approved"))
    ready=all([handover_ok,assets_ok,docs_ok,warranties_ok,maintenance_ok,inspections_ok,spares_ok,professional])

    return {
        "handover_gate_pass":handover_ok,
        "mandatory_assets_complete":assets_ok,
        "mandatory_om_documents_complete_and_verified":docs_ok,
        "mandatory_warranties_complete_and_verified":warranties_ok,
        "maintenance_plans_complete":maintenance_ok,
        "initial_inspections_complete_and_passed":inspections_ok,
        "critical_spares_defined":spares_ok,
        "professional_operations_acceptance_approved":professional,
        "operations_ready":ready,
        "automatic_operations_release":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--operations-profile",required=True)
    ap.add_argument("--handover-gate",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.operations_profile)
    handover_gate=readj(q.handover_gate) if q.handover_gate else None

    out=Path(q.output).resolve()
    if out.exists(): shutil.rmtree(out)
    for d in ("assets","om","warranties","maintenance","inspections","faults","service","spares","replacement","reports","digital_twin"):
        (out/d).mkdir(parents=True,exist_ok=True)

    assets=norm_assets(profile)
    docs=norm_docs(profile,"om_documents","OM")
    warranties=norm_warranties(profile)
    maintenance=norm_maintenance(profile)
    inspections=norm_inspections(profile)
    faults=norm_faults(profile)
    service=norm_service(profile)
    spares=norm_spares(profile)
    replacement=norm_replacement(profile)

    gate=evaluate(profile,assets,docs,warranties,maintenance,inspections,spares,handover_gate)

    csvw(out/"assets/asset_register.csv",
         ["asset_id","name","category","location","manufacturer","model","serial_number","commissioning_date","status","criticality","mandatory"],assets)
    csvw(out/"om/om_document_register.csv",
         ["record_id","asset_id","title","file_path","revision","mandatory","verified","verified_by"],docs)
    csvw(out/"warranties/warranty_register.csv",
         ["warranty_id","asset_id","provider","start_date","end_date","reference","mandatory","verified"],warranties)
    csvw(out/"maintenance/preventive_maintenance_register.csv",
         ["maintenance_id","asset_id","task","interval","responsible_party","procedure_reference","mandatory","complete"],maintenance)
    csvw(out/"inspections/inspection_register.csv",
         ["inspection_id","asset_id","inspection_type","date","status","result_reference","inspected_by","initial_required"],inspections)
    csvw(out/"faults/fault_register.csv",
         ["fault_id","asset_id","reported_date","severity","description","status","resolution_reference"],faults)
    csvw(out/"service/service_history_register.csv",
         ["service_id","asset_id","date","activity","provider","result","document_reference"],service)
    csvw(out/"spares/spare_parts_register.csv",
         ["spare_id","asset_id","part_number","description","minimum_stock","critical","supplier"],spares)
    csvw(out/"replacement/replacement_cycle_register.csv",
         ["replacement_id","asset_id","expected_life_years","replacement_year","budget_reference","strategy"],replacement)

    writej(out/"reports/operations_readiness_matrix.json",{
        "assets":assets,
        "om_documents":docs,
        "warranties":warranties,
        "maintenance_plans":maintenance,
        "inspections":inspections,
        "faults":faults,
        "service_history":service,
        "spare_parts":spares,
        "replacement_cycles":replacement,
        "release":gate
    })

    writej(out/"operations_release_gate.json",{
        "schema_version":"phoenix.operations-release-gate/7.3.0",
        "status":"UNLOCKED" if gate["operations_ready"] else "LOCKED",
        **gate,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("operations_ready","automatic_operations_release") and v is False]
    })

    writej(out/"digital_twin/operational_asset_twin_v7_3_0.json",{
        "schema_version":"phoenix.digital-twin-operational-assets/7.3.0",
        "project_id":project.get("project_id",""),
        "asset_count":len(assets),
        "om_document_count":len(docs),
        "warranty_count":len(warranties),
        "maintenance_plan_count":len(maintenance),
        "inspection_count":len(inspections),
        "fault_count":len(faults),
        "service_record_count":len(service),
        "spare_part_count":len(spares),
        "replacement_cycle_count":len(replacement),
        "operations_ready":gate["operations_ready"],
        "automatic_operations_release":False
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

    writej(out/"asset_fm_operations_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "operations_ready":gate["operations_ready"],
        "automatic_operations_release":False
    })

    print("ASSET INFORMATION, FACILITY MANAGEMENT, MAINTENANCE AND DIGITAL TWIN OPERATIONS ENGINE: PASSED")
    print("ASSET REGISTER: GENERATED")
    print("O&M DOCUMENT REGISTER: GENERATED")
    print("WARRANTY REGISTER: GENERATED")
    print("PREVENTIVE MAINTENANCE REGISTER: GENERATED")
    print("INSPECTION REGISTER: GENERATED")
    print("FAULT REGISTER: GENERATED")
    print("SERVICE HISTORY REGISTER: GENERATED")
    print("SPARE PARTS REGISTER: GENERATED")
    print("REPLACEMENT CYCLE REGISTER: GENERATED")
    print("OPERATIONS READINESS MATRIX: GENERATED")
    print("CENTRAL OPERATIONAL DIGITAL TWIN WRITEBACK: PASSED")
    print("AUTOMATIC OPERATIONS RELEASE: DISABLED")
    print("OPERATIONS-READY RELEASE: "+("UNLOCKED" if gate["operations_ready"] else "LOCKED"))

if __name__=="__main__":
    main()
