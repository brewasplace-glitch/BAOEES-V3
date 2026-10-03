from __future__ import annotations

from pathlib import Path
import hashlib
import json
import unittest

from phoenix.autonomy import IntegratedProjectOrchestrationService
from phoenix.autonomy.integrated_project_orchestration import EXPECTED_STAGES
from phoenix.autonomy.multidisciplinary_engine_suite import object_sha256


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name: str) -> dict:
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


class Phase18IntegratedProjectOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.service = IntegratedProjectOrchestrationService.from_repo(ROOT)
        self.catalog = load("integrated_project_orchestration_v1.json")

    def project(self, evidence=True):
        variants = [{"variant_id": f"V{i}"} for i in range(1, 6)]
        verified = {
            descriptor.key: {name: f"verified:{name}" for name in descriptor.required_inputs}
            for descriptor in self.service.discipline_service.descriptors
        }
        ledger = {}
        if evidence:
            for stage in self.service.stages:
                ledger[stage.stage_id] = {}
                for name in stage.required_evidence:
                    ledger[stage.stage_id][name] = {
                        "artifact_id": f"{stage.stage_id}:{name}",
                        "source": "unit-test",
                        "verified": True,
                        "sha256": hashlib.sha256(f"{stage.stage_id}:{name}".encode()).hexdigest(),
                    }
        return {
            "project_id": "P18-TEST",
            "instruction": "Design and document a complete project.",
            "location_reference": "test:site",
            "requested_outputs": ["drawings", "calculations", "cost", "planning", "reports"],
            "design_variants": variants,
            "selected_variant_id": "V1",
            "verified_inputs": verified,
            "evidence": ledger,
        }

    def test_01_schema(self): self.assertEqual(self.catalog["schema"], "PHOENIX_INTEGRATED_PROJECT_ORCHESTRATION_V1")
    def test_02_active(self): self.assertEqual(self.catalog["status"], "ACTIVE_GOVERNED")
    def test_03_fail_closed(self): self.assertTrue(self.catalog["fail_closed"])
    def test_04_exact_five_variants(self): self.assertEqual(self.catalog["concept_variant_count"], 5)
    def test_05_exact_fourteen_disciplines(self): self.assertEqual(self.catalog["multidisciplinary_engine_count"], 14)
    def test_06_shared_digital_twin(self): self.assertEqual(self.catalog["shared_model"], "PHOENIX_DIGITAL_TWIN")
    def test_07_no_repo_mutation(self): self.assertFalse(self.catalog["automatic_repository_mutation"])
    def test_08_no_engine_activation(self): self.assertFalse(self.catalog["automatic_engine_activation"])
    def test_09_no_auto_release(self): self.assertFalse(self.catalog["automatic_professional_release"])
    def test_10_professional_release_required(self): self.assertTrue(self.catalog["professional_release_required"])
    def test_11_hash_evidence_required(self): self.assertTrue(self.catalog["evidence_sha256_required"])
    def test_12_exact_stage_count(self): self.assertEqual(len(self.service.stages), 15)
    def test_13_exact_stage_order(self): self.assertEqual(tuple(x.stage_id for x in self.service.stages), EXPECTED_STAGES)
    def test_14_unique_stages(self): self.assertEqual(len({x.stage_id for x in self.service.stages}), 15)
    def test_15_dependencies_precede(self):
        order = {x.stage_id: x.order for x in self.service.stages}
        self.assertTrue(all(order[d] < x.order for x in self.service.stages for d in x.dependencies))
    def test_16_all_require_evidence(self): self.assertTrue(all(x.required_evidence for x in self.service.stages))
    def test_17_all_declare_outputs(self): self.assertTrue(all(x.outputs for x in self.service.stages))
    def test_18_all_bind_modules(self): self.assertTrue(all(x.module_bindings for x in self.service.stages))
    def test_19_project_id_required(self):
        with self.assertRaisesRegex(ValueError, "PROJECT_ID_REQUIRED"): self.service.run({})
    def test_20_evidence_object_required(self):
        project = self.project(); project["evidence"] = []
        with self.assertRaisesRegex(ValueError, "EVIDENCE_OBJECT_REQUIRED"): self.service.run(project)
    def test_21_wrong_variant_count_denied(self):
        project = self.project(); project["design_variants"] = project["design_variants"][:4]
        with self.assertRaisesRegex(ValueError, "EXACT_FIVE_UNIQUE"): self.service.run(project)
    def test_22_duplicate_variants_denied(self):
        project = self.project(); project["design_variants"][4]["variant_id"] = "V1"
        with self.assertRaisesRegex(ValueError, "EXACT_FIVE_UNIQUE"): self.service.run(project)
    def test_23_unknown_selection_denied(self):
        project = self.project(); project["selected_variant_id"] = "V9"
        with self.assertRaisesRegex(ValueError, "SELECTED_VARIANT_NOT_FOUND"): self.service.run(project)
    def test_24_missing_evidence_waits(self):
        self.assertEqual(self.service.run(self.project(False))["status"], "WAITING_FOR_EVIDENCE")
    def test_25_missing_verified_inputs_holds(self):
        project = self.project(); project["verified_inputs"] = {}
        self.assertEqual(self.service.run(project)["status"], "HOLD_MISSING_VERIFIED_INPUTS")
    def test_26_complete_evidence_ready_for_review(self):
        self.assertEqual(self.service.run(self.project())["status"], "READY_FOR_PROFESSIONAL_REVIEW")
    def test_27_never_professionally_released(self): self.assertFalse(self.service.run(self.project())["professional_release"])
    def test_28_never_mutates_repo(self): self.assertFalse(self.service.run(self.project())["repository_mutation"])
    def test_29_never_activates_engines(self): self.assertFalse(self.service.run(self.project())["automatic_engine_activation"])
    def test_30_exact_fourteen_engine_rows(self): self.assertEqual(len(self.service.run(self.project())["discipline_plan"]["engines"]), 14)
    def test_31_no_outputs_fabricated(self): self.assertTrue(all(not x["outputs_claimed_produced"] for x in self.service.run(self.project())["stages"]))
    def test_32_result_digest_bound(self):
        result = self.service.run(self.project())
        self.assertEqual(result["result_sha256"], object_sha256({k:v for k,v in result.items() if k != "result_sha256"}))
    def test_33_bad_hash_waits(self):
        project = self.project(); project["evidence"]["project_intake"]["project_brief"]["sha256"] = "bad"
        self.assertEqual(self.service.run(project)["stages"][0]["status"], "WAITING_FOR_EVIDENCE")
    def test_34_unverified_evidence_waits(self):
        project = self.project(); project["evidence"]["project_intake"]["project_brief"]["verified"] = False
        self.assertEqual(self.service.run(project)["stages"][0]["status"], "WAITING_FOR_EVIDENCE")
    def test_35_calculations_bound(self): self.assertIn("verified_calculation_set", next(x for x in self.service.stages if x.stage_id == "calculation_verification").outputs)
    def test_36_drawings_bound(self): self.assertIn("plans", next(x for x in self.service.stages if x.stage_id == "drawing_production").outputs)
    def test_37_cost_bound(self): self.assertIn("cost_estimate", next(x for x in self.service.stages if x.stage_id == "cost_estimation").outputs)
    def test_38_planning_bound(self): self.assertIn("construction_schedule", next(x for x in self.service.stages if x.stage_id == "construction_planning").outputs)
    def test_39_permits_bound(self): self.assertIn("permit_dossier", next(x for x in self.service.stages if x.stage_id == "permit_documentation").outputs)
    def test_40_reporting_bound(self): self.assertIn("technical_reports", next(x for x in self.service.stages if x.stage_id == "integrated_reporting").outputs)
    def test_41_dossier_bound(self): self.assertIn("complete_project_dossier", next(x for x in self.service.stages if x.stage_id == "complete_project_dossier").outputs)
    def test_42_synthetic_proof(self): self.assertEqual(self.service.synthetic_proof()["status"], "PASS")
    def test_43_proof_has_fifteen_stages(self): self.assertEqual(self.service.synthetic_proof()["stage_count"], 15)
    def test_44_proof_has_fourteen_disciplines(self): self.assertEqual(self.service.synthetic_proof()["discipline_count"], 14)
    def test_45_result_schema_present(self): self.assertEqual(load("integrated_project_run_v1.schema.json")["properties"]["schema"]["const"], "PHOENIX_INTEGRATED_PROJECT_RUN_V1")
    def test_46_open_source_review_present(self): self.assertEqual(load("open_source_phase18_project_orchestration_review_v1.json")["decision"], "ADMIT_GOVERNED_EXISTING_BINDINGS")
    def test_47_policy_manifest_binds_orchestration(self): self.assertIn("integrated_project_orchestration_v1.json", load("policy_bundle_manifest_v1.json")["files"])


if __name__ == "__main__":
    unittest.main()
