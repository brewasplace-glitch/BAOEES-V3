"""Generate real drawings and reports from the central model."""
from __future__ import annotations
import argparse,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from phoenix.production.real_drawings_reports import RealConceptProductionEngine
from phoenix.production.model_driven_adapter import derive_production_config
BASE=Path('configs/projects/moskee_bunschoten_real_concept_production_v1_0_0.json')
MODEL=Path('artifacts/bb35/pilot_1_moskee_bunschoten/central_geometric_project_model_v1_0_0/02_canonical_geometric_project_model.json')
def compare_trees(e:Path,a:Path)->list[str]:
    en=sorted(p.relative_to(e).as_posix() for p in e.rglob('*') if p.is_file());an=sorted(p.relative_to(a).as_posix() for p in a.rglob('*') if p.is_file())
    if en!=an:return sorted(set(en)^set(an))
    return [n for n in en if (e/n).read_bytes()!=(a/n).read_bytes()]
def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path);p.add_argument('--verify-against-artifacts',type=Path);p.add_argument('--expect-production-ready',action='store_true');args=p.parse_args(argv)
    temp=None
    if args.output_dir is None:temp=tempfile.TemporaryDirectory();out=Path(temp.name)
    else:out=args.output_dir
    base=json.loads((ROOT/BASE).read_text(encoding='utf-8'));model=json.loads((ROOT/MODEL).read_text(encoding='utf-8'));config=derive_production_config(base,model)
    result=RealConceptProductionEngine(config).produce(out);summary=result['summary'];m=[];match=None
    if args.verify_against_artifacts:m=compare_trees(args.verify_against_artifacts,out);match=not m
    passed=(summary['status']=='REAL_CONCEPT_DRAWINGS_AND_REPORTS_GENERATED' and summary['model_id']==model['model_id'] and summary['model_fingerprint_sha256']==model['model_fingerprint_sha256'] and summary['geometry_source']=='central_geometric_project_model_v1_0_0' and summary['drawing_sheet_count']==10 and summary['report_count']==6 and summary['cross_checks_passed']==14 and summary['parking_basis_spaces']==225 and summary['gross_area_m2']==140.0 and match is not False)
    print(json.dumps({'execution_status':'PASSED' if passed else 'FAILED','production_status':summary['status'],'issue_id':summary['issue_id'],'model_id':summary['model_id'],'model_fingerprint_sha256':summary['model_fingerprint_sha256'],'geometry_source':summary['geometry_source'],'drawing_sheet_count':summary['drawing_sheet_count'],'report_count':summary['report_count'],'cross_checks_passed':summary['cross_checks_passed'],'output_file_count':summary['output_file_count'],'artifacts_match':match,'artifact_mismatch_count':len(m),'artifact_mismatch_paths':m,'output_dir':str(out)},ensure_ascii=False,indent=2))
    if temp is not None:temp.cleanup()
    if args.expect_production_ready:return 0 if passed else 1
    return 0 if passed else 2
if __name__=='__main__':raise SystemExit(main())
