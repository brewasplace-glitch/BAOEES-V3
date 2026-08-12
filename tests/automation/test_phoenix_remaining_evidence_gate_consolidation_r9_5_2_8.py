from __future__ import annotations

import unittest
from pathlib import Path

from phoenix.autonomy.remaining_evidence_gate_consolidation_r9_5_2_8 import (
    BLOCKED_STATUS,
    ELIGIBLE_STATUS,
    EXECUTED_STATUS,
    PACKAGE_C_ID,
    PACKAGE_D_ID,
    PACKAGE_E_ID,
    READY_STATUS,
    RUNTIME_CONTEXT_INCOMPLETE,
    consolidate_remaining_evidence_gates,
    consolidation_template,
    run_remaining_evidence_gate_consolidation_r9_5_2_8,
)


def eligible(package_id: str) -> dict:
    return {
        "package_id": package_id,
        "status": ELIGIBLE_STATUS,
        "eligible_for_r9_5_promotion": True,
    }


class RemainingEvidenceGateConsolidationR9528Tests(unittest.TestCase):
    def test_01_template_creates_no_engineered_values(self):
        value = consolidation_template()
        self.assertEqual("NO_NEW_ENGINEERED_VALUES_CREATED_BY_R9_5_2_8", value["human_input_policy"])
        self.assertEqual([PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID], value["required_packages"])

    def test_02_missing_packages_remain_blocked(self):
        result = consolidate_remaining_evidence_gates({})
        self.assertEqual(BLOCKED_STATUS, result["status"])
        self.assertFalse(result["all_remaining_evidence_gates_satisfied"])
        self.assertEqual(3, len(result["remaining_evidence"]))
        self.assertFalse(result["requalification"]["authorized_by_evidence_gate"])

    def test_03_recursive_discovery_finds_c_d_e(self):
        context = {
            "deep": {
                "package_inputs": {
                    PACKAGE_C_ID: eligible(PACKAGE_C_ID),
                    PACKAGE_D_ID: eligible(PACKAGE_D_ID),
                    PACKAGE_E_ID: eligible(PACKAGE_E_ID),
                }
            }
        }
        result = consolidate_remaining_evidence_gates(context)
        self.assertEqual(READY_STATUS, result["status"])
        self.assertTrue(result["all_remaining_evidence_gates_satisfied"])

    def test_04_single_incomplete_gate_prevents_requalification_callback(self):
        context = {
            "_phoenix_package_c_r9_5_2_6": eligible(PACKAGE_C_ID),
            "_phoenix_package_d_r9_5_2_7": eligible(PACKAGE_D_ID),
            "_phoenix_package_e_r9_5_2_5": {
                "package_id": PACKAGE_E_ID,
                "status": "INPUT_REQUIRED",
                "eligible_for_r9_5_promotion": False,
            },
        }
        called = []
        def callback(**kwargs):
            called.append(kwargs)
            return {"status": "SHOULD_NOT_RUN"}

        result = run_remaining_evidence_gate_consolidation_r9_5_2_8(
            context, requalification_callable=callback
        )
        self.assertEqual(BLOCKED_STATUS, result["status"])
        self.assertEqual([], called)
        self.assertFalse(result["requalification"]["attempted"])

    def test_05_all_eligible_but_runtime_context_missing_does_not_invent_execution(self):
        context = {
            "_phoenix_package_c_r9_5_2_6": eligible(PACKAGE_C_ID),
            "_phoenix_package_d_r9_5_2_7": eligible(PACKAGE_D_ID),
            "_phoenix_package_e_r9_5_2_5": eligible(PACKAGE_E_ID),
        }
        result = run_remaining_evidence_gate_consolidation_r9_5_2_8(
            context, requalification_callable=lambda **kwargs: {"status": "UNREACHABLE"}
        )
        self.assertEqual(RUNTIME_CONTEXT_INCOMPLETE, result["status"])
        self.assertFalse(result["requalification"]["attempted"])
        self.assertIn("project_id", result["requalification"]["missing_runtime_context"])

    def test_06_all_gates_complete_executes_existing_requalification_and_preserves_result(self):
        context = {
            "_phoenix_package_c_r9_5_2_6": eligible(PACKAGE_C_ID),
            "_phoenix_package_d_r9_5_2_7": eligible(PACKAGE_D_ID),
            "_phoenix_package_e_r9_5_2_5": eligible(PACKAGE_E_ID),
            "project_id": "PHX-TEST",
            "workspace": Path("C:/work"),
            "repository": Path("C:/repo"),
            "_phx_r93": {"status": "R93"},
            "_phx_r94": {"status": "R94"},
            "_phx_r95": {"status": "BLOCKED"},
            "_phx_r951": {"status": "R951"},
            "_phx_r952": {"evidence_intake": {}},
        }
        captured = {}
        def callback(**kwargs):
            captured.update(kwargs)
            return {
                "status": "BLOCKED",
                "qualified": False,
                "unresolved_check_types": ["EXAMPLE_REMAINING"],
            }

        result = run_remaining_evidence_gate_consolidation_r9_5_2_8(
            context, requalification_callable=callback
        )
        self.assertEqual(EXECUTED_STATUS, result["status"])
        self.assertTrue(result["requalification"]["attempted"])
        self.assertEqual("BLOCKED", result["requalification"]["result"]["status"])
        self.assertFalse(result["requalification"]["result"]["qualified"])
        package_inputs = captured["r952_initial"]["evidence_intake"]["package_inputs"]
        self.assertEqual({PACKAGE_C_ID, PACKAGE_D_ID, PACKAGE_E_ID}, set(package_inputs))
        self.assertEqual(
            Path("C:/repo").joinpath(
                "configs", "phoenix", "structural",
                "stability_ab_project_policy_r9_5_2_2.json"
            ),
            captured["ab_policy_path"],
        )

    def test_07_package_e_explicit_independent_completion_may_satisfy_e_gate(self):
        context = {
            "_phoenix_package_c_r9_5_2_6": eligible(PACKAGE_C_ID),
            "_phoenix_package_d_r9_5_2_7": eligible(PACKAGE_D_ID),
            "_phoenix_package_e_r9_5_2_5": {
                "package_id": PACKAGE_E_ID,
                "status": "INDEPENDENT_EVIDENCE_COMPLETE",
                "independent_evidence_complete": True,
                "independent_review_complete": True,
                "acceptance_criterion_traceability_complete": True,
            },
        }
        result = consolidate_remaining_evidence_gates(context)
        self.assertTrue(result["gates"]["package_e"]["eligible_for_later_r9_5_promotion"])
        self.assertTrue(result["all_remaining_evidence_gates_satisfied"])

    def test_08_safety_locks_never_change(self):
        result = consolidate_remaining_evidence_gates({})
        safety = result["safety"]
        self.assertFalse(safety["automatic_seismic_applicability_decision"])
        self.assertFalse(safety["automatic_numerical_criteria_generation"])
        self.assertFalse(safety["automatic_screening_proxy_acceptance"])
        self.assertFalse(safety["automatic_independent_evidence_generation"])
        self.assertFalse(safety["automatic_professional_approval"])
        self.assertFalse(safety["automatic_code_compliance_claim"])
        self.assertFalse(safety["automatic_r9_5_success_claim"])
        self.assertEqual("LOCKED", safety["production_release"])
        self.assertEqual("LOCKED", safety["for_construction_release"])


if __name__ == "__main__":
    unittest.main()
