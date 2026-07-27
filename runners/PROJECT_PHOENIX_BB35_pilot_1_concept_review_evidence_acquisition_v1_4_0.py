\
"""Generate and verify BB35 Pilot 1 concept review and evidence requests."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.concept_review_evidence_acquisition import (
    MoskeeConceptReviewEvidenceAcquisition,
)


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def file_map(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--verify-against-artifacts', type=Path)
    parser.add_argument('--expect-evidence-open', action='store_true')
    args = parser.parse_args(argv)

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix='PHOENIX_HBM_REVIEW_')
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    concept_root = (
        ROOT
        / 'artifacts/bb35/pilot_1_moskee_bunschoten/'
        'concept_generation_v1_3_3'
    )
    result = MoskeeConceptReviewEvidenceAcquisition().generate(
        project_config=load('configs/projects/moskee_bunschoten_bb35_pilot_1.json'),
        verified_inputs=load(
            'inputs/pilots/moskee_bunschoten/'
            'verified_inputs_register_v1_2_0.json'
        ),
        concept_root=concept_root,
        output_dir=output_dir,
    )

    mismatches = []
    artifacts_match = None
    if args.verify_against_artifacts is not None:
        generated = file_map(output_dir)
        expected = file_map(args.verify_against_artifacts)
        mismatches = sorted(
            set(generated) ^ set(expected)
            | {
                name
                for name in set(generated) & set(expected)
                if generated[name] != expected[name]
            }
        )
        artifacts_match = not mismatches

    expected_open = (
        result['status'] == 'CONCEPT_REVIEW_COMPLETE_EVIDENCE_ACQUISITION_OPEN'
        and result['concept_review_complete']
        and result['concept_package_accepted_with_conditions']
        and result['open_evidence_request_count'] == 8
        and result['valid_concept_artifact_count'] == result['concept_artifact_count']
        and result['concept_development_allowed']
        and not result['final_generation_allowed']
        and not result['bb36_unlock_allowed']
        and (artifacts_match is not False)
    )

    print(json.dumps({
        'status': 'PASSED' if expected_open else 'FAILED',
        'pilot_id': result['pilot_id'],
        'project_id': result['project_id'],
        'review_status': result['status'],
        'concept_review_complete': result['concept_review_complete'],
        'concept_package_accepted_with_conditions': result['concept_package_accepted_with_conditions'],
        'valid_concept_artifact_count': result['valid_concept_artifact_count'],
        'concept_artifact_count': result['concept_artifact_count'],
        'review_item_count': result['review_item_count'],
        'finding_count': result['finding_count'],
        'risk_count': result['risk_count'],
        'open_evidence_request_count': result['open_evidence_request_count'],
        'output_count': result['output_count'],
        'artifacts_match': artifacts_match,
        'artifact_mismatch_count': len(mismatches),
        'artifact_mismatch_paths': mismatches,
        'concept_development_allowed': result['concept_development_allowed'],
        'final_generation_allowed': result['final_generation_allowed'],
        'bb36_unlock_allowed': result['bb36_unlock_allowed'],
        'output_dir': str(output_dir),
    }, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_evidence_open:
        return 0 if expected_open else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
