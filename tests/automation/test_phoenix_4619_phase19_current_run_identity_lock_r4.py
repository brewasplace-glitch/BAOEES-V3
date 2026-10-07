from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from phoenix.local_app.integrated_project_bridge import OfficialStartIntegratedProjectBridge

class _FakeService:
    def run(self, contract):
        return {
            "status": "HOLD_MISSING_VERIFIED_INPUTS",
            "concept_variant_count": len(contract.get("design_variants") or []),
            "selected_variant_id": None,
            "stages": [],
            "discipline_plan": {"engines":[]},
            "shared_model": "PHOENIX_DIGITAL_TWIN",
            "result_sha256": hashlib.sha256(
                json.dumps(contract, sort_keys=True, default=str).encode()
            ).hexdigest(),
        }

class CurrentRunIdentityLockR4(unittest.TestCase):
    RUN_ID = "P19-ABCDEF0123456789"

    def bridge(self, root):
        obj = object.__new__(OfficialStartIntegratedProjectBridge)
        obj.repository = root
        obj.service = _FakeService()
        obj.output_root = root / "outputs/runtime/phase19_start_screen_bridge"
        return obj

    def configs(self, root):
        for rel in (
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('{"status":"REFERENCE_ONLY"}\n', encoding="utf-8")

    def test_force_replan_keeps_exact_run_identity_and_variant_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.configs(root)
            session = {
                "session_id":"PHX-R4-IDENTITY",
                "project_type":"BOUW",
                "project_mode":"autonomous",
                "brief":"Tropische woning met 2 verdiepingen en 3 slaapkamers.",
                "location_reference":"Paramaribo Noord, Suriname",
                "upload_batch":None,
                "desired_outputs":["drawings","ifc","digital_twin"],
                "phase19_r4_source_run_id":self.RUN_ID,
            }
            result = self.bridge(root).plan(session, persist=True, force_replan=True)
            self.assertEqual(result.run_id, self.RUN_ID)
            pkg = result.payload["concept_package"]
            self.assertEqual(pkg["source_run_id"], self.RUN_ID)
            self.assertEqual(pkg["variant_provider"], "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1")
            self.assertTrue(all(self.RUN_ID in x["svg_path"] for x in pkg["variant_files"]))
            self.assertTrue(all("/real_spatial/" in x["svg_path"] for x in pkg["variant_files"]))

    def test_source_contains_identity_lock(self):
        root=Path(__file__).resolve().parents[2]
        src=(root/"phoenix/local_app/integrated_project_bridge.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_4_6_19_PHASE19_CURRENT_RUN_IDENTITY_LOCK_R4", src)
        self.assertIn("PHASE19_LOCKED_RUN_ID_DENY", src)
        self.assertIn('"source_run_id": run_id', src)

if __name__=="__main__":
    unittest.main()
