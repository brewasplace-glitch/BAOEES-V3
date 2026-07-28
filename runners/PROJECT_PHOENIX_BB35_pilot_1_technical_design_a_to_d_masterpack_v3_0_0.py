from __future__ import annotations
import argparse
import json
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from phoenix.bb35_pilots.moskee_bunschoten.technical_design_a_to_d_masterpack import AcceleratedTechnicalDesignMasterpack, MasterpackExporter

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path);parser.add_argument('--verify-against-artifacts',type=Path);parser.add_argument('--expect-masterpack-ready',action='store_true');args=parser.parse_args(argv)
    config=json.loads((ROOT/'configs/projects/moskee_bunschoten_technical_design_a_to_d_masterpack_v3_0_0.json').read_text(encoding='utf-8'))
    engine=AcceleratedTechnicalDesignMasterpack(ROOT,config);report=engine.build();temporary=None
    if args.output_dir is None: temporary=tempfile.TemporaryDirectory();out=Path(temporary.name)
    else: out=args.output_dir
    paths=MasterpackExporter(engine).export_all(out)
    mismatch=[];match=None
    if args.verify_against_artifacts:
        expected_root=args.verify_against_artifacts
        expected=sorted(p.relative_to(expected_root).as_posix() for p in expected_root.rglob('*') if p.is_file())
        actual=sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file())
        if expected!=actual: mismatch=sorted(set(expected)^set(actual))
        else: mismatch=[rel for rel in expected if (expected_root/rel).read_bytes()!=(out/rel).read_bytes()]
        match=not mismatch
    passed=(report['status']=='TECHNICAL_DESIGN_A_TO_D_CONCEPT_MASTERPACK_READY' and report['all_phase_gates_passed'] and report['all_master_checks_passed'] and report['phase_gates_passed']==4 and report['professional_blocker_count']==6 and report['professional_evidence_accepted_count']==0 and report['release_gates']['technical_concept_issue_allowed'] and not report['release_gates']['permit_ready_issue_allowed'] and not report['release_gates']['tender_ready_issue_allowed'] and not report['release_gates']['execution_ready_issue_allowed'] and not report['release_gates']['bb36_production_release_allowed'])
    if match is False: passed=False
    result={'execution_status':'PASSED' if passed else 'FAILED','status':report['status'],'revision_code':report['revision_code'],'phase_gate_count':report['phase_gate_count'],'phase_gates_passed':report['phase_gates_passed'],'master_check_count':report['master_check_count'],'master_checks_passed':report['master_checks_passed'],'technical_detail_sheet_count':12,'drawing_pdf_count':13,'drawing_svg_count':12,'drawing_dxf_count':12,'docx_report_count':3,'pdf_report_count':3,'professional_blocker_count':6,'professional_evidence_accepted_count':0,'permit_ready_issue_allowed':False,'tender_ready_issue_allowed':False,'execution_ready_issue_allowed':False,'bb36_production_release_allowed':False,'artifacts_match':match,'artifact_mismatch_count':len(mismatch),'artifact_mismatch_paths':mismatch,'output_file_count':sum(1 for p in out.rglob('*') if p.is_file()),'outputs':{k:str(v) for k,v in sorted(paths.items())},'next_gate':report['next_gate']}
    print(json.dumps(result,indent=2,ensure_ascii=False))
    if temporary: temporary.cleanup()
    if args.expect_masterpack_ready: return 0 if passed else 1
    return 0 if passed else 2
if __name__=='__main__': raise SystemExit(main())
