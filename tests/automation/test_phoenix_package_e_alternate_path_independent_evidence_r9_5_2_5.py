from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.autonomy.normative_applicability_stability_design_basis_r9_4 import (
    build_normative_applicability_stability_design_basis,
)
from phoenix.autonomy.package_b_licensed_source_traceability_r9_5_2_3 import (
    apply_package_b_traceability_to_r9_5_required_input_document,
)
from phoenix.autonomy.package_e_alternate_path_independent_evidence_r9_5_2_5 import (
    CHECK_TYPE,
    PACKAGE_ID,
    _merge_into_r9_5_input,
    _update_r9_5_2_package_e,
    _validate_independent_evidence,
    build_required_input_template,
)
from phoenix.autonomy.project_stability_design_basis_decision_r9_5 import (
    build_project_stability_design_basis_decision,
)
from phoenix.autonomy.stability_ab_project_policy_integration_r9_5_2_2 import (
    apply_ab_policy_to_r9_5_required_input_document,
)

CHECKS = [
    "ALTERNATE_LOAD_PATH_EVIDENCE",
    "DIAPHRAGM_CONTINUITY",
    "GLOBAL_BUCKLING_FACTOR",
    "LOAD_PATH_CONTINUITY",
    "SECOND_ORDER_AMPLIFICATION",
    "SOFT_STOREY_STIFFNESS_RATIO",
    "STOREY_STABILITY_INDEX",
    "TORSIONAL_DRIFT_RATIO",
    "WEAK_STOREY_STRENGTH_RATIO",
]


def make_r93():
    evidence = {
        "SECOND_ORDER_AMPLIFICATION": {
            "first_order_max_horizontal_displacement_m": 1.0,
            "second_order_max_horizontal_displacement_m": 1.01,
        },
        "GLOBAL_BUCKLING_FACTOR": {"lowest_positive_buckling_factor": 20.0},
        "STOREY_STABILITY_INDEX": {
            "storey_id": "S1",
            "gravity_load_above_storey_kN": 100.0,
            "mean_interstorey_drift_m": 0.01,
            "storey_shear_kN": 20.0,
            "storey_height_m": 3.0,
        },
        "TORSIONAL_DRIFT_RATIO": {
            "storey_id": "S2",
            "max_nodal_interstorey_drift_m": 0.002,
            "average_nodal_interstorey_drift_m": 0.001,
        },
        "SOFT_STOREY_STIFFNESS_RATIO": {
            "storey_id": "S2",
            "storey_stiffness_kN_per_m": 100.0,
            "reference_stiffness_kN_per_m": 200.0,
        },
        "DIAPHRAGM_CONTINUITY": {"continuity_verified": True},
        "LOAD_PATH_CONTINUITY": {
            "all_loaded_nodes_reach_support": True,
            "loaded_nodes": ["N1"],
            "load_path_edges": [{"from": "N1", "to": "SUP1"}],
        },
        "WEAK_STOREY_STRENGTH_RATIO": {
            "governing_candidate": {
                "storey_id": "S2",
                "storey_strength_proxy_kN": 50.0,
                "reference_strength_proxy_kN": 100.0,
            }
        },
        "ALTERNATE_LOAD_PATH_EVIDENCE": {
            "status": "AVAILABLE",
            "minimum_residual_capacity_proxy_ratio": 0.9,
            "alternate_path_verified": False,
        },
    }
    return {
        "status": "BLOCKED",
        "technical_evidence_available_for": list(CHECKS),
        "analysis_required_for": [],
        "qualification_register": {key: {"evidence": evidence[key]} for key in CHECKS},
        "required_input_template": {
            "r9_3_stability_design_basis_input": {
                "stability_basis": {
                    "project_jurisdiction": "Suriname / Paramaribo",
                    "engineering_design_methodology": "Eurocode 2 based",
                    "legal_applicability_in_suriname": "NOT_VERIFIED",
                }
            }
        },
    }


class Tests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (
                ROOT
                / "configs/phoenix/structural/package_e_alternate_path_independent_evidence_policy_r9_5_2_5.json"
            ).read_text(encoding="utf-8")
        )
        self.r95_policy = ROOT / "configs/phoenix/structural/project_stability_design_basis_decision_policy_r9_5.json"
        self.r94_policy = ROOT / "configs/phoenix/structural/normative_applicability_stability_design_basis_policy_r9_4.json"
        self.r94_public = ROOT / "configs/phoenix/structural/normative_applicability_public_source_registry_r9_4.json"
        self.sur_rules = ROOT / "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json"
        self.sur_sources = ROOT / "outputs/bib/index/suriname_regulatory_source_registry_v1_0.json"
        self.ab_policy_path = ROOT / "configs/phoenix/structural/stability_ab_project_policy_r9_5_2_2.json"
        self.b_registry = ROOT / "configs/phoenix/structural/package_b_licensed_source_traceability_r9_5_2_3.json"

    def valid_doc(self, evidence_rel, evidence_sha):
        return {
            "project_id": "PHOENIX-PAT-001",
            "package_id": PACKAGE_ID,
            "check_type": CHECK_TYPE,
            "decision": {
                "applicability": "APPLICABLE",
                "methodology_accepted": True,
                "methodology_acceptance_reference": "INDEPENDENT-ROBUSTNESS-REVIEW-TEST",
                "primary_source_record_id": "PACKAGE_E_PROJECT_POLICY",
                "supporting_source_record_ids": [],
                "acceptance_criteria": {
                    "minimum_residual_capacity_proxy_ratio": 0.8
                },
                "criteria_traceability": {
                    "minimum_residual_capacity_proxy_ratio": {
                        "source_record_id": "PACKAGE_E_PROJECT_POLICY",
                        "clause_reference": "UNIT-TEST INDEPENDENT REVIEW ACCEPTANCE BASIS",
                    }
                },
                "evidence_reference": "INDEPENDENT-ALT-PATH-TEST",
                "alternate_path_verified": True,
                "independent_engineering_evidence_reference": "INDEPENDENT-ALT-PATH-TEST",
                "independent_engineering_evidence_file": evidence_rel,
                "independent_engineering_evidence_sha256": evidence_sha,
                "independent_review_status": "REVIEWED",
                "independent_review_reference": "INDEPENDENT-REVIEW-TEST",
            },
            "source_records": {
                "PACKAGE_E_PROJECT_POLICY": {
                    "reference_type": "PROJECT_ENGINEERING_POLICY",
                    "reference": "Package E unit-test project policy",
                    "project_policy_approved": True,
                    "approval_reference": "UNIT_TEST_ONLY",
                    "scope": "ALTERNATE_LOAD_PATH_EVIDENCE",
                }
            },
            "independence_attestation": {
                "evidence_origin": "EXTERNAL_INDEPENDENT_ENGINEERING",
                "phoenix_generated": False,
                "independent_from_phoenix_analysis": True,
                "reviewer_or_organization": "UNIT TEST REVIEWER",
                "attestation_reference": "UNIT-TEST-ATTESTATION",
            },
        }

    def test_01_template_has_safe_unset_decisions(self):
        d = build_required_input_template(
            project_id="PHOENIX-PAT-001",
            repository_root=ROOT,
        )
        self.assertIsNone(d["decision"]["applicability"])
        self.assertFalse(d["decision"]["methodology_accepted"])
        self.assertIsNone(
            d["decision"]["acceptance_criteria"]["minimum_residual_capacity_proxy_ratio"]
        )
        self.assertFalse(d["decision"]["alternate_path_verified"])
        self.assertIsNone(d["decision"]["independent_review_status"])

    def test_02_not_applicable_does_not_auto_waive_v86(self):
        d = build_required_input_template(
            project_id="PHOENIX-PAT-001",
            repository_root=ROOT,
        )
        d["decision"]["applicability"] = "NOT_APPLICABLE"
        v = _validate_independent_evidence(
            document=d,
            project_id="PHOENIX-PAT-001",
            repository_root=ROOT,
            policy=self.policy,
        )
        self.assertIn(
            "professional_v8_6_scope_waiver_or_policy_revision",
            v["missing_requirements"],
        )

    def test_03_project_mismatch_rejected(self):
        d = build_required_input_template(
            project_id="OTHER",
            repository_root=ROOT,
        )
        v = _validate_independent_evidence(
            document=d,
            project_id="PHOENIX-PAT-001",
            repository_root=ROOT,
            policy=self.policy,
        )
        self.assertIn("project_id_mismatch", v["errors"])

    def test_04_phoenix_generated_evidence_rejected(self):
        d = build_required_input_template(
            project_id="PHOENIX-PAT-001",
            repository_root=ROOT,
        )
        d["decision"]["applicability"] = "APPLICABLE"
        d["independence_attestation"]["phoenix_generated"] = True
        v = _validate_independent_evidence(
            document=d,
            project_id="PHOENIX-PAT-001",
            repository_root=ROOT,
            policy=self.policy,
        )
        self.assertIn("phoenix_generated_must_be_false", v["missing_requirements"])

    def test_05_r93_screening_stays_screening_only(self):
        self.assertFalse(
            self.policy["r9_3_screening"]["sufficient_as_independent_evidence"]
        )
        self.assertFalse(
            self.policy["r9_3_screening"][
                "may_be_promoted_to_redistributed_member_removal_analysis"
            ]
        )

    def test_06_valid_external_evidence_hash_and_review_validate(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            evidence = Path(td) / "independent_evidence.txt"
            evidence.write_text("independent evidence test fixture", encoding="utf-8")
            rel = evidence.relative_to(ROOT).as_posix()
            sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
            v = _validate_independent_evidence(
                document=self.valid_doc(rel, sha),
                project_id="PHOENIX-PAT-001",
                repository_root=ROOT,
                policy=self.policy,
            )
            self.assertEqual("VALIDATED", v["status"])
            self.assertTrue(v["evidence_trace"]["sha256_validated"])

    def test_07_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            evidence = Path(td) / "independent_evidence.txt"
            evidence.write_text("test", encoding="utf-8")
            rel = evidence.relative_to(ROOT).as_posix()
            v = _validate_independent_evidence(
                document=self.valid_doc(rel, "0" * 64),
                project_id="PHOENIX-PAT-001",
                repository_root=ROOT,
                policy=self.policy,
            )
            self.assertIn("alternate_path_source_sha256_mismatch", v["errors"])

    def test_08_merge_preserves_existing_package_b_values(self):
        global_input = {
            "r9_5_project_stability_design_basis_decision": {
                "source_records": {},
                "checks": {
                    CHECK_TYPE: {
                        "applicability": None,
                        "acceptance_criteria": {
                            "minimum_residual_capacity_proxy_ratio": None
                        },
                    },
                    "GLOBAL_BUCKLING_FACTOR": {
                        "acceptance_criteria": {
                            "minimum_critical_load_factor": 11.0
                        }
                    },
                },
            }
        }
        d = self.valid_doc("x.pdf", "1" * 64)
        out = _merge_into_r9_5_input(
            global_input=global_input,
            package_e_input=d,
            validation={"status": "VALIDATED"},
        )
        root = out["r9_5_project_stability_design_basis_decision"]
        self.assertEqual(
            11.0,
            root["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"][
                "minimum_critical_load_factor"
            ],
        )
        self.assertEqual(
            0.8,
            root["checks"][CHECK_TYPE]["acceptance_criteria"][
                "minimum_residual_capacity_proxy_ratio"
            ],
        )

    def test_09_package_e_resolution_does_not_modify_package_c(self):
        r952 = {
            "evidence_intake": {
                "package_inputs": {
                    PACKAGE_ID: {
                        "status": "REQUIRED",
                        "checks": [CHECK_TYPE],
                        "validation": {"qualified": False},
                    },
                    "PKG-C-SEISMIC-SCOPE-AND-CRITERIA": {
                        "status": "REQUIRED",
                        "checks": ["TORSIONAL_DRIFT_RATIO"],
                    },
                }
            }
        }
        out = _update_r9_5_2_package_e(
            r952=r952,
            package_e_input=self.valid_doc("x.pdf", "1" * 64),
            qualified=True,
            validation={"evidence_trace": {"sha256_validated": True}},
        )
        self.assertTrue(
            out["evidence_intake"]["package_inputs"][PACKAGE_ID]["validation"]["qualified"]
        )
        self.assertEqual(
            "REQUIRED",
            out["evidence_intake"]["package_inputs"][
                "PKG-C-SEISMIC-SCOPE-AND-CRITERIA"
            ]["status"],
        )

    def test_10_cross_gate_e_can_raise_qualified_count_from_five_to_six(self):
        r93 = make_r93()
        r94 = build_normative_applicability_stability_design_basis(
            project_id="PHOENIX-PAT-001",
            r93_qualification=r93,
            candidates=[],
            policy_path=self.r94_policy,
            source_registry_path=self.r94_public,
        )
        initial = build_project_stability_design_basis_decision(
            project_id="PHOENIX-PAT-001",
            r93_qualification=r93,
            r94_initial=r94,
            candidates=[],
            policy_path=self.r95_policy,
            suriname_rule_registry_path=self.sur_rules,
            suriname_source_registry_path=self.sur_sources,
            r94_policy_path=self.r94_policy,
            r94_public_source_registry_path=self.r94_public,
            repository_root=ROOT,
        )
        doc = initial["required_input_template"]
        ab_policy = json.loads(self.ab_policy_path.read_text(encoding="utf-8"))
        doc = apply_ab_policy_to_r9_5_required_input_document(doc, ab_policy)
        root = doc["r9_5_project_stability_design_basis_decision"]
        for row in root["checks"].values():
            if row.get("applicability") is True:
                row["applicability"] = "APPLICABLE"
        doc = apply_package_b_traceability_to_r9_5_required_input_document(
            doc,
            repo_root=ROOT,
            registry_path=self.b_registry,
        )

        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            evidence = Path(td) / "independent_evidence.txt"
            evidence.write_text("independent evidence test fixture", encoding="utf-8")
            rel = evidence.relative_to(ROOT).as_posix()
            sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
            e = self.valid_doc(rel, sha)
            v = _validate_independent_evidence(
                document=e,
                project_id="PHOENIX-PAT-001",
                repository_root=ROOT,
                policy=self.policy,
            )
            self.assertEqual("VALIDATED", v["status"])
            doc = _merge_into_r9_5_input(
                global_input=doc,
                package_e_input=e,
                validation=v,
            )

            r95 = build_project_stability_design_basis_decision(
                project_id="PHOENIX-PAT-001",
                r93_qualification=r93,
                r94_initial=r94,
                candidates=[(
                    "inputs/structural/global_stability_engineering_input_REQUIRED.json",
                    doc,
                )],
                policy_path=self.r95_policy,
                suriname_rule_registry_path=self.sur_rules,
                suriname_source_registry_path=self.sur_sources,
                r94_policy_path=self.r94_policy,
                r94_public_source_registry_path=self.r94_public,
                repository_root=ROOT,
            )
            self.assertEqual(
                "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK",
                r95["decision_register"][CHECK_TYPE]["state"],
            )
            self.assertEqual(6, r95["summary"]["decision_qualified_check_count"])
            self.assertEqual(3, r95["summary"]["unresolved_decision_check_count"])

    def test_11_no_auto_review_compliance_or_approval(self):
        safety = self.policy["safety"]
        self.assertFalse(safety["automatic_independent_review_claim"])
        self.assertFalse(safety["automatic_professional_review_claim"])
        self.assertFalse(safety["automatic_code_compliance_claim"])
        self.assertFalse(safety["automatic_structural_approval"])
        self.assertTrue(safety["professional_structural_review_required"])

    def test_12_production_locked_and_seismic_auto_decision_disabled(self):
        safety = self.policy["safety"]
        self.assertEqual("LOCKED", safety["production_release"])
        self.assertFalse(safety["automatic_seismic_scope_decision"])


if __name__ == "__main__":
    unittest.main()
