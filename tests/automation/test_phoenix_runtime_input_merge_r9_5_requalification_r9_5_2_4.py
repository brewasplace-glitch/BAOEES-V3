from __future__ import annotations

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
from phoenix.autonomy.project_stability_design_basis_decision_r9_5 import (
    build_project_stability_design_basis_decision,
)
from phoenix.autonomy.runtime_input_merge_r9_5_requalification_r9_5_2_4 import (
    _atomic_write_json,
    _package_resolution,
    normalize_r9_5_contract,
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
        self.r95_policy = ROOT / "configs/phoenix/structural/project_stability_design_basis_decision_policy_r9_5.json"
        self.r94_policy = ROOT / "configs/phoenix/structural/normative_applicability_stability_design_basis_policy_r9_4.json"
        self.r94_public = ROOT / "configs/phoenix/structural/normative_applicability_public_source_registry_r9_4.json"
        self.sur_rules = ROOT / "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json"
        self.sur_sources = ROOT / "outputs/bib/index/suriname_regulatory_source_registry_v1_0.json"
        self.ab_policy_path = ROOT / "configs/phoenix/structural/stability_ab_project_policy_r9_5_2_2.json"
        self.b_registry = ROOT / "configs/phoenix/structural/package_b_licensed_source_traceability_r9_5_2_3.json"

    def test_01_true_applicability_normalizes_to_explicit_state(self):
        d = {
            "r9_5_project_stability_design_basis_decision": {
                "checks": {"X": {"applicability": True}}
            }
        }
        out = normalize_r9_5_contract(d)
        self.assertEqual(
            "APPLICABLE",
            out["r9_5_project_stability_design_basis_decision"]["checks"]["X"]["applicability"],
        )

    def test_02_false_applicability_does_not_invent_not_applicable(self):
        d = {
            "r9_5_project_stability_design_basis_decision": {
                "checks": {"X": {"applicability": False}}
            }
        }
        out = normalize_r9_5_contract(d)
        self.assertIsNone(
            out["r9_5_project_stability_design_basis_decision"]["checks"]["X"]["applicability"]
        )

    def test_03_package_b_source_type_normalizes_to_r95_contract(self):
        d = {
            "r9_5_project_stability_design_basis_decision": {
                "checks": {},
                "source_records": {
                    "NEN_EC2_STABILITY_PACKAGE_B_LICENSED_EXTRACT": {
                        "reference_type": "LICENSED_STANDARD_EXTRACT"
                    }
                },
            }
        }
        out = normalize_r9_5_contract(d)
        self.assertEqual(
            "LICENSED_STANDARD_SOURCE",
            out["r9_5_project_stability_design_basis_decision"]["source_records"][
                "NEN_EC2_STABILITY_PACKAGE_B_LICENSED_EXTRACT"
            ]["reference_type"],
        )

    def test_04_atomic_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json"
            value = {"a": 1, "b": {"c": True}}
            readback, sha = _atomic_write_json(path, value)
            self.assertEqual(value, readback)
            self.assertEqual(64, len(sha))
            self.assertFalse(path.with_name(path.name + ".r9_5_2_4.tmp").exists())

    def test_05_package_resolution_resolves_a_b_only_for_five_checks(self):
        r952 = {
            "evidence_intake": {
                "package_inputs": {
                    "PKG-A-STABILITY-METHODOLOGY-DECISION": {
                        "checks": [
                            "DIAPHRAGM_CONTINUITY",
                            "GLOBAL_BUCKLING_FACTOR",
                            "LOAD_PATH_CONTINUITY",
                            "SECOND_ORDER_AMPLIFICATION",
                            "STOREY_STABILITY_INDEX",
                        ],
                        "validation": {},
                    },
                    "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA": {
                        "checks": [
                            "GLOBAL_BUCKLING_FACTOR",
                            "SECOND_ORDER_AMPLIFICATION",
                            "STOREY_STABILITY_INDEX",
                        ],
                        "validation": {
                            "licensed_source_traceability_complete": True,
                            "licensed_use_confirmed": True,
                            "extraction_reviewed": True,
                        },
                    },
                    "PKG-C-SEISMIC-SCOPE-AND-CRITERIA": {
                        "checks": [
                            "SOFT_STOREY_STIFFNESS_RATIO",
                            "TORSIONAL_DRIFT_RATIO",
                            "WEAK_STOREY_STRENGTH_RATIO",
                        ],
                        "validation": {},
                    },
                    "PKG-D-WEAK-STOREY-SCREENING-REVIEW": {
                        "checks": ["WEAK_STOREY_STRENGTH_RATIO"],
                        "validation": {},
                    },
                    "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE": {
                        "checks": ["ALTERNATE_LOAD_PATH_EVIDENCE"],
                        "validation": {},
                    },
                }
            }
        }
        qualified = [
            "DIAPHRAGM_CONTINUITY",
            "GLOBAL_BUCKLING_FACTOR",
            "LOAD_PATH_CONTINUITY",
            "SECOND_ORDER_AMPLIFICATION",
            "STOREY_STABILITY_INDEX",
        ]
        resolved, unresolved = _package_resolution(r952, qualified_checks=qualified)
        self.assertEqual(
            [
                "PKG-A-STABILITY-METHODOLOGY-DECISION",
                "PKG-B-NUMERICAL-ACCEPTANCE-CRITERIA",
            ],
            resolved,
        )
        self.assertEqual(
            [
                "PKG-C-SEISMIC-SCOPE-AND-CRITERIA",
                "PKG-D-WEAK-STOREY-SCREENING-REVIEW",
                "PKG-E-ALTERNATE-PATH-INDEPENDENT-EVIDENCE",
            ],
            unresolved,
        )

    def test_06_cross_gate_ab_package_b_yields_five_r95_qualified_checks(self):
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
        doc = normalize_r9_5_contract(doc)
        doc = apply_package_b_traceability_to_r9_5_required_input_document(
            doc,
            repo_root=ROOT,
            registry_path=self.b_registry,
        )
        doc = normalize_r9_5_contract(doc)

        r95 = build_project_stability_design_basis_decision(
            project_id="PHOENIX-PAT-001",
            r93_qualification=r93,
            r94_initial=r94,
            candidates=[("inputs/structural/global_stability_engineering_input_REQUIRED.json", doc)],
            policy_path=self.r95_policy,
            suriname_rule_registry_path=self.sur_rules,
            suriname_source_registry_path=self.sur_sources,
            r94_policy_path=self.r94_policy,
            r94_public_source_registry_path=self.r94_public,
            repository_root=ROOT,
        )
        self.assertEqual(5, r95["summary"]["decision_qualified_check_count"])
        self.assertEqual(4, r95["summary"]["unresolved_decision_check_count"])
        self.assertEqual(
            {
                "DIAPHRAGM_CONTINUITY",
                "GLOBAL_BUCKLING_FACTOR",
                "LOAD_PATH_CONTINUITY",
                "SECOND_ORDER_AMPLIFICATION",
                "STOREY_STABILITY_INDEX",
            },
            {
                key
                for key, row in r95["decision_register"].items()
                if row["state"] == "DECISION_AND_SOURCE_QUALIFIED_FOR_R9_4_RECHECK"
            },
        )

    def test_07_no_automatic_seismic_decision(self):
        from phoenix.autonomy.runtime_input_merge_r9_5_requalification_r9_5_2_4 import ENGINE_ID
        self.assertIn("R9.5.2.4", ENGINE_ID)

    def test_08_package_b_engine_uses_r95_licensed_reference_type(self):
        text = (
            ROOT
            / "phoenix/autonomy/package_b_licensed_source_traceability_r9_5_2_3.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"reference_type": "LICENSED_STANDARD_SOURCE"', text)
        self.assertNotIn('"reference_type": "LICENSED_STANDARD_EXTRACT"', text)

    def test_09_ab_engine_uses_explicit_applicability_string(self):
        text = (
            ROOT
            / "phoenix/autonomy/stability_ab_project_policy_integration_r9_5_2_2.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(2, text.count('row["applicability"] = "APPLICABLE"'))
        self.assertNotIn('row["applicability"] = True', text)


    def test_10_package_b_promotes_without_top_level_project_id(self):
        d = {
            "r9_5_project_stability_design_basis_decision": {
                "source_records": {},
                "checks": {
                    "GLOBAL_BUCKLING_FACTOR": {
                        "applicability": "APPLICABLE",
                        "methodology_accepted": True,
                        "acceptance_criteria": {"minimum_critical_load_factor": None},
                        "criteria_traceability": {"minimum_critical_load_factor": {"source_record_id": None, "clause_reference": None}},
                    },
                    "SECOND_ORDER_AMPLIFICATION": {
                        "applicability": "APPLICABLE",
                        "methodology_accepted": True,
                        "acceptance_criteria": {"max_amplification_factor": None},
                        "criteria_traceability": {"max_amplification_factor": {"source_record_id": None, "clause_reference": None}},
                    },
                    "STOREY_STABILITY_INDEX": {
                        "applicability": "APPLICABLE",
                        "methodology_accepted": True,
                        "acceptance_criteria": {"max_stability_index": None},
                        "criteria_traceability": {"max_stability_index": {"source_record_id": None, "clause_reference": None}},
                    },
                },
            }
        }
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            d,
            repo_root=ROOT,
            registry_path=self.b_registry,
        )
        root = out["r9_5_project_stability_design_basis_decision"]
        self.assertIn("NEN_EC2_STABILITY_PACKAGE_B_LICENSED_EXTRACT", root["source_records"])
        self.assertEqual(
            11.0,
            root["checks"]["GLOBAL_BUCKLING_FACTOR"]["acceptance_criteria"]["minimum_critical_load_factor"],
        )
        self.assertEqual(
            1.10,
            root["checks"]["SECOND_ORDER_AMPLIFICATION"]["acceptance_criteria"]["max_amplification_factor"],
        )
        self.assertEqual(
            0.10,
            root["checks"]["STOREY_STABILITY_INDEX"]["acceptance_criteria"]["max_stability_index"],
        )

    def test_11_package_b_still_rejects_explicit_project_mismatch(self):
        d = {
            "project_id": "OTHER-PROJECT",
            "r9_5_project_stability_design_basis_decision": {
                "source_records": {},
                "checks": {},
            },
        }
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            d,
            repo_root=ROOT,
            registry_path=self.b_registry,
        )
        self.assertEqual({}, out["r9_5_project_stability_design_basis_decision"]["source_records"])

    def test_12_package_b_ignores_non_r95_document_without_project_id(self):
        d = {"unrelated": True}
        out = apply_package_b_traceability_to_r9_5_required_input_document(
            d,
            repo_root=ROOT,
            registry_path=self.b_registry,
        )
        self.assertEqual(d, out)


if __name__ == "__main__":
    unittest.main()
