from __future__ import annotations
import argparse, hashlib, json, sys, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from phoenix.contract_administration import ContractAdministrationEngine
from phoenix.site_execution_qaqc import SiteExecutionQAQCEngine
from phoenix.commissioning_handover import CommissioningHandoverEngine
from phoenix.digital_twin_operations import DigitalTwinOperationsEngine
from phoenix.commercial_delivery_orchestrator import CommercialDeliveryOrchestrator, CommercialDeliveryExporter

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--output-dir",type=Path); args=parser.parse_args(argv)
    project={"project_id":"PHX-BB26-BB30-SELFTEST","project_name":"Phoenix Commercial Building Pilot"}
    bb26=ContractAdministrationEngine().create_report(project,
        contracts=[{"contract_id":"C1","awarded_amount":500000}],
        variations=[{"variation_id":"V1","contract_id":"C1","amount":10000,"status":"approved"}],
        payments=[{"payment_id":"P1","contract_id":"C1","certified_amount":150000}],
        rfis=[{"rfi_id":"R1","status":"answered"}],submittals=[{"submittal_id":"S1","status":"approved"}])
    bb27=SiteExecutionQAQCEngine().create_report(project,
        activities=[{"activity_id":"A1","weight":300000,"progress_percent":80},
                    {"activity_id":"A2","weight":200000,"progress_percent":50}],
        inspections=[{"inspection_id":"I1","result":"passed"}],
        ncrs=[{"ncr_id":"N1","severity":"minor","status":"closed"}],daily_logs=[{"log_id":"L1"}])
    bb28=CommissioningHandoverEngine().create_report(project,
        assets=[{"asset_id":"ASSET-1","as_built_complete":True}],
        commissioning_tests=[{"test_id":"T1","asset_id":"ASSET-1","result":"passed"}],
        handover_documents=[{"document_id":"D1","asset_id":"ASSET-1","document_type":"om_manual","status":"released"}])
    bb29=DigitalTwinOperationsEngine().create_report(project,
        assets=[{"asset_id":"ASSET-1","commissioned":True}],
        maintenance_plans=[{"plan_id":"MP1","asset_id":"ASSET-1","interval_days":365,"annual_cost":2500}],
        as_of_date="2026-01-01",forecast_years=10)

    names=["building_model","architectural_drawings","structural_design","quantity_takeoff","cost_estimation",
           "bim_coordination","construction_documentation","construction_planning","procurement_tendering"]
    upstream={name:{"project_id":project["project_id"],"blocking_issue_count":0,"passed":True} for name in names}
    upstream.update({"contract_administration":bb26,"site_qaqc":bb27,
                     "commissioning_handover":bb28,"digital_twin_operations":bb29})
    types=["3d_impression","structural_calculations","structural_report","building_drawings",
           "technical_specification","specification_drawings","cost_calculation","material_schedules","site_plan"]
    deliverables=[]
    for i,t in enumerate(types,1):
        digest=hashlib.sha256(f"{project['project_id']}|{t}|P01".encode()).hexdigest()
        deliverables.append({"deliverable_id":f"DEL-{i:03d}","deliverable_type":t,"status":"released",
                             "revision":"P01","file_name":f"{t}.pdf","sha256":digest})
    manifest=CommercialDeliveryOrchestrator().create_delivery_manifest(
        project,upstream_reports=upstream,deliverables=deliverables,release_requested=True)

    temp=None
    if args.output_dir is None:
        temp=tempfile.TemporaryDirectory(); output=Path(temp.name)
    else: output=args.output_dir
    paths=CommercialDeliveryExporter().export_all(manifest,output)
    with zipfile.ZipFile(paths["dossier"]) as z: names=set(z.namelist())
    dossier_valid={"commercial_building_delivery_manifest.json","commercial_deliverable_checklist.csv",
                   "commercial_delivery_readiness.html","checksums.sha256","PACKAGE_README.txt"}.issubset(names)
    passed=(bb26["contract_control_passed"] and bb27["site_quality_passed"] and bb28["handover_passed"]
            and bb29["operations_ready"] and manifest["commercial_package_ready"]
            and manifest["release_status"]=="released_for_commercial_pilot"
            and dossier_valid and all(p.is_file() for p in paths.values()))
    print(json.dumps({
        "status":"PASSED" if passed else "FAILED",
        "bb26_contract_control_passed":bb26["contract_control_passed"],
        "bb27_site_quality_passed":bb27["site_quality_passed"],
        "bb28_handover_passed":bb28["handover_passed"],
        "bb29_operations_ready":bb29["operations_ready"],
        "bb30_commercial_package_ready":manifest["commercial_package_ready"],
        "bb30_release_status":manifest["release_status"],
        "commercial_deliverable_count":len(manifest["deliverable_checklist"]),
        "dossier_valid":dossier_valid,"output_dir":str(output),
    },indent=2))
    if temp: temp.cleanup()
    return 0 if passed else 1

if __name__=="__main__": raise SystemExit(main())
