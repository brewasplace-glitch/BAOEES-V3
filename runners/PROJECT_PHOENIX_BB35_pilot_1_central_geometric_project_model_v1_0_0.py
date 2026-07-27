"""Run the BB35 central geometric project model engine."""
from __future__ import annotations
import argparse, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from phoenix.model.central_geometric_project_model import CentralGeometricProjectModelEngine, CentralGeometricProjectModelExporter
CONFIG_REL=Path('configs/projects/moskee_bunschoten_central_geometric_model_v1_0_0.json')
def load_config(): return json.loads((ROOT/CONFIG_REL).read_text(encoding='utf-8'))
def compare_trees(expected:Path,actual:Path)->list[str]:
    e=sorted(p.relative_to(expected).as_posix() for p in expected.rglob('*') if p.is_file()); a=sorted(p.relative_to(actual).as_posix() for p in actual.rglob('*') if p.is_file())
    if e!=a:return sorted(set(e)^set(a))
    return [name for name in e if (expected/name).read_bytes()!=(actual/name).read_bytes()]
def main(argv=None)->int:
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir',type=Path); parser.add_argument('--verify-against-artifacts',type=Path); parser.add_argument('--expect-model-valid',action='store_true'); args=parser.parse_args(argv)
    temporary=None
    if args.output_dir is None: temporary=tempfile.TemporaryDirectory(); output_dir=Path(temporary.name)
    else: output_dir=args.output_dir
    result=CentralGeometricProjectModelEngine(load_config()).build(); paths=CentralGeometricProjectModelExporter().export_all(result,output_dir); summary=json.loads(paths['summary'].read_text(encoding='utf-8'))
    mismatches=[]; artifacts_match=None
    if args.verify_against_artifacts: mismatches=compare_trees(args.verify_against_artifacts,output_dir); artifacts_match=not mismatches
    passed=(summary['status']=='CENTRAL_GEOMETRIC_PROJECT_MODEL_GENERATED' and summary['object_count']==299 and summary['parking_bay_count']==225 and summary['geometry_check_count']==22 and summary['geometry_checks_passed']==22 and summary['all_geometry_checks_passed'] and summary['extension_gross_area_m2']==140.0 and summary['model_is_single_source_for_drawings_reports_calculations'] and artifacts_match is not False)
    output={'execution_status':'PASSED' if passed else 'FAILED','model_status':summary['status'],'model_id':summary['model_id'],'model_fingerprint_sha256':summary['model_fingerprint_sha256'],'object_count':summary['object_count'],'space_count':summary['space_count'],'wall_count':summary['wall_count'],'opening_count':summary['opening_count'],'parking_bay_count':summary['parking_bay_count'],'geometry_checks_passed':summary['geometry_checks_passed'],'output_file_count':sum(1 for p in output_dir.rglob('*') if p.is_file()),'artifacts_match':artifacts_match,'artifact_mismatch_count':len(mismatches),'artifact_mismatch_paths':mismatches,'output_dir':str(output_dir),'next_gate':'Use this model fingerprint as the mandatory geometry source for drawings, reports and calculation sheets.'}
    print(json.dumps(output,ensure_ascii=False,indent=2))
    if temporary is not None: temporary.cleanup()
    if args.expect_model_valid:return 0 if passed else 1
    return 0 if passed else 2
if __name__=='__main__': raise SystemExit(main())
