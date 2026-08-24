import json
import unittest
from pathlib import Path

from phoenix.local_app.professional_output_level_contract_v1_0 import (
    LEVEL_A,
    LEVEL_B,
    STATE_A_PROFESSIONAL,
    STATE_B_PENDING,
    STATE_B_RELEASED,
    STATE_B_REVIEW_REQUIRED,
    OutputLevelContractError,
    append_brief_markers,
    build_output_level_contract,
    normalize_project_start_payload,
    normalize_target_level,
    resolve_output_state,
)


REPO = Path(__file__).resolve().parents[2]
JS_NAME = "PROJECT_PHOENIX_professional_country_aware_end_to_end_ab_v1_0.js"


class ProfessionalOutputLevelContractTests(unittest.TestCase):
    def test_default_level_is_a(self):
        self.assertEqual(normalize_target_level(None), LEVEL_A)

    def test_b_normalizes(self):
        self.assertEqual(normalize_target_level("B"), LEVEL_B)

    def test_invalid_level_fails(self):
        with self.assertRaises(OutputLevelContractError):
            normalize_target_level("C")

    def test_a_is_professional_not_release(self):
        self.assertEqual(resolve_output_state("A"), STATE_A_PROFESSIONAL)

    def test_b_without_evidence_is_pending(self):
        self.assertEqual(resolve_output_state("B"), STATE_B_PENDING)

    def test_b_with_evidence_can_be_released(self):
        self.assertEqual(
            resolve_output_state(
                "B",
                professional_review_complete=True,
                release_gates_closed=True,
                materials_and_project_inputs_verified=True,
                revision_fingerprint="abc",
            ),
            STATE_B_RELEASED,
        )

    def test_released_revision_change_requires_review(self):
        self.assertEqual(
            resolve_output_state(
                "B",
                previous_state=STATE_B_RELEASED,
                professional_review_complete=True,
                release_gates_closed=True,
                materials_and_project_inputs_verified=True,
                revision_fingerprint="new",
                released_revision_fingerprint="old",
            ),
            STATE_B_REVIEW_REQUIRED,
        )

    def test_contract_requires_country_aware_costing(self):
        contract = build_output_level_contract("A", project_id="P1", country_code="SR")
        self.assertTrue(contract["country_aware_costing_required"])
        self.assertEqual(contract["country_code"], "SR")
        self.assertFalse(contract["formal_release"]["automatic_for_construction_release"])

    def test_same_project_a_to_b(self):
        contract = build_output_level_contract("B", project_id="P1")
        self.assertTrue(contract["same_project_transition"]["A_to_B"])
        self.assertFalse(contract["same_project_transition"]["new_project_required"])

    def test_payload_marker_and_fail_closed(self):
        payload = normalize_project_start_payload({"brief": "Ontwerp woning"}, target_level="B")
        self.assertEqual(payload["professional_output_state"], STATE_B_PENDING)
        self.assertTrue(payload["formal_release_fail_closed"])
        self.assertFalse(payload["automatic_professional_approval"])
        self.assertIn("[PHOENIX_PROFESSIONAL_OUTPUT_LEVEL_TARGET=B]", payload["brief"])
        self.assertIn("[PHOENIX_COUNTRY_AWARE_COSTING=REQUIRED]", payload["brief"])

    def test_markers_replace_previous_level(self):
        brief = "X\n[PHOENIX_PROFESSIONAL_OUTPUT_LEVEL_TARGET=A]"
        result = append_brief_markers(brief, target_level="B")
        self.assertNotIn("TARGET=A", result)
        self.assertIn("TARGET=B", result)

    def test_startscreen_script_is_installed_and_injected(self):
        matches = list(REPO.rglob(JS_NAME))
        self.assertEqual(len(matches), 1, matches)
        js = matches[0].read_text(encoding="utf-8-sig")
        self.assertIn("A — PROFESSIONELE PROJECTOUTPUT", js)
        self.assertIn("B — FORMEEL GECONTROLEERD / VOOR UITVOERING", js)
        self.assertIn("country_aware_costing_required", js)
        self.assertIn("automatic_for_construction_release = false", js)

        hosts = list(REPO.rglob("PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"))
        self.assertEqual(len(hosts), 1, hosts)
        host = hosts[0].read_text(encoding="utf-8-sig")
        self.assertIn(JS_NAME, host)
        self.assertIn("document.createElement", host)

    def test_policy_files_parse(self):
        for rel in (
            "configs/phoenix/professional_country_aware_end_to_end_policy_v1_0.json",
            "configs/phoenix/startscreen_capabilities/professional_country_aware_end_to_end_ab_v1_0.json",
        ):
            data = json.loads((REPO / rel).read_text(encoding="utf-8-sig"))
            self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
