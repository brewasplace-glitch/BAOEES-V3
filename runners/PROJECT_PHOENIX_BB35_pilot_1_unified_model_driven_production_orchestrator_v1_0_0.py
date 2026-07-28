"""Run unified model-driven production orchestration v1.0.0."""
from __future__ import annotations
import argparse,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from phoenix.orchestration.unified_model_driven_production import UnifiedProductionOrchestrator

def compare_trees(expected:Path,actual:Path)->list[str]:
    e=sorted(p.relative_to(expected).as_posix() for p in expected.rglob('*') if p.is_file());a=sorted(p.relative_to(actual).as_posix() for p in actual.rglob('*') if p.is_file())
    if e!=a:return sorted(set(e)^set(a))
    return [name for name in e if (expected/name).read_bytes()!=(actual/name).read_bytes()]
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path);p.add_argument('--verify-against-artifacts',type=Path);p.add_argument('--expect-release-ready',action='store_true');p.add_argument('--force-all',action='store_true');p.add_argument('--ignore-previous-state',action='store_true');p.add_argument('--no-execute-changed',action='store_true');args=p.parse_args(argv)
    config=json.loads((ROOT/'configs/projects/moskee_bunschoten_unified_production_orchestrator_v1_0_0.json').read_text(encoding='utf-8'))
    temp=None
    if args.output_dir is None:temp=tempfile.TemporaryDirectory();out=Path(temp.name)
    else:out=args.output_dir
    result=UnifiedProductionOrchestrator(ROOT,config).execute(out,execute_changed=not args.no_execute_changed,force_all=args.force_all,ignore_previous=args.ignore_previous_state);release=result['release'];m=[];match=None
    if args.verify_against_artifacts:m=compare_trees(args.verify_against_artifacts,out);match=not m
    passed=(release['status']=='UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_READY' and release['cross_check_count']==22 and release['cross_checks_passed']==22 and release['all_cross_checks_passed'] and release['drawing_sheet_count']==10 and release['report_count']==6 and release['calculation_count']==32 and release['parking_basis_spaces']==225 and release['professional_blocker_count']==6 and release['gates']['all_products_current'] and release['gates']['unified_concept_issue_ready'] and not release['gates']['final_permit_ready_generation_allowed'] and not release['gates']['bb36_production_release_allowed'] and match is not False)
    payload={'execution_status':'PASSED' if passed else 'FAILED','status':release['status'],'revision_code':release['revision_code'],'run_mode':release['run_mode'],'model_id':release['model_id'],'model_fingerprint_sha256':release['model_fingerprint_sha256'],'direct_change_count':release['change_count'],'regenerated_component_count':release['regenerated_component_count'],'reused_component_count':release['reused_component_count'],'drawing_sheet_count':release['drawing_sheet_count'],'report_count':release['report_count'],'calculation_count':release['calculation_count'],'cross_check_count':release['cross_check_count'],'cross_checks_passed':release['cross_checks_passed'],'professional_blocker_count':release['professional_blocker_count'],'final_permit_ready_generation_allowed':release['gates']['final_permit_ready_generation_allowed'],'bb36_production_release_allowed':release['gates']['bb36_production_release_allowed'],'artifacts_match':match,'artifact_mismatch_count':len(m),'artifact_mismatch_paths':m,'output_file_count':sum(1 for x in out.rglob('*') if x.is_file()),'outputs':{k:str(v) for k,v in sorted(result['paths'].items())},'next_gate':release['next_gate']}
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    if temp:temp.cleanup()
    if args.expect_release_ready:return 0 if passed else 1
    return 0 if passed else 2
if __name__=='__main__':raise SystemExit(main())
