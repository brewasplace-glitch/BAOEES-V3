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
from phoenix.autonomy.project_stability_design_basis_decision_r9_5 import (
    build_project_stability_design_basis_decision,
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
        "GLOBAL_BUCKLING_FACTOR": {"lowest_positive_buckling_factor": 10.0},
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
        "qualification_register": {
            key: {"evidence": evidence[key]} for key in CHECKS
        },
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


class R95Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.policy = (
            ROOT
            / "configs"
            / "phoenix"
            / "structural"
            / "project_stability_design_basis_decision_policy_r9_5.json"
        )
        self.r94_policy = (
            ROOT
            / "configs"
            / "phoenix"
            / "structural"
            / "normative_applicability_stability_design_basis_policy_r9_4.json"
        )
        self.r94_public = (
            ROOT
            / "configs"
            / "phoenix"
            / "structural"
            / "normative_applicability_public_source_registry_r9_4.json"
        )
        self.sur_rules = (
            ROOT
            / "configs"
            / "phoenix"
            / "jurisdictions"
            / "suriname"
            / "suriname_structural_rule_registry_v1_0.json"
        )
        self.sur_sources = (
            ROOT
            / "outputs"
            / "bib"
            / "index"
            / "suriname_regulatory_source_registry_v1_0.json"
        )
        self.r93 = make_r93()
        self.r94 = build_normative_applicability_stability_design_basis(
            project_id="P",
            r93_qualification=self.r93,
            candidates=[],
            policy_path=self.r94_policy,
            source_registry_path=self.r94_public,
        )
        evidence = self.repo / "evidence" / "alternate_path_review.txt"
        evidence.parent.mkdir(parents=True)
        evidence.write_text("independent alternate-path test evidence\n", encoding="utf-8")
        self.alt_rel = evidence.relative_to(self.repo).as_posix()
        self.alt_sha = hashlib.sha256(evidence.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def run_r95(self, candidates=None):
        return build_project_stability_design_basis_decision(
            project_id="P",
            r93_qualification=self.r93,
            r94_initial=self.r94,
            candidates=candidates or [],
            policy_path=self.policy,
            suriname_rule_registry_path=self.sur_rules,
            suriname_source_registry_path=self.sur_sources,
            r94_policy_path=self.r94_policy,
            r94_public_source_registry_path=self.r94_public,
            repository_root=self.repo,
        )

    def full_input(self):
        criteria = {
            "SECOND_ORDER_AMPLIFICATION": {"max_amplification_factor": 1.1},
            "GLOBAL_BUCKLING_FACTOR": {"minimum_critical_load_factor": 2.0},
            "STOREY_STABILITY_INDEX": {"max_stability_index": 0.1},
            "TORSIONAL_DRIFT_RATIO": {"max_torsional_drift_ratio": 3.0},
            "SOFT_STOREY_STIFFNESS_RATIO": {"minimum_ratio": 0.4},
            "WEAK_STOREY_STRENGTH_RATIO": {"minimum_ratio": 0.4},
            "ALTERNATE_LOAD_PATH_EVIDENCE": {
                "minimum_residual_capacity_proxy_ratio": 0.8
            },
            "DIAPHRAGM_CONTINUITY": {},
            "LOAD_PATH_CONTINUITY": {},
        }
        rows = {}
        for check in CHECKS:
            trace = {
                key: {
                    "source_record_id": "POLICY",
                    "clause_reference": f"TEST-POLICY:{check}:{key}",
                }
                for key in criteria[check]
            }
            rows[check] = {
                "applicability": "SUPPLEMENTAL_ENGINEERING_POLICY",
                "methodology_accepted": True,
                "methodology_acceptance_reference": f"TEST-POLICY:{check}",
                "primary_source_record_id": "POLICY",
                "supporting_source_record_ids": [],
                "acceptance_criteria": criteria[check],
                "criteria_traceability": trace,
                "evidence_reference": f"R9.3:{check}",
            }
        rows["GLOBAL_BUCKLING_FACTOR"]["supporting_source_record_ids"] = ["SUR-BB1"]
        rows["WEAK_STOREY_STRENGTH_RATIO"].update(
            screening_proxy_accepted_for_candidate_gate=True,
            screening_proxy_review_reference="TEST-REVIEW-WEAK",
        )
        rows["ALTERNATE_LOAD_PATH_EVIDENCE"].update(
            alternate_path_verified=True,
            independent_engineering_evidence_reference="TEST-ALT-PATH-ANALYSIS",
            independent_engineering_evidence_file=self.alt_rel,
            independent_engineering_evidence_sha256=self.alt_sha,
            independent_review_status="REVIEWED",
            independent_review_reference="TEST-ALT-PATH-REVIEW",
        )
        return {
            "r9_5_project_stability_design_basis_decision": {
                "decision_id": "P-R9.5-TEST",
                "jurisdictional_basis": {
                    "project_jurisdiction": "Suriname / Paramaribo",
                    "engineering_design_methodology": "Eurocode 2 based",
                },
                "seismic_applicability": {
                    "status": "ENGINEERING_POLICY_APPLIED",
                    "source_record_id": "POLICY",
                    "professional_scope_reviewed": True,
                    "scope_review_reference": "TEST-SEISMIC-REVIEW",
                },
                "source_records": {
                    "POLICY": {
                        "reference_type": "PROJECT_ENGINEERING_POLICY",
                        "reference": "TEST-PROJECT-STABILITY-POLICY",
                        "project_policy_approved": True,
                        "approval_reference": "TEST-APPROVAL",
                        "scope": "R9.5 candidate stability qualification test",
                    },
                    "SUR-BB1": {
                        "reference_type": "AUTHORITY_APPROVED_PROJECT_BASIS",
                        "reference": "Suriname Bouwbesluit no. 1",
                        "bib_source_id": "SR-SUR-BB1-1956-001",
                        "source_pointer": "Article 27",
                    },
                },
                "checks": rows,
            }
        }

    def test_01_no_input_blocks_on_explicit_decision(self):
        r = self.run_r95()
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(
            r["blockers"][0]["reason"],
            "R9_5_PROJECT_STABILITY_DESIGN_BASIS_DECISION_REQUIRED",
        )

    def test_02_r93_technical_evidence_remains_nine(self):
        r = self.run_r95()
        self.assertEqual(r["summary"]["r9_3_technical_evidence_count"], 9)

    def test_03_surinaame_bib_buckling_support_available(self):
        r = self.run_r95()
        support = r["local_surinaame_primary_support"]["GLOBAL_BUCKLING_FACTOR"]
        self.assertEqual(support[0]["status"], "AVAILABLE")
        self.assertEqual(support[0]["rule_id"], "SUR-BB1-A27-BUCKLING")

    def test_04_surinaame_bib_does_not_supply_v86_buckling_limit(self):
        r = self.run_r95()
        support = r["local_surinaame_primary_support"]["GLOBAL_BUCKLING_FACTOR"]
        self.assertFalse(support[0]["exact_v8_6_acceptance_limit_available"])

    def test_05_background_ai_never_used_as_normative_input(self):
        r = self.run_r95()
        self.assertFalse(
            r["safety"]["background_ai_source_used_as_normative_input"]
        )

    def test_06_project_policy_source_qualifies_only_when_approved(self):
        data = self.full_input()
        data["r9_5_project_stability_design_basis_decision"]["source_records"][
            "POLICY"
        ]["project_policy_approved"] = False
        r = self.run_r95([("p.json", data)])
        self.assertEqual(
            r["source_qualification_register"]["POLICY"]["status"],
            "REJECTED",
        )

    def test_07_registered_surinaame_primary_source_can_qualify_as_authority_basis(self):
        data = self.full_input()
        r = self.run_r95([("p.json", data)])
        self.assertEqual(
            r["source_qualification_register"]["SUR-BB1"]["status"],
            "QUALIFIED",
        )

    def test_08_background_bib_source_cannot_qualify_as_primary_authority_basis(self):
        data = self.full_input()
        data["r9_5_project_stability_design_basis_decision"]["source_records"][
            "SUR-BB1"
        ]["bib_source_id"] = "SR-SUR-BG-2026-001"
        r = self.run_r95([("p.json", data)])
        self.assertEqual(
            r["source_qualification_register"]["SUR-BB1"]["status"],
            "REJECTED",
        )

    def test_09_valid_licensed_source_checksum_qualifies(self):
        licensed = self.repo / "licensed" / "standard_excerpt.bin"
        licensed.parent.mkdir(parents=True)
        licensed.write_bytes(b"licensed test fixture")
        sha = hashlib.sha256(licensed.read_bytes()).hexdigest()
        data = self.full_input()
        data["r9_5_project_stability_design_basis_decision"]["source_records"][
            "LIC"
        ] = {
            "reference_type": "LICENSED_STANDARD_SOURCE",
            "reference": "TEST-LICENSED-SOURCE",
            "source_file": licensed.relative_to(self.repo).as_posix(),
            "sha256": sha,
            "clause_reference": "TEST-CLAUSE",
            "licensed_use_confirmed": True,
            "extraction_reviewed": True,
        }
        r = self.run_r95([("p.json", data)])
        self.assertEqual(
            r["source_qualification_register"]["LIC"]["status"],
            "QUALIFIED",
        )

    def test_10_licensed_source_hash_mismatch_rejected(self):
        licensed = self.repo / "licensed.bin"
        licensed.write_bytes(b"x")
        data = self.full_input()
        data["r9_5_project_stability_design_basis_decision"]["source_records"][
            "LIC"
        ] = {
            "reference_type": "LICENSED_STANDARD_SOURCE",
            "reference": "TEST-LICENSED-SOURCE",
            "source_file": "licensed.bin",
            "sha256": "0" * 64,
            "clause_reference": "TEST-CLAUSE",
            "licensed_use_confirmed": True,
            "extraction_reviewed": True,
        }
        r = self.run_r95([("p.json", data)])
        self.assertIn(
            "source_sha256_mismatch",
            r["source_qualification_register"]["LIC"]["errors"],
        )

    def test_11_complete_explicit_decision_requalifies_r94_nine_of_nine(self):
        r = self.run_r95([("project.json", self.full_input())])
        self.assertEqual(r["status"], "PASSED")
        self.assertEqual(r["summary"]["r9_4_requalified_check_count"], 9)
        self.assertEqual(len(r["qualified_check_types"]), 9)

    def test_12_complete_decision_builds_global_stability_input(self):
        r = self.run_r95([("project.json", self.full_input())])
        self.assertIsInstance(r["global_stability_input"], dict)

    def test_13_alternate_path_requires_real_evidence_file(self):
        data = self.full_input()
        row = data["r9_5_project_stability_design_basis_decision"]["checks"][
            "ALTERNATE_LOAD_PATH_EVIDENCE"
        ]
        row["independent_engineering_evidence_file"] = "missing.dat"
        r = self.run_r95([("project.json", data)])
        self.assertIn(
            "ALTERNATE_LOAD_PATH_EVIDENCE",
            r["unresolved_check_types"],
        )

    def test_14_alternate_path_hash_mismatch_blocks(self):
        data = self.full_input()
        row = data["r9_5_project_stability_design_basis_decision"]["checks"][
            "ALTERNATE_LOAD_PATH_EVIDENCE"
        ]
        row["independent_engineering_evidence_sha256"] = "0" * 64
        r = self.run_r95([("project.json", data)])
        self.assertIn(
            "ALTERNATE_LOAD_PATH_EVIDENCE",
            r["unresolved_check_types"],
        )

    def test_15_weak_storey_proxy_requires_explicit_candidate_acceptance(self):
        data = self.full_input()
        row = data["r9_5_project_stability_design_basis_decision"]["checks"][
            "WEAK_STOREY_STRENGTH_RATIO"
        ]
        row["screening_proxy_accepted_for_candidate_gate"] = False
        r = self.run_r95([("project.json", data)])
        self.assertIn(
            "WEAK_STOREY_STRENGTH_RATIO",
            r["unresolved_check_types"],
        )

    def test_16_seismic_not_applicable_does_not_auto_waive_v86(self):
        data = self.full_input()
        seismic = data["r9_5_project_stability_design_basis_decision"][
            "seismic_applicability"
        ]
        seismic["status"] = "NOT_APPLICABLE"
        r = self.run_r95([("project.json", data)])
        self.assertEqual(r["status"], "BLOCKED")
        self.assertIn(
            "mandatory_v8_6_scope_waiver_or_policy_revision",
            r["seismic_scope_decision"]["missing_requirements"],
        )

    def test_17_template_contains_no_default_numerical_limits(self):
        r = self.run_r95()
        checks = r["required_input_template"][
            "r9_5_project_stability_design_basis_decision"
        ]["checks"]
        for check in checks.values():
            for value in check["acceptance_criteria"].values():
                self.assertIsNone(value)

    def test_18_current_2026_legal_status_not_invented(self):
        r = self.run_r95()
        basis = r["required_input_template"][
            "r9_5_project_stability_design_basis_decision"
        ]["jurisdictional_basis"]
        self.assertEqual(
            basis["current_2026_surinaame_legal_status"],
            "NOT_EXTERNALLY_VERIFIED",
        )

    def test_19_production_release_locked(self):
        self.assertEqual(
            self.run_r95()["safety"]["production_release"],
            "LOCKED",
        )

    def test_20_deterministic_no_input_register(self):
        self.assertEqual(
            self.run_r95()["decision_register"],
            self.run_r95()["decision_register"],
        )


if __name__ == "__main__":
    unittest.main()
