from __future__ import annotations

from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from phoenix.local_app.integrated_project_bridge import OfficialStartIntegratedProjectBridge


ROOT = Path(__file__).resolve().parents[2]


class _FakeService:
    def run(self, contract):
        count = len(contract.get("design_variants") or [])
        status = "HOLD_MISSING_VERIFIED_INPUTS" if count == 5 else "WAITING_FOR_FIVE_VARIANTS"
        return {
            "status": status,
            "concept_variant_count": 5,
            "selected_variant_id": contract.get("selected_variant_id"),
            "stages": [
                {"order": 20, "stage_id": "site_and_regulatory_analysis", "status": "EVIDENCE_VERIFIED", "missing_evidence": []},
                {"order": 30, "stage_id": "five_design_variants", "status": "EVIDENCE_VERIFIED" if count == 5 else "WAITING_FOR_FIVE_VARIANTS", "missing_evidence": []},
            ],
            "discipline_plan": {"engines": [f"engine-{index}" for index in range(14)]},
            "shared_model": "PHOENIX_DIGITAL_TWIN",
            "result_sha256": hashlib.sha256(str(count).encode()).hexdigest(),
        }


class Phase19FixR4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (ROOT / "phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_phase19_integrated_project_bridge_v1_0.js").read_text(encoding="utf-8")
        cls.server = (ROOT / "phoenix/local_app/server.py").read_text(encoding="utf-8")

    def bridge(self, root: Path) -> OfficialStartIntegratedProjectBridge:
        value = object.__new__(OfficialStartIntegratedProjectBridge)
        value.repository = root
        value.service = _FakeService()
        value.output_root = root / "outputs/runtime/phase19_start_screen_bridge"
        return value

    @staticmethod
    def fixture(root: Path):
        batch = "20261005T140000Z_cafebabe"
        folder = root / "inputs/runtime/official_start_v3_uploads" / batch
        folder.mkdir(parents=True)
        (folder / "terrain.png").write_bytes(b"parcel-314-terrain")
        (folder / "upload_manifest.json").write_text(json.dumps({
            "batch_id": batch,
            "file_count": 1,
            "files": [{"name": "terrain.png", "size_bytes": 18}],
        }), encoding="utf-8")
        for relative in (
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"status":"REFERENCE_ONLY"}\n', encoding="utf-8")
        session = {
            "session_id": "PHX-20261005T140000Z-cafebabe",
            "project_type": "BOUW",
            "project_mode": "autonomous",
            "brief": "Urban villa 300 m2, 2 verdiepingen, 3 slaapkamers, garage voor 2 wagens.",
            "location_reference": "Perceel 314, Heliosstraat / Plutostraat",
            "upload_batch": batch,
            "desired_outputs": ["drawings", "calculations", "cost_estimate"],
        }
        return batch, session

    def test_01_upload_bytes_and_hash_are_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch, _ = self.fixture(root)
            proof = self.bridge(root).validate_upload_batch(batch)
            self.assertTrue(proof["verified"])
            self.assertEqual(proof["files"][0]["sha256"], hashlib.sha256(b"parcel-314-terrain").hexdigest())

    def test_02_upload_scope_does_not_claim_survey_or_cadastre(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch, _ = self.fixture(root)
            proof = self.bridge(root).validate_upload_batch(batch)
            self.assertFalse(proof["survey_verified"])
            self.assertFalse(proof["cadastral_verified"])
            self.assertFalse(proof["professional_release_eligible"])

    def test_03_tampered_upload_size_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch, _ = self.fixture(root)
            (root / "inputs/runtime/official_start_v3_uploads" / batch / "terrain.png").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "UPLOAD_FILE_SIZE_DENY"):
                self.bridge(root).validate_upload_batch(batch)

    def test_04_exact_five_ordered_variants_are_generated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, session = self.fixture(root)
            result = self.bridge(root).prepare_concept_inputs(session, "P19-0123456789ABCDEF")
            self.assertEqual([x["variant_id"] for x in result["design_variants"]], list("ABCDE"))
            self.assertEqual(len({x["strategy"] for x in result["design_variants"]}), 5)

    def test_05_project_constraints_are_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, session = self.fixture(root)
            result = self.bridge(root).prepare_concept_inputs(session, "P19-0123456789ABCDEF")
            project = result["project"]
            self.assertEqual(project["program"]["target_floor_area_m2"], 300.0)
            self.assertEqual(project["program"]["storeys"], 2)
            self.assertEqual(project["preferences"]["garage_spaces"], 2)
            self.assertEqual(project["site"]["floor_level_nap_m"], 1.50)

    def test_06_flat_roof_and_raised_floor_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, session = self.fixture(root)
            variants = self.bridge(root).prepare_concept_inputs(session, "P19-0123456789ABCDEF")["design_variants"]
            self.assertTrue(all(x["roof_pitch_deg"] == 0 for x in variants))
            self.assertTrue(all(x["raised_floor_m"] == 0.65 for x in variants))

    def test_07_manifest_and_ten_variant_files_exist(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, session = self.fixture(root)
            result = self.bridge(root).prepare_concept_inputs(session, "P19-0123456789ABCDEF")
            self.assertTrue((root / result["manifest_path"]).is_file())
            for item in result["variant_files"]:
                self.assertTrue((root / item["svg_path"]).is_file())
                self.assertTrue((root / item["json_path"]).is_file())

    def test_08_evidence_is_valid_but_professionally_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, session = self.fixture(root)
            evidence = self.bridge(root).prepare_concept_inputs(session, "P19-0123456789ABCDEF")["evidence"]
            location = evidence["site_and_regulatory_analysis"]["location_evidence"]
            rules = evidence["site_and_regulatory_analysis"]["applicable_rules"]
            self.assertTrue(location["verified"])
            self.assertFalse(location["survey_verified"])
            self.assertFalse(rules["legal_applicability_verified"])

    def test_09_request_fingerprint_ignores_session_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, first = self.fixture(root)
            second = dict(first, session_id="PHX-OTHER")
            bridge = self.bridge(root)
            self.assertEqual(bridge._request_fingerprint(bridge.build_contract(first)), bridge._request_fingerprint(bridge.build_contract(second)))

    def test_10_duplicate_request_reuses_existing_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, session = self.fixture(root)
            bridge = self.bridge(root)
            first = bridge.plan(session)
            second = bridge.plan(dict(session, session_id="PHX-OTHER"))
            self.assertEqual(first.run_id, second.run_id)
            self.assertTrue(second.payload["duplicate_run_reused"])

    def test_11_resume_generates_and_binds_concept_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch, session = self.fixture(root)
            bridge = self.bridge(root)
            session_root = root / "outputs/runtime/phoenix_start_v3_sessions"
            session_root.mkdir(parents=True)
            (session_root / f'{session["session_id"]}.json').write_text(json.dumps(session), encoding="utf-8")
            held = bridge.plan(session)
            resumed = bridge.resume(held.run_id, {"location_reference": session["location_reference"], "upload_batch": batch})
            self.assertEqual(resumed.payload["concept_package"]["variant_count"], 5)
            self.assertEqual(resumed.payload["concept_package"]["release_status"], "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION")

    def test_12_client_auto_resumes_held_run(self):
        self.assertIn('if (!plan.concept_package', self.js)
        self.assertIn('"/api/integrated-project/resume"', self.js)

    def test_13_client_exposes_variant_links(self):
        self.assertIn('item.svg_path', self.js)
        self.assertIn('Variant ${esc(item.variant_id)}', self.js)

    def test_14_server_reports_bridge_version(self):
        self.assertIn('"integrated_project_orchestration_bridge": "1.1.0"', self.server)

    def test_15_release_boundaries_are_visible(self):
        self.assertIn("kadastrale grens", self.js)
        self.assertIn("professionele vrijgave", self.js)


if __name__ == "__main__":
    unittest.main()
