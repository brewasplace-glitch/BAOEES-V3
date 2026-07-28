"""Run Project Phoenix model-driven calculation workbook v1.0.0."""
from __future__ import annotations
import argparse, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from phoenix.calculations.model_driven_workbook import ModelDrivenCalculationEngine, CalculationArtifactExporter

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--verify-against-artifacts',type=Path)
    parser.add_argument('--expect-calculations-valid',action='store_true')
    args=parser.parse_args(argv)
    config=json.loads((ROOT/'configs/projects/moskee_bunschoten_model_driven_calculation_workbook_v1_0_0.json').read_text(encoding='utf-8'))
    result=ModelDrivenCalculationEngine().evaluate(repository=ROOT,config=config)
    temp=None
    if args.output_dir is None:
        temp=tempfile.TemporaryDirectory(); output=Path(temp.name)
    else: output=args.output_dir
    paths=CalculationArtifactExporter().export_all(result,output)
    mismatch=[]; artifacts_match=None
    if args.verify_against_artifacts:
        expected_root=args.verify_against_artifacts
        expected=sorted(p.relative_to(expected_root).as_posix() for p in expected_root.rglob('*') if p.is_file())
        actual=sorted(p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file())
        if expected!=actual: mismatch=sorted(set(expected)^set(actual))
        else: mismatch=[rel for rel in expected if (expected_root/rel).read_bytes()!=(output/rel).read_bytes()]
        artifacts_match=not mismatch
    gates=result['gates']
    valid=(result['status']=='MODEL_DRIVEN_CONCEPT_CALCULATIONS_GENERATED' and result['metrics']['calculation_category_count']==8 and result['metrics']['calculation_count']==32 and result['metrics']['quality_check_count']==18 and result['metrics']['quality_checks_passed']==18 and gates['calculation_workbook_generated'] and gates['model_traceability_passed'] and gates['calculation_quality_checks_passed'] and gates['concept_calculation_issue_allowed'] and not gates['final_permit_ready_generation_allowed'] and not gates['bb36_production_release_allowed'])
    if artifacts_match is False: valid=False
    payload={
      'execution_status':'PASSED' if valid else 'FAILED',
      'status':result['status'],
      'model_id':result['model_id'],
      'model_fingerprint_sha256':result['model_fingerprint_sha256'],
      'input_count':result['metrics']['input_count'],
      'calculation_count':result['metrics']['calculation_count'],
      'calculation_category_count':result['metrics']['calculation_category_count'],
      'traceability_link_count':result['metrics']['traceability_link_count'],
      'quality_check_count':result['metrics']['quality_check_count'],
      'quality_checks_passed':result['metrics']['quality_checks_passed'],
      'professional_blocker_count':result['metrics']['professional_blocker_count'],
      'parking_capacity_spaces':result['metrics']['parking_capacity_spaces'],
      'workbook_sheet_count':13,
      'artifacts_match':artifacts_match,
      'artifact_mismatch_count':len(mismatch),
      'artifact_mismatch_paths':mismatch,
      'output_file_count':sum(1 for p in output.rglob('*') if p.is_file()),
      'outputs':{k:str(v) for k,v in sorted(paths.items())},
      'final_permit_ready_generation_allowed':gates['final_permit_ready_generation_allowed'],
      'bb36_production_release_allowed':gates['bb36_production_release_allowed'],
    }
    print(json.dumps(payload,indent=2,ensure_ascii=False))
    if temp: temp.cleanup()
    if args.expect_calculations_valid: return 0 if valid else 1
    return 0 if valid else 2
if __name__=='__main__': raise SystemExit(main())
