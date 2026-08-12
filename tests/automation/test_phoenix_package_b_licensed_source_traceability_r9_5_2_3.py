from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy.package_b_licensed_source_traceability_r9_5_2_3 import (
    apply_package_b_traceability_to_r9_5_2_result,
    apply_package_b_traceability_to_r9_5_required_input_document,
    validate_traceability_registry,
)

REGISTRY_PATH = ROOT / "configs/phoenix/structural/package_b_licensed_source_traceability_r9_5_2_3.json"
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def global_input_fixture():
    checks = {}
    for check_id in (
        "DIAPHRAGM_CONTINUITY",
        "GLOBAL_BUCKLING_FACTOR",
        "LOAD_PATH_CONTINUITY",
        "SECOND_ORDER_AMPLIFICATION",
        "STOREY_STABILITY_INDEX",
    ):
        checks[check_id] = {
            "acceptance_criteria": {},
            "criteria_traceability": {},
        }
    checks["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"] = {"minimum_critical_load_factor": None}
    checks["SECOND_ORDER_AMPLIFICATION"]["acceptance_criteria"] = {"max_amplification_factor": None}
    checks["STOREY_STABILITY_INDEX"]["acceptance_criteria"] = {"max_stability_index": None}
    return {
        "project_id": "PHOENIX-PAT-001",
        "r9_5_project_stability_design_basis_decision": {
            "source_records": {},
            "checks": checks,
        },
    }


def r952_fixture():
    return {
        "project_id": "PHOENIX-PAT-001",
        "evidence_intake": {
            "source_records": {},
            "package_inputs": {
                "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA": {
                    "status": "PROJECT_POLICY_CRITERIA_APPROVED_LICENSED_SOURCE_TRACEABILITY_REQUIRED",
                    "inputs": {
                        "source_record_id": None,
                        "source_file": None,
                        "sha256": None,
                        "clause_reference": None,
                        "licensed_use_confirmed": False,
                        "extraction_reviewed": False,
                        "criteria": {
                            "GLOBAL_BUCKLING_FACTOR": {"minimum_critical_load_factor": 11.0},
                            "SECOND_ORDER_AMPLIFICATION": {"max_amplification_factor": 1.10},
                            "STOREY_STABILITY_INDEX": {"max_stability_index": 0.10},
                        },
                    },
                }
            },
            "intake_metadata": {},
        },
        "blockers": [{"reason": "R9_5_2_STABILITY_DESIGN_BASIS_EVIDENCE_INTAKE_REQUIRED"}],
    }


class Tests(unittest.TestCase):
    def test_01_registry_validates(self):
        state = validate_traceability_registry(repo_root=ROOT, registry_path=REGISTRY_PATH)
        self.assertEqual("VALIDATED", state["status"])

    def test_02_licensed_use_confirmed(self):
        self.assertTrue(REGISTRY["licensed_use"]["confirmed"])

    def test_03_extraction_reviewed(self):
        self.assertTrue(REGISTRY["extraction_review"]["reviewed"])

    def test_04_not_professional_review(self):
        self.assertFalse(REGISTRY["extraction_review"]["professional_structural_review"])

    def test_05_bundle_sha_present(self):
        self.assertEqual(64, len(REGISTRY["bundle_source"]["sha256"]))

    def test_06_raw_evidence_count(self):
        self.assertEqual(4, len(REGISTRY["bundle_source"]["raw_evidence_files"]))

    def test_07_second_order_promoted(self):
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            global_input_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        value = out["r9_5_project_stability_design_basis_decision"]["checks"]["SECOND_ORDER_AMPLIFICATION"]["acceptance_criteria"]["max_amplification_factor"]
        self.assertEqual(1.10, value)

    def test_08_buckling_promoted(self):
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            global_input_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        value = out["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"]
        self.assertEqual(11.0, value)

    def test_09_storey_index_promoted(self):
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            global_input_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        value = out["r9_5_project_stability_design_basis_decision"]["checks"]["STOREY_STABILITY_INDEX"]["acceptance_criteria"]["max_stability_index"]
        self.assertEqual(0.10, value)

    def test_10_traceability_source_record_added(self):
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            global_input_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        records = out["r9_5_project_stability_design_basis_decision"]["source_records"]
        self.assertIn("NEN_EC2_STABILITY_PACKAGE_B_LICENSED_EXTRACT", records)

    def test_11_literal_limit_claim_false(self):
        for row in REGISTRY["criteria_traceability"].values():
            self.assertFalse(row["literal_standard_limit_claim"])

    def test_12_existing_equal_value_preserved(self):
        doc = global_input_fixture()
        doc["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"] = 11.0
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            doc, repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        self.assertEqual(
            11.0,
            out["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"],
        )

    def test_13_conflicting_existing_value_fails_closed(self):
        doc = global_input_fixture()
        doc["r9_5_project_stability_design_basis_decision"]["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"] = 7.0
        with self.assertRaises(ValueError):
            apply_package_b_traceability_to_r9_5_required_input_document(
                doc, repo_root=ROOT, registry_path=REGISTRY_PATH
            )

    def test_14_r952_package_b_traceability_complete(self):
        out = apply_package_b_traceability_to_r9_5_2_result(
            r952_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        row = out["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]
        self.assertTrue(row["validation"]["licensed_source_traceability_complete"])

    def test_15_r952_licensed_use_true(self):
        out = apply_package_b_traceability_to_r9_5_2_result(
            r952_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        self.assertTrue(out["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]["inputs"]["licensed_use_confirmed"])

    def test_16_r952_extraction_reviewed_true(self):
        out = apply_package_b_traceability_to_r9_5_2_result(
            r952_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        self.assertTrue(out["evidence_intake"]["package_inputs"]["PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA"]["inputs"]["extraction_reviewed"])

    def test_17_r952_still_not_professionally_approved(self):
        out = apply_package_b_traceability_to_r9_5_2_result(
            r952_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        self.assertFalse(out["r9_5_2_3"]["professional_structural_review"])

    def test_18_production_locked(self):
        self.assertEqual("LOCKED", REGISTRY["safety"]["production_release"])

    def test_19_tampered_bundle_fails(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            shutil.copytree(ROOT / "outputs/bib/sources/standards/licensed/nen_en_1992_1_1_package_b", temp / "bundle")
            reg = json.loads(json.dumps(REGISTRY))
            reg["bundle_source"]["source_file"] = "bundle/PHOENIX_PACKAGE_B_NEN_LICENSED_SOURCE_EVIDENCE_v1_0.pdf"
            reg["bundle_source"]["local_file"] = reg["bundle_source"]["source_file"]
            reg["bundle_source"]["file_path"] = reg["bundle_source"]["source_file"]
            reg["bundle_source"]["repo_relative_path"] = reg["bundle_source"]["source_file"]
            raw = []
            for row in reg["bundle_source"]["raw_evidence_files"]:
                raw.append({"file": "bundle/raw/" + Path(row["file"]).name, "sha256": row["sha256"]})
            reg["bundle_source"]["raw_evidence_files"] = raw
            reg_path = temp / "registry.json"
            reg_path.write_text(json.dumps(reg), encoding="utf-8")
            (temp / reg["bundle_source"]["source_file"]).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                validate_traceability_registry(repo_root=temp, registry_path=reg_path)

    def test_20_no_code_compliance_claim(self):
        self.assertFalse(REGISTRY["safety"]["automatic_code_compliance_claim"])

    def test_21_no_suriname_legal_adoption_claim(self):
        self.assertFalse(REGISTRY["safety"]["legal_adoption_in_suriname_claim"])

    def test_22_bundle_clauses_include_5_8_2_6(self):
        self.assertIn("5.8.2(6)", REGISTRY["bundle_source"]["clause_reference"])

    def test_23_bundle_clauses_include_5_8_7_3(self):
        self.assertIn("5.8.7.3", REGISTRY["bundle_source"]["clause_reference"])

    def test_24_r952_status_complete(self):
        out = apply_package_b_traceability_to_r9_5_2_result(
            r952_fixture(), repo_root=ROOT, registry_path=REGISTRY_PATH
        )
        self.assertEqual("PACKAGE_B_LICENSED_SOURCE_TRACEABILITY_COMPLETE", out["r9_5_2_3"]["status"])


if __name__ == "__main__":
    unittest.main()
