"""Run BB35 integrated concept dossier generation v2.0.2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.bb35_pilots.moskee_bunschoten.integrated_concept_dossier import (
    IntegratedConceptDossierEngine,
    IntegratedConceptDossierExporter,
    load_source_manifest_snapshot,
)

SOURCE_ROOT = ROOT / (
    "artifacts/bb35/pilot_1_moskee_bunschoten/"
    "full_concept_evidence_simulation_v1_9_0"
)
SOURCE_MANIFEST_SNAPSHOT = ROOT / (
    "inputs/pilots/moskee_bunschoten/"
    "integrated_concept_dossier_source_manifest_snapshot_v2_0_2.json"
)


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load_csv(relative: str):
    with (ROOT / relative).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))



def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-against-artifacts", type=Path)
    parser.add_argument("--expect-dossier-ready", action="store_true")
    args = parser.parse_args(argv)

    base = "artifacts/bb35/pilot_1_moskee_bunschoten/full_concept_evidence_simulation_v1_9_0/"
    report = IntegratedConceptDossierEngine().evaluate(
        simulation_summary=load_json(base + "01_full_concept_simulation_summary.json"),
        concept_register=load_json(base + "02_integrated_concept_register.json"),
        gate_status=load_json(base + "06_gate_status.json"),
        assumptions=load_csv(base + "03_assumptions_register.csv"),
        handoffs=load_csv(base + "04_cross_discipline_handoff_matrix.csv"),
        checks=load_csv(base + "05_consistency_checks.csv"),
        req102_geometry=load_json(base + "REQ-102/02_REQ_102_simulated_geometry.json"),
        req103_structure=load_json(base + "REQ-103/02_REQ_103_structural_scheme.json"),
        req104_foundation=load_json(base + "REQ-104/03_REQ_104_foundation_concept_calculation.json"),
        req105_fire=load_json(base + "REQ-105/02_REQ_105_fire_egress_concept.json"),
        req106_parking=load_json(base + "REQ-106/02_REQ_106_capacity_correction.json"),
        req107_closure=load_json(base + "REQ-107/01_REQ_107_closure_record.json"),
        req108_gap=load_json(base + "REQ-108/06_REQ_108_evidence_gap.json"),
        source_files=load_source_manifest_snapshot(
            SOURCE_MANIFEST_SNAPSHOT, SOURCE_ROOT
        ),
        config=load_json("configs/projects/moskee_bunschoten_integrated_concept_dossier_v2_0_2.json"),
    )

    temporary = None
    if args.output_dir is None:
        temporary = tempfile.TemporaryDirectory()
        output_dir = Path(temporary.name)
    else:
        output_dir = args.output_dir

    paths = IntegratedConceptDossierExporter().export_all(report, output_dir)

    mismatch_paths = []
    artifacts_match = None
    if args.verify_against_artifacts:
        expected_root = args.verify_against_artifacts
        expected = sorted(
            path.relative_to(expected_root).as_posix()
            for path in expected_root.rglob("*") if path.is_file()
        )
        actual = sorted(
            path.relative_to(output_dir).as_posix()
            for path in output_dir.rglob("*") if path.is_file()
        )
        if expected != actual:
            mismatch_paths = sorted(set(expected) ^ set(actual))
        else:
            mismatch_paths = [
                relative for relative in expected
                if (expected_root / relative).read_bytes() != (output_dir / relative).read_bytes()
            ]
        artifacts_match = not mismatch_paths

    expected_status = (
        report["status"] == "INTEGRATED_CONCEPT_DOSSIER_GENERATED_REVIEW_READY"
        and report["metrics"]["request_count"] == 7
        and report["metrics"]["concept_simulation_count"] == 6
        and report["metrics"]["authoritative_request_count"] == 1
        and report["metrics"]["drawing_register_count"] == 8
        and report["metrics"]["calculation_register_count"] == 8
        and report["metrics"]["assumption_count"] == 8
        and report["metrics"]["handoff_count"] == 6
        and report["metrics"]["consistency_check_count"] == 11
        and report["metrics"]["professional_blocker_count"] == 6
        and report["metrics"]["source_file_count"] == 44
        and report["parking_basis_spaces"] == 225
        and report["req107_status"] == "CLOSED_PROJECT_LEADER_APPROVED"
        and report["gates"]["integrated_concept_dossier_generated"]
        and report["gates"]["concept_dossier_review_ready"]
        and report["gates"]["bb36_functional_validation_passed"]
        and not report["gates"]["final_permit_ready_generation_allowed"]
        and not report["gates"]["bb36_production_release_allowed"]
    )
    if artifacts_match is False:
        expected_status = False

    result = {
        "execution_status": "PASSED" if expected_status else "FAILED",
        "dossier_status": report["status"],
        "dossier_id": report["dossier_id"],
        "request_count": report["metrics"]["request_count"],
        "drawing_register_count": report["metrics"]["drawing_register_count"],
        "calculation_register_count": report["metrics"]["calculation_register_count"],
        "assumption_count": report["metrics"]["assumption_count"],
        "consistency_check_count": report["metrics"]["consistency_check_count"],
        "professional_blocker_count": report["metrics"]["professional_blocker_count"],
        "source_file_count": report["metrics"]["source_file_count"],
        "parking_basis_spaces": report["parking_basis_spaces"],
        "req107_status": report["req107_status"],
        "concept_dossier_review_ready": report["gates"]["concept_dossier_review_ready"],
        "final_permit_ready_generation_allowed": report["gates"]["final_permit_ready_generation_allowed"],
        "bb36_functional_validation_passed": report["gates"]["bb36_functional_validation_passed"],
        "bb36_production_release_allowed": report["gates"]["bb36_production_release_allowed"],
        "artifacts_match": artifacts_match,
        "artifact_mismatch_count": len(mismatch_paths),
        "artifact_mismatch_paths": mismatch_paths,
        "output_file_count": sum(1 for path in output_dir.rglob("*") if path.is_file()),
        "outputs": {key: str(value) for key, value in sorted(paths.items())},
        "next_gate": report["next_gate"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if temporary is not None:
        temporary.cleanup()

    if args.expect_dossier_ready:
        return 0 if expected_status else 1
    return 0 if expected_status else 2


if __name__ == "__main__":
    raise SystemExit(main())
