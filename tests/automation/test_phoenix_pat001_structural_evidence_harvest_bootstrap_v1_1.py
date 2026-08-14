from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from phoenix.autonomy.pat001_structural_evidence_harvest_bootstrap_v1_1 import *

def base_contract():
    return {
        "schema_version":"phoenix.pat001-structural-input-contract/1.0",
        "project_id":PROJECT_ID,
        "project_identity":{"name":"REQUIRED","location":"REQUIRED","structural_scope":"REQUIRED"},
        "canonical_structural_model":{"path":"REQUIRED_PATH_TO_CANONICAL_MODEL_JSON"},
        "provenance":{
            "geometry":{"status":"REQUIRED","sources":[]},"materials":{"status":"REQUIRED","sources":[]},
            "sections":{"status":"REQUIRED","sources":[]},"supports_and_boundaries":{"status":"REQUIRED","sources":[]},
            "load_basis":{"status":"REQUIRED","sources":[]},"load_cases":{"status":"REQUIRED","sources":[]},
            "load_combinations":{"status":"REQUIRED","sources":[]}
        },
        "analysis_scope":{"status":"REQUIRED","calculation_type":None},
        "scia":{"seed_esa":None,"seed_provenance":None,"xml_update":None,"xml_definition":None},
        "calculix":{"project_adapter":None}
    }

def canonical():
    return {
        "schema_version":"phoenix.canonical-structural-model/1.0",
        "project_id":PROJECT_ID,
        "model_id":"PAT001-MODEL",
        "units":{"length":"m","force":"N","mass":"kg","temperature":"C"},
        "nodes":[{"id":"N1","x":0,"y":0,"z":0},{"id":"N2","x":1,"y":0,"z":0}],
        "materials":[{"id":"M1"}],"sections":[{"id":"S1"}],
        "members":[{"id":"B1","start_node":"N1","end_node":"N2","material":"M1","section":"S1"}],
        "supports":[{"id":"SUP1","node":"N1"}],"load_cases":[{"id":"LC1"}],
        "nodal_loads":[],"line_loads":[],
        "load_combinations":[{"id":"C1","terms":[{"load_case":"LC1","factor":1.0}]}],
        "metadata":{}
    }

class HarvestTests(unittest.TestCase):
    def test_01_project_id_detection(self):
        self.assertTrue(contains_project_id({"project_id":PROJECT_ID}))
        self.assertFalse(contains_project_id({"project_id":"OTHER"}))

    def test_02_identity_requires_explicit_project_id(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"configs/projects/x.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"name":"WRONG"}))
            self.assertIsNone(harvest_identity(json_candidates(root))["name"]["value"])

    def test_03_identity_autofill_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"configs/projects/x.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"project_id":PROJECT_ID,"project_name":"PAT 001","location":"SITE","structural_scope":"FRAME"}))
            r=harvest_identity(json_candidates(root))
            self.assertEqual("PAT 001",r["name"]["value"])
            self.assertEqual("SITE",r["location"]["value"])

    def test_04_identity_conflict_unresolved(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); d=root/"configs/projects"; d.mkdir(parents=True)
            (d/"a.json").write_text(json.dumps({"project_id":PROJECT_ID,"project_name":"A"}))
            (d/"b.json").write_text(json.dumps({"project_id":PROJECT_ID,"project_name":"B"}))
            r=harvest_identity(json_candidates(root))["name"]
            self.assertIsNone(r["value"]); self.assertEqual(2,len(r["conflicts"]))

    def test_05_valid_canonical_selected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/f"projects/runtime/{PROJECT_ID}/model.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps(canonical()))
            r=harvest_canonical(json_candidates(root))
            self.assertIsNotNone(r["selected"])

    def test_06_golden_reference_outside_search_roots_not_selected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"reference_models/structural/x.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps(canonical()))
            self.assertEqual([],harvest_canonical(json_candidates(root))["valid_candidates"])

    def test_07_provenance_traceable_from_pat001_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/f"projects/runtime/{PROJECT_ID}/model.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps(canonical()))
            r=harvest_provenance(json_candidates(root))
            self.assertEqual("TRACEABLE",r["geometry"]["status"])
            self.assertEqual("TRACEABLE",r["materials"]["status"])

    def test_08_analysis_scope_unique(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/f"projects/runtime/{PROJECT_ID}/scope.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"project_id":PROJECT_ID,"analysis_scope":{"calculation_type":"LIN"}}))
            r=harvest_analysis_scope(json_candidates(root))
            self.assertEqual("LIN",r["calculation_type"])

    def test_09_analysis_scope_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); d=root/f"projects/runtime/{PROJECT_ID}"; d.mkdir(parents=True)
            (d/"a.json").write_text(json.dumps({"project_id":PROJECT_ID,"calculation_type":"LIN"}))
            (d/"b.json").write_text(json.dumps({"project_id":PROJECT_ID,"calculation_type":"NEL"}))
            r=harvest_analysis_scope(json_candidates(root))
            self.assertIsNone(r["calculation_type"]); self.assertEqual(2,len(r["conflicts"]))

    def test_10_scia_seed_requires_matching_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); d=root/f"projects/runtime/{PROJECT_ID}"; d.mkdir(parents=True)
            seed=d/"x.esa"; seed.write_bytes(b"SEN")
            (d/"manifest.json").write_text(json.dumps({"project_id":PROJECT_ID,"seed_esa":"x.esa","sha256":"0"*64}))
            r=harvest_scia_seed(root,json_candidates(root))
            self.assertIsNone(r["selected"]); self.assertTrue(r["rejected_candidates"])

    def test_11_scia_seed_accepts_explicit_matching_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); d=root/f"projects/runtime/{PROJECT_ID}"; d.mkdir(parents=True)
            seed=d/"x.esa"; seed.write_bytes(b"SEN")
            h=hashlib.sha256(seed.read_bytes()).hexdigest()
            (d/"manifest.json").write_text(json.dumps({"project_id":PROJECT_ID,"seed_esa":"x.esa","sha256":h}))
            r=harvest_scia_seed(root,json_candidates(root))
            self.assertEqual(str(seed),r["selected"]["seed_esa"])

    def test_12_calculix_adapter_explicit_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/f"projects/runtime/{PROJECT_ID}/adapter.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"project_id":PROJECT_ID,"calculix_project_adapter":"PAT001-CCX-v1"}))
            self.assertEqual("PAT001-CCX-v1",harvest_calculix_adapter(json_candidates(root))["project_adapter"])

    def test_13_bootstrap_does_not_overwrite_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/"source.json"; source.write_text(json.dumps(base_contract()))
            before=sha256_file(source)
            bootstrap(root,source,root/"out.json",root/"audit.json")
            self.assertEqual(before,sha256_file(source))

    def test_14_bootstrap_populates_traceable_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/"source.json"; source.write_text(json.dumps(base_contract()))
            d=root/f"projects/runtime/{PROJECT_ID}"; d.mkdir(parents=True)
            (d/"model.json").write_text(json.dumps(canonical()))
            (d/"identity.json").write_text(json.dumps({"project_id":PROJECT_ID,"project_name":"PAT","location":"SITE","structural_scope":"FRAME","calculation_type":"LIN"}))
            audit=bootstrap(root,source,root/"out.json",root/"audit.json")
            out=read_json(root/"out.json")
            self.assertEqual("PAT",out["project_identity"]["name"])
            self.assertEqual("LIN",out["analysis_scope"]["calculation_type"])
            self.assertTrue(audit["applied_fields"])

    def test_15_no_field_invention(self):
        self.assertFalse(SAFETY["field_invented_without_source"])
        self.assertFalse(SAFETY["source_contract_overwritten"])

    def test_16_no_reference_model_as_pat001(self):
        self.assertFalse(SAFETY["reference_model_is_pat001_project_evidence"])
        self.assertFalse(SAFETY["historical_esa_auto_labeled_pat001"])

    def test_17_no_live_solvers(self):
        self.assertFalse(SAFETY["automatic_live_scia"]); self.assertFalse(SAFETY["automatic_live_calculix"])

    def test_18_release_locks(self):
        self.assertEqual("LOCKED",SAFETY["production_release"])
        self.assertEqual("LOCKED",SAFETY["for_construction_release"])
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])

if __name__=="__main__":
    unittest.main()
