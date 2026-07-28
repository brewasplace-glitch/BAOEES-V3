"""Run regional profiles and sketch-input recognition v1.0.1 cross-platform recovery."""
from __future__ import annotations
import argparse, csv, hashlib, json, shutil, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from phoenix.structural.regional_profiles import RegionalStructuralProfileRegistry
from phoenix.structural.sketch_input_recognition import SketchInputRecognitionEngine, render_preview_svg
from phoenix.structural.reinforced_concrete_beam import ReinforcedConcreteBeamDesignEngine, ReinforcedConcreteBeamDesignExporter

PROFILE_REGISTRY = ROOT / 'configs/structural/regional_structural_profiles_v1_0_0.json'
BASE_CONFIG = ROOT / 'configs/structural/reinforced_concrete_beam_example_v1_0_0.json'
DEFAULT_SKETCH = ROOT / 'examples/structural_sketch_input/sample_rc_beam_sketch_SUR.png'
DEFAULT_CONFIRMATION = ROOT / 'examples/structural_sketch_input/sample_rc_beam_sketch_SUR_confirmation.json'
DEFAULT_ENGINEER = ROOT / 'examples/structural_sketch_input/sample_SUR_engineer_basis_confirmation.json'


def canonical_json(value): return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def export_all(output: Path, recognition, profile, beam_cfg, design_result):
    if output.exists(): shutil.rmtree(output)
    output.mkdir(parents=True)
    (output/'01_sketch_input_summary.json').write_text(canonical_json({
        'status': 'SKETCH_INPUT_READY_FOR_PRELIMINARY_BEAM_DESIGN' if recognition['input_ready'] else 'CONFIRMATION_REQUIRED',
        'jurisdiction': profile['jurisdiction'], 'jurisdiction_code': profile['jurisdiction_code'],
        'input_ready': recognition['input_ready'], 'text_source': recognition['text_source'],
        'recognized_field_count': len(recognition['candidate']['fields']),
        'distributed_load_count': len(recognition['resolved']['distributed_loads']),
        'point_load_count': len(recognition['resolved']['point_loads']),
        'final_structural_release_allowed': False,
    }), encoding='utf-8', newline='\n')
    (output/'02_selected_jurisdiction_profile.json').write_text(canonical_json(profile), encoding='utf-8', newline='\n')
    (output/'03_recognition_result.json').write_text(canonical_json(recognition), encoding='utf-8', newline='\n')
    with (output/'04_recognition_confidence_register.csv').open('w', newline='', encoding='utf-8') as fh:
        writer=csv.writer(fh); writer.writerow(['field','value','confidence','evidence'])
        for name,row in sorted(recognition['candidate']['fields'].items()): writer.writerow([name,row['value'],row['confidence'],row['evidence']])
        for row in recognition['candidate']['distributed_loads']: writer.writerow([row['load_id'],row['characteristic_kn_m'],row['confidence'],row['evidence']])
        for row in recognition['candidate']['point_loads']: writer.writerow([row['load_id'],row['characteristic_kn'],row['confidence'],row['evidence']])
    (output/'05_normalized_rc_beam_input.json').write_text(canonical_json(beam_cfg), encoding='utf-8', newline='\n')
    (output/'06_interpretation_preview.svg').write_text(render_preview_svg(recognition), encoding='utf-8', newline='\n')
    report = f"""# Phoenix regional structural profile and sketch-input validation\n\n- Jurisdiction: {profile['jurisdiction']} ({profile['jurisdiction_code']})\n- OCR/text source: {recognition['text_source']}\n- User confirmation gate: {'PASSED' if recognition['input_ready'] else 'BLOCKED'}\n- Design standard status: {profile['structural_standard_status']}\n- Final release policy: {profile['final_release_policy']}\n- Sample design technical checks: {design_result['metrics']['technical_checks_passed']} / {design_result['metrics']['technical_check_count']} passed\n\nThe regional profile is a controlled context profile, not a legal declaration that one structural standard is automatically accepted. Final use requires the competent local engineer and authority.\n"""
    (output/'07_validation_report.md').write_text(report, encoding='utf-8', newline='\n')
    profile_rows=''.join(f"<tr><td>{p['jurisdiction_code']}</td><td>{p['jurisdiction']}</td><td>{p['structural_standard_status']}</td></tr>" for p in RegionalStructuralProfileRegistry(PROFILE_REGISTRY).describe())
    values=recognition['resolved']['values']
    html=f"""<!doctype html><html><head><meta charset="utf-8"><title>Phoenix sketch input</title><style>body{{font-family:Arial;max-width:1150px;margin:30px auto;color:#172033}}.card{{border:1px solid #ccd3df;border-radius:12px;padding:18px;margin:15px 0}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3df;padding:9px;text-align:left}}.ok{{color:#087443;font-weight:bold}}.warn{{color:#a55b00;font-weight:bold}}code{{background:#f3f5f8;padding:2px 5px}}</style></head><body><h1>Project Phoenix — Regional Structural Profiles & Sketch Input</h1><div class="card"><h2>Sample recognition</h2><p class="ok">USER CONFIRMATION GATE PASSED</p><p>Jurisdiction: <b>{profile['jurisdiction']}</b></p><p>Span {values['span_m']} m; section {values['width_mm']} × {values['height_mm']} mm; concrete {values['concrete_class']}; steel {values['reinforcement_class']}.</p><p>Sketch formats: PNG, JPG, JPEG, BMP, TIFF and PDF. OCR priority: explicit text → sidecar → Tesseract → Windows OCR → PDF text → manual confirmation.</p><p class="warn">Final structural release remains blocked until local engineer approval.</p></div><div class="card"><object data="06_interpretation_preview.svg" type="image/svg+xml" width="100%"></object></div><div class="card"><h2>Available profiles</h2><table><tr><th>Code</th><th>Jurisdiction</th><th>Standard status</th></tr>{profile_rows}</table></div><div class="card"><h2>Generated design</h2><p>Open <code>beam_design/09_beam_design_dashboard.html</code>, the XLSX workbook, PDF report or DXF/SVG details.</p></div></body></html>"""
    (output/'08_sketch_input_dashboard.html').write_text(html, encoding='utf-8', newline='\n')
    design_dir=output/'beam_design'; ReinforcedConcreteBeamDesignExporter(design_result).export_all(design_dir)
    checksum_lines=[]
    for p in sorted(output.rglob('*')):
        if p.is_file() and p.name!='checksums.sha256': checksum_lines.append(f"{sha(p)}  {p.relative_to(output).as_posix()}")
    (output/'checksums.sha256').write_text('\n'.join(checksum_lines)+'\n', encoding='utf-8', newline='\n')
    return {'output_file_count': sum(1 for p in output.rglob('*') if p.is_file()), 'design_check_count': design_result['metrics']['technical_check_count'], 'design_checks_passed': design_result['metrics']['technical_checks_passed']}


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--sketch',type=Path,default=DEFAULT_SKETCH); ap.add_argument('--jurisdiction',default='SUR'); ap.add_argument('--ocr-text-file',type=Path); ap.add_argument('--confirmation-json',type=Path,default=DEFAULT_CONFIRMATION); ap.add_argument('--engineer-confirmation-json',type=Path,default=DEFAULT_ENGINEER); ap.add_argument('--output-dir',type=Path); ap.add_argument('--verify-against-artifacts',type=Path); ap.add_argument('--expect-input-ready',action='store_true'); args=ap.parse_args(argv)
    sketch=args.sketch if args.sketch.is_absolute() else ROOT/args.sketch
    explicit=args.ocr_text_file.read_text(encoding='utf-8') if args.ocr_text_file else None
    confirmation=json.loads((args.confirmation_json if args.confirmation_json.is_absolute() else ROOT/args.confirmation_json).read_text(encoding='utf-8'))
    engineer=json.loads((args.engineer_confirmation_json if args.engineer_confirmation_json.is_absolute() else ROOT/args.engineer_confirmation_json).read_text(encoding='utf-8'))
    registry=RegionalStructuralProfileRegistry(PROFILE_REGISTRY); profile=registry.get(args.jurisdiction)
    basis_errors=registry.validate_confirmation(args.jurisdiction, engineer)
    recognition=SketchInputRecognitionEngine(ROOT).recognize(sketch,args.jurisdiction,explicit,confirmation)
    base=json.loads(BASE_CONFIG.read_text(encoding='utf-8'))
    beam_cfg=SketchInputRecognitionEngine(ROOT).to_beam_config(recognition,profile,engineer,base)
    design=ReinforcedConcreteBeamDesignEngine().evaluate(beam_cfg)
    temp=None
    if args.output_dir is None: temp=tempfile.TemporaryDirectory(); out=Path(temp.name)
    else: out=args.output_dir
    info=export_all(out,recognition,profile,beam_cfg,design)
    mismatch=[]; match=None
    if args.verify_against_artifacts:
        expected=args.verify_against_artifacts if args.verify_against_artifacts.is_absolute() else ROOT/args.verify_against_artifacts
        exp=sorted(p.relative_to(expected).as_posix() for p in expected.rglob('*') if p.is_file()); act=sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file())
        mismatch=sorted(set(exp)^set(act))
        if not mismatch:
            mismatch=[rel for rel in exp if (expected/rel).read_bytes()!=(out/rel).read_bytes()]
        match=not mismatch
    status='PASSED' if recognition['input_ready'] and not basis_errors and design['metrics']['technical_checks_passed']==design['metrics']['technical_check_count'] and (match is not False) else 'FAILED'
    result={'execution_status':status,'jurisdiction_code':args.jurisdiction,'jurisdiction':profile['jurisdiction'],'profile_count':len(registry.describe()),'input_ready':recognition['input_ready'],'text_source':recognition['text_source'],'recognized_field_count':len(recognition['candidate']['fields']),'distributed_load_count':len(recognition['resolved']['distributed_loads']),'point_load_count':len(recognition['resolved']['point_loads']),'engineer_basis_errors':basis_errors,'design_checks_passed':info['design_checks_passed'],'design_check_count':info['design_check_count'],'output_file_count':info['output_file_count'],'artifacts_match':match,'artifact_mismatch_paths':mismatch,'final_structural_release_allowed':False,'next_gate':'Use a real uploaded sketch, confirm all recognized values and obtain local engineer approval for the selected jurisdiction.'}
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if status=='PASSED' else 1
if __name__=='__main__': raise SystemExit(main())
