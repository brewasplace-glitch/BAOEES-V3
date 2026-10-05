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
        missing = not bool(contract.get("location_reference"))
        status = "HOLD_MISSING_PROJECT_INPUTS" if missing else "WAITING_FOR_EVIDENCE"
        return {
            "status": status,
            "concept_variant_count": 0,
            "selected_variant_id": None,
            "stages": [{
                "order": 10,
                "stage_id": "project_intake",
                "status": status,
                "missing_evidence": [],
            }],
            "discipline_plan": {"engines": [f"engine-{index}" for index in range(14)]},
            "shared_model": "PHOENIX_DIGITAL_TWIN",
            "result_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        }


class Phase19FixR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_phase19_integrated_project_bridge_v1_0.js").read_text(encoding="utf-8")
        cls.visual = (ROOT / "phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js").read_text(encoding="utf-8")
        cls.server = (ROOT / "phoenix/local_app/server.py").read_text(encoding="utf-8")

    def bridge(self, root: Path) -> OfficialStartIntegratedProjectBridge:
        value = object.__new__(OfficialStartIntegratedProjectBridge)
        value.repository = root
        value.service = _FakeService()
        value.output_root = root / "outputs/runtime/phase19_start_screen_bridge"
        return value

    @staticmethod
    def session():
        return {
            "session_id": "PHX-20261004T234700Z-deadbeef",
            "project_type": "BOUW",
            "project_mode": "autonomous",
            "brief": "Ontwerp urban villa.",
            "selected_project": "",
            "location_reference": "",
            "upload_batch": None,
            "desired_outputs": ["reports", "drawings"],
        }

    @staticmethod
    def upload(root: Path, batch_id="20261004T234700Z_deadbeef"):
        folder = root / "inputs/runtime/official_start_v3_uploads" / batch_id
        folder.mkdir(parents=True)
        (folder / "terrain.png").write_bytes(b"terrain")
        manifest = {
            "batch_id": batch_id,
            "file_count": 1,
            "files": [{"name": "terrain.png", "size_bytes": 7}],
        }
        (folder / "upload_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        for relative in (
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        return batch_id

    def test_01_location_input_visible(self):
        self.assertIn('id="locationReference"', self.html)

    def test_02_resume_input_visible(self):
        self.assertIn('id="phase19ResumeRun"', self.html)

    def test_03_client_never_hardcodes_empty_location(self):
        self.assertNotIn('location_reference: ""', self.js)

    def test_04_client_sends_location(self):
        self.assertIn("location_reference: locationReference", self.js)

    def test_05_client_sends_upload_batch(self):
        self.assertIn("upload_batch: uploadBatch", self.js)

    def test_06_visual_exposes_upload_batch(self):
        self.assertIn("window.PHOENIX_UPLOAD_BATCH = state.uploadBatch", self.visual)

    def test_07_resume_route_present(self):
        self.assertIn('/api/integrated-project/resume', self.js)
        self.assertIn('parsed.path == "/api/integrated-project/resume"', self.server)

    def test_08_invalid_batch_id_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "UPLOAD_BATCH_ID_DENY"):
                self.bridge(Path(temporary)).validate_upload_batch("../escape")

    def test_09_missing_batch_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "UPLOAD_BATCH_NOT_FOUND"):
                self.bridge(Path(temporary)).validate_upload_batch("20261004T234700Z_deadbeef")

    def test_10_upload_files_are_integrity_verified_with_limited_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = self.upload(root)
            proof = self.bridge(root).validate_upload_batch(batch)
            self.assertEqual(proof["file_count"], 1)
            self.assertTrue(proof["verified"])
            self.assertFalse(proof["survey_verified"])
            self.assertFalse(proof["cadastral_verified"])
            self.assertEqual(len(proof["files"][0]["sha256"]), 64)
            self.assertEqual(len(proof["manifest_sha256"]), 64)

    def test_11_contract_binds_location_and_upload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch = self.upload(root)
            session = self.session()
            session["location_reference"] = "Perceel 314, Paramaribo"
            session["upload_batch"] = batch
            contract = self.bridge(root).build_contract(session)
            self.assertEqual(contract["location_reference"], "Perceel 314, Paramaribo")
            self.assertEqual(contract["start_screen_context"]["upload_batch"], batch)
            self.assertTrue(contract["evidence"]["project_uploads"]["verified"])

    def test_12_safe_resume_updates_exact_prior_session(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge = self.bridge(root)
            session = self.session()
            session_dir = root / "outputs/runtime/phoenix_start_v3_sessions"
            session_dir.mkdir(parents=True)
            session_path = session_dir / f'{session["session_id"]}.json'
            session_path.write_text(json.dumps(session), encoding="utf-8")
            held = bridge.plan(session, persist=True)
            batch = self.upload(root)
            resumed = bridge.resume(held.run_id, {
                "location_reference": "Perceel 314, Paramaribo",
                "upload_batch": batch,
            })
            self.assertTrue(resumed.payload["safe_resume"])
            self.assertEqual(resumed.payload["resumed_from_run_id"], held.run_id)
            self.assertNotEqual(resumed.run_id, held.run_id)
            stored = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["location_reference"], "Perceel 314, Paramaribo")
            self.assertEqual(stored["upload_batch"], batch)

    def test_13_professional_review_status_resume_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge = self.bridge(root)
            bridge.output_root.mkdir(parents=True)
            run_id = "P19-0123456789ABCDEF"
            (bridge.output_root / f"{run_id}.json").write_text(
                json.dumps({"status": "READY_FOR_PROFESSIONAL_REVIEW"}), encoding="utf-8"
            )
            batch = self.upload(root)
            with self.assertRaisesRegex(ValueError, "RESUME_STATUS_DENY"):
                bridge.resume(run_id, {"location_reference": "site", "upload_batch": batch})


if __name__ == "__main__":
    unittest.main()
