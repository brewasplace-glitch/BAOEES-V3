from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from phoenix.design.tropical_residential.canonical_output_manifest import (
    HANDOFF_SCHEMA, SCHEMA, build_structural_handoff_contract, write_canonical_output_manifest
)

class R8CanonicalOutputManifestTests(unittest.TestCase):
    def _fixture(self, root: Path):
        layout_paths={}; ifc_evidence={}
        for vid in "ABCDE":
            vdir=root/"variants"/f"variant_{vid}"; vdir.mkdir(parents=True,exist_ok=True)
            layout=vdir/"real_spatial_layout.json"; layout.write_text(json.dumps({"variant_id":vid}),encoding="utf-8")
            svg1=vdir/"storey_1_plan.svg"; svg2=vdir/"storey_2_plan.svg"
            svg1.write_text("<svg/>",encoding="utf-8"); svg2.write_text("<svg/>",encoding="utf-8")
            ifc=vdir/f"variant_{vid}.ifc"; ifc.write_bytes(f"IFC-{vid}".encode())
            layout_paths[vid]={"layout_json":str(layout),"svg_plans":[str(svg1),str(svg2)]}
            ifc_evidence[vid]={"ifc_file":str(ifc),"ifc_schema":"IFC4","release_status":"CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"}
        auth=root/"authoritative"/"P_authoritative_recommended_E.ifc"; auth.parent.mkdir(parents=True,exist_ok=True); auth.write_bytes(b"IFC-E")
        return layout_paths,ifc_evidence,auth

    def test_manifest_unifies_exact_ae_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); layouts,ifcs,auth=self._fixture(root)
            result=write_canonical_output_manifest(project={"project_id":"P"},output_dir=root,recommended_variant_id="E",
                layout_paths=layouts,ifc_evidence=ifcs,authoritative_ifc=auth,tools={},
                freecad_result={"status":"NOT_REQUESTED","executed":False},blender_result={"status":"NOT_REQUESTED","executed":False})
            m=result["manifest"]
            self.assertEqual(m["schema"],SCHEMA)
            self.assertEqual([x["variant_id"] for x in m["variants"]],list("ABCDE"))
            self.assertEqual(m["recommended_variant_id"],"E")
            self.assertEqual(m["release_status"],"CONCEPT_ONLY_NOT_FOR_CONSTRUCTION")
            self.assertTrue(Path(result["manifest_path"]).is_file())

    def test_structural_handoff_binds_existing_chain_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); layout=root/"layout.json"; layout.write_text("{}",encoding="utf-8")
            ifc=root/"a.ifc"; ifc.write_bytes(b"IFC")
            h=build_structural_handoff_contract(project_id="P",recommended_variant_id="E",
                canonical_layout_json=layout,authoritative_ifc=ifc)
            self.assertEqual(h["schema"],HANDOFF_SCHEMA)
            self.assertEqual(h["existing_consumer"]["function"],"run_structural")
            self.assertEqual(h["required_architecture_adapter_outputs"],
                ["architectural_model.json","detailed_elements.json","structural_project_profile.json"])
            self.assertEqual(h["handoff_status"],"CONTRACT_BOUND_INPUTS_REQUIRED")
            self.assertFalse(h["solver_execution_started"])
            self.assertEqual(h["production_release"],"LOCKED")

    def test_manifest_hashes_are_real_file_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); layouts,ifcs,auth=self._fixture(root)
            result=write_canonical_output_manifest(project={"project_id":"P"},output_dir=root,recommended_variant_id="E",
                layout_paths=layouts,ifc_evidence=ifcs,authoritative_ifc=auth,tools={},freecad_result={},blender_result={})
            row=result["manifest"]["variants"][0]
            self.assertEqual(len(row["layout_json"]["sha256"]),64)
            self.assertGreater(row["layout_json"]["bytes"],0)
            self.assertEqual(len(row["ifc"]["sha256"]),64)

if __name__=="__main__":
    unittest.main()
