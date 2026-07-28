"""Run BB35 Pilot 1 professional evidence intake validation and closure gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.professional_evidence_intake_closure_gate import (
    ProfessionalEvidenceIntakeClosureExporter,
    ProfessionalEvidenceIntakeClosureGate,
)

CONFIG_PATH = ROOT / 'configs/projects/moskee_bunschoten_professional_evidence_intake_closure_gate_v2_3_0.json'
DEFAULT_OUTPUT = ROOT / 'artifacts/bb35/pilot_1_moskee_bunschoten/professional_evidence_intake_closure_gate_v2_3_0'


def file_map(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root')
    parser.add_argument('--output-dir')
    parser.add_argument('--verify-against-artifacts')
    parser.add_argument('--expect-gate-operational', action='store_true')
    parser.add_argument('--expect-all-closed', action='store_true')
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    input_root = Path(args.input_root) if args.input_root else ROOT / config['intake_root']
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT
    gate = ProfessionalEvidenceIntakeClosureGate(config)
    exporter = ProfessionalEvidenceIntakeClosureExporter(config)
    report = gate.evaluate(input_root)
    paths = exporter.export_all(report, output_dir)

    match = None
    mismatch_paths: list[str] = []
    if args.verify_against_artifacts:
        reference = Path(args.verify_against_artifacts)
        actual_map = file_map(output_dir)
        expected_map = file_map(reference)
        names = sorted(set(actual_map) | set(expected_map))
        mismatch_paths = [name for name in names if actual_map.get(name) != expected_map.get(name)]
        match = not mismatch_paths

    expectation_ok = report['intake_gate_operational']
    if args.expect_all_closed:
        expectation_ok = expectation_ok and report['professional_evidence_closure_gate_passed']
    if match is False:
        expectation_ok = False

    result = {
        'execution_status': 'PASSED' if expectation_ok else 'FAILED',
        'status': report['status'],
        'project_id': report['project_id'],
        'evaluation_revision': report['evaluation_revision'],
        'intake_gate_operational': report['intake_gate_operational'],
        'requirement_count': report['requirement_count'],
        'evidence_accepted_count': report['evidence_accepted_count'],
        'evidence_open_count': report['evidence_open_count'],
        'professional_evidence_closure_gate_passed': report['professional_evidence_closure_gate_passed'],
        'req107_status': report['req107_status'],
        'technical_regeneration_required': report['technical_regeneration_required'],
        'permit_ready_release_allowed': report['permit_ready_release_allowed'],
        'tender_ready_release_allowed': report['tender_ready_release_allowed'],
        'execution_ready_release_allowed': report['execution_ready_release_allowed'],
        'bb36_production_release_allowed': report['bb36_production_release_allowed'],
        'validation_finding_count': len(report['validation_findings']),
        'artifacts_match': match,
        'artifact_mismatch_count': len(mismatch_paths),
        'artifact_mismatch_paths': mismatch_paths,
        'output_file_count': sum(1 for path in output_dir.rglob('*') if path.is_file()),
        'outputs': {key: str(value) for key, value in sorted(paths.items())},
        'next_gate': report['next_gate'],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if expectation_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
