from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
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


class OptionalUploadRealVariantsR3(unittest.TestCase):
    def bridge(self, root: Path) -> OfficialStartIntegratedProjectBridge:
        obj=object.__new__(OfficialStartIntegratedProjectBridge)
        obj.repository=root
        obj.service=_FakeService()
        obj.output_root=root/"outputs/runtime/phase19_start_screen_bridge"
        return obj

    def fixture(self):
        return {
            "session_id":"PHX-R3-NO-UPLOAD",
            "project_type":"BOUW",
            "project_mode":"autonomous",
            "brief":"Tropische woning met 2 verdiepingen, 3 slaapkamers en garage.",
            "location_reference":"Paramaribo Noord, Suriname",
            "upload_batch":None,
            "desired_outputs":["drawings","ifc","digital_twin"],
        }

    def configs(self, root: Path):
        for rel in (
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ):
            p=root/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('{"status":"REFERENCE_ONLY"}\n',encoding="utf-8")

    def test_no_upload_still_generates_current_run_real_spatial_variants(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.configs(root)
            result=self.bridge(root).plan(self.fixture())
            pkg=result.payload["concept_package"]

            self.assertEqual(pkg["variant_provider"],"PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1")
            self.assertEqual(len(pkg["variant_files"]),5)
            self.assertTrue(all("/real_spatial/" in x["svg_path"] for x in pkg["variant_files"]))
            self.assertTrue((root/pkg["real_spatial_manifest_path"]).is_file())

    def test_missing_upload_is_not_falsely_verified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.configs(root)
            bridge=self.bridge(root)
            result=bridge.plan(self.fixture())
            concept=bridge.prepare_concept_inputs(self.fixture(),result.run_id)
            ev=concept["evidence"]["site_and_regulatory_analysis"]["location_evidence"]
            self.assertFalse(ev["verified"])
            self.assertEqual(ev["source"],"official-start-user-declared-location")
            self.assertIn("project_uploads",ev["missing_evidence"])

    def test_nonpersistent_plan_remains_side_effect_free(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.configs(root)
            result=self.bridge(root).plan(self.fixture(), persist=False)

            # This local fake service intentionally returns no stage rows.
            # The canonical bridge regression test verifies the exact
            # WAITING_FOR_FIVE_VARIANTS stage contract. Here we verify only
            # the R3 invariant: persist=False must not author a concept package
            # or create Phase-19 runtime output.
            self.assertNotIn("concept_package", result.payload)
            self.assertFalse(
                (root/"outputs/runtime/phase19_start_screen_bridge").exists()
            )

    def test_source_contains_optional_upload_gate(self):
        root=Path(__file__).resolve().parents[2]
        src=(root/"phoenix/local_app/integrated_project_bridge.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_4_6_19_PHASE19_OPTIONAL_UPLOAD_REAL_VARIANTS_R3",src)
        self.assertIn("USER_DECLARED_LOCATION_ONLY_NO_UPLOAD",src)


if __name__=="__main__":
    unittest.main()
