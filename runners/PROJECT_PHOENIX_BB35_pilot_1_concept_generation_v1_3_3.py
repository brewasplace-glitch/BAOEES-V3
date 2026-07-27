\
"""Generate and optionally verify the BB35 Moskee Bunschoten concept package."""

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

from phoenix.bb35_pilots.moskee_bunschoten.concept_generation import (
    MoskeeBunschotenConceptGenerator,
)


def _load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*')) if path.is_file()
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--verify-against-artifacts', type=Path)
    args = parser.parse_args(argv)

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    result = MoskeeBunschotenConceptGenerator().generate(
        config=_load('configs/projects/moskee_bunschoten_bb35_pilot_1.json'),
        verified_inputs=_load('inputs/pilots/moskee_bunschoten/verified_inputs_register_v1_2_0.json'),
        output_dir=output_dir,
    )

    artifacts_match = None
    mismatch_paths: list[str] = []
    if args.verify_against_artifacts is not None:
        generated = _tree_hashes(output_dir)
        committed = _tree_hashes(args.verify_against_artifacts)
        artifacts_match = generated == committed
        mismatch_paths = sorted(
            path for path in set(generated) | set(committed)
            if generated.get(path) != committed.get(path)
        )

    passed = (
        result['status'] == 'CONCEPT_PACKAGE_READY_PENDING_EXTERNAL_TECHNICAL_EVIDENCE'
        and result['gross_area_m2'] == 140.0
        and result['space_count'] == 15
        and result['output_count'] >= 25
        and not result['final_generation_allowed']
        and not result['bb36_unlock_allowed']
        and (artifacts_match is not False)
    )

    print(json.dumps({
        'status': 'PASSED' if passed else 'FAILED',
        'pilot_id': result['pilot_id'],
        'project_id': result['project_id'],
        'concept_status': result['status'],
        'status_notice': result['status_notice'],
        'gross_area_m2': result['gross_area_m2'],
        'space_count': result['space_count'],
        'assumption_count': result['assumption_count'],
        'risk_count': result['risk_count'],
        'permit_item_count': result['permit_item_count'],
        'output_count': result['output_count'],
        'artifacts_match': artifacts_match,
        'artifact_mismatch_count': len(mismatch_paths),
        'artifact_mismatch_paths': mismatch_paths,
        'final_generation_allowed': result['final_generation_allowed'],
        'bb36_unlock_allowed': result['bb36_unlock_allowed'],
        'output_dir': str(output_dir),
    }, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
