from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.local_app.integrated_project_bridge import OfficialStartIntegratedProjectBridge


class _FakeService:
    def run(self, contract):
        count=len(contract.get("design_variants") or [])
        return {
            "status": "HOLD_MISSING_VERIFIED_INPUTS",
            "concept_variant_count": count,
            "selected_variant_id": None,
            "stages": [],
            "discipline_plan": {"engines":[]},
            "shared_model": "PHOENIX_DIGITAL_TWIN",
            "result_sha256": hashlib.sha256(str(count).encode()).hexdigest(),
        }


class FreshRunRealVariantBindingR2(unittest.TestCase):
    def bridge(self, root):
        obj=object.__new__(OfficialStartIntegratedProjectBridge)
        obj.repository=root
        obj.service=_FakeService()
        obj.output_root=root/"outputs/runtime/phase19_start_screen_bridge"
        return obj

    def fixture(self, root):
        batch="20261007T220000Z_cafebabe"
        folder=root/"inputs/runtime/official_start_v3_uploads"/batch
        folder.mkdir(parents=True)
        raw=b"fresh-run-real-variant-binding"
        (folder/"terrain.png").write_bytes(raw)
        (folder/"upload_manifest.json").write_text(json.dumps({
            "batch_id":batch,
            "file_count":1,
            "files":[{"name":"terrain.png","size_bytes":len(raw)}],
        }),encoding="utf-8")
        for rel in (
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ):
            p=root/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('{"status":"REFERENCE_ONLY"}\n',encoding="utf-8")
        return {
            "session_id":"PHX-FRESH-R2",
            "project_type":"BOUW",
            "project_mode":"autonomous",
            "brief":"Urban villa 300 m2, 2 verdiepingen, 3 slaapkamers, garage voor 2 wagens.",
            "location_reference":"Perceel 314, Heliosstraat / Plutostraat",
            "upload_batch":batch,
            "desired_outputs":["drawings","ifc","digital_twin"],
            "_phase19_r4_concept_package":{
                "source_run_id":"P19-AAAAAAAAAAAAAAAA",
                "variant_files":[
                    {"variant_id":"A","svg_path":"outputs/runtime/phase19_start_screen_bridge/P19-AAAAAAAAAAAAAAAA/five_variants/variants/variant_A.svg"}
                ],
            },
        }

    def test_fresh_plan_replaces_stale_package_with_current_run_real_spatial(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bridge=self.bridge(root)
            result=bridge.plan(self.fixture(root))
            pkg=result.payload["concept_package"]

            self.assertEqual(pkg["source_run_id"],result.run_id)
            self.assertEqual(pkg["variant_provider"],"PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1")
            self.assertEqual(len(pkg["variant_files"]),5)
            self.assertTrue(
                all(result.run_id in item["svg_path"] for item in pkg["variant_files"])
            )
            self.assertTrue(
                all("/real_spatial/" in item["svg_path"] for item in pkg["variant_files"])
            )
            self.assertTrue(
                (root/pkg["real_spatial_manifest_path"]).is_file()
            )

    def test_fresh_run_persisted_payload_has_no_foreign_variant_run_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bridge=self.bridge(root)
            result=bridge.plan(self.fixture(root))
            persisted=json.loads(result.path.read_text(encoding="utf-8"))
            text=json.dumps(persisted)
            self.assertNotIn("P19-AAAAAAAAAAAAAAAA",text)
            self.assertIn(result.run_id,text)
            self.assertEqual(
                persisted["concept_package"]["source_run_id"],result.run_id
            )

    def test_source_contains_fresh_run_binding_guard(self):
        root=Path(__file__).resolve().parents[2]
        src=(root/"phoenix/local_app/integrated_project_bridge.py").read_text(encoding="utf-8")
        self.assertIn("PHOENIX_4_6_19_PHASE19_FRESH_RUN_REAL_VARIANT_BINDING_R2",src)
        self.assertIn("PHASE19_CONCEPT_PACKAGE_RUN_ID_DENY",src)


if __name__ == "__main__":
    unittest.main()
