from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from phoenix.autonomy.pat001_structural_preparation_v1_0 import (
    PROJECT_ID, INPUT_CONTRACT_REQUIRED, CANONICAL_REQUIRED, CANONICAL_INVALID,
    PROVENANCE_REQUIRED, ANALYSIS_SCOPE_REQUIRED, SCIA_MODEL_REQUIRED,
    CALCULIX_ADAPTER_REQUIRED, PREPARATION_READY, SAFETY,
    assess, inventory_candidates
)

def canonical():
    return {
        "schema_version":"phoenix.canonical-structural-model/1.0",
        "model_id":"PAT001-TEST-MODEL",
        "units":{"length":"m","force":"N","mass":"kg","temperature":"C"},
        "nodes":[{"id":"N1","x":0,"y":0,"z":0},{"id":"N2","x":1,"y":0,"z":0}],
        "materials":[{"id":"M1"}],
        "sections":[{"id":"S1"}],
        "members":[{"id":"B1","start_node":"N1","end_node":"N2","material":"M1","section":"S1"}],
        "supports":[{"id":"SUP1","node":"N1"}],
        "load_cases":[{"id":"LC1"}],
        "nodal_loads":[],
        "line_loads":[],
        "load_combinations":[{"id":"C1","terms":[{"load_case":"LC1","factor":1.0}]}],
        "metadata":{}
    }

def source():
    return {"status":"CONFIRMED","sources":[{"reference":"TEST-EVIDENCE"}]}

def contract(model_path="model.json"):
    return {
        "schema_version":"phoenix.pat001-structural-input-contract/1.0",
        "project_id":PROJECT_ID,
        "project_identity":{"name":"PAT 001","location":"TEST","structural_scope":"TEST SCOPE"},
        "canonical_structural_model":{"path":model_path},
        "provenance":{
            "geometry":source(),"materials":source(),"sections":source(),
            "supports_and_boundaries":source(),"load_basis":source(),
            "load_cases":source(),"load_combinations":source()
        },
        "analysis_scope":{"status":"CONFIRMED","calculation_type":"LIN"},
        "scia":{"seed_esa":None,"seed_provenance":None,"xml_update":None,"xml_definition":None},
        "calculix":{"project_adapter":None}
    }

class Pat001PreparationTests(unittest.TestCase):
    def test_01_missing_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            r=assess(root/"missing.json",root,root/"out")
            self.assertEqual(INPUT_CONTRACT_REQUIRED,r["status"])

    def test_02_missing_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            c=contract("missing.json")
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(CANONICAL_REQUIRED,r["status"])

    def test_03_invalid_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"model.json").write_text(json.dumps({"bad":True}))
            cp=root/"c.json"; cp.write_text(json.dumps(contract()))
            r=assess(cp,root,root/"out")
            self.assertEqual(CANONICAL_INVALID,r["status"])

    def test_04_missing_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"model.json").write_text(json.dumps(canonical()))
            c=contract(); c["provenance"]["geometry"]={"status":"REQUIRED","sources":[]}
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(PROVENANCE_REQUIRED,r["status"])

    def test_05_missing_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"model.json").write_text(json.dumps(canonical()))
            c=contract(); c["analysis_scope"]={"status":"REQUIRED","calculation_type":None}
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(ANALYSIS_SCOPE_REQUIRED,r["status"])

    def test_06_unqualified_scia_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"model.json").write_text(json.dumps(canonical()))
            seed=root/"old.esa"; seed.write_bytes(b"SEN-old")
            c=contract(); c["scia"]["seed_esa"]="old.esa"
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(SCIA_MODEL_REQUIRED,r["status"])
            self.assertFalse(r["scia_seed_qualification"]["qualified"])

    def test_07_wrong_project_seed_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            import hashlib
            root=Path(td); (root/"model.json").write_text(json.dumps(canonical()))
            seed=root/"x.esa"; seed.write_bytes(b"SEN")
            h=hashlib.sha256(seed.read_bytes()).hexdigest()
            c=contract(); c["scia"].update({"seed_esa":"x.esa","seed_provenance":{"project_id":"OTHER","sha256":h},"xml_update":"u.xml","xml_definition":"u.def"})
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(SCIA_MODEL_REQUIRED,r["status"])

    def test_08_valid_seed_but_no_adapter_stops_at_calculix(self):
        with tempfile.TemporaryDirectory() as td:
            import hashlib
            root=Path(td); (root/"model.json").write_text(json.dumps(canonical()))
            seed=root/"x.esa"; seed.write_bytes(b"SEN")
            h=hashlib.sha256(seed.read_bytes()).hexdigest()
            c=contract(); c["scia"].update({"seed_esa":"x.esa","seed_provenance":{"project_id":PROJECT_ID,"sha256":h},"xml_update":"u.xml","xml_definition":"u.def"})
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(CALCULIX_ADAPTER_REQUIRED,r["status"])

    def test_09_full_preparation_ready_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            import hashlib
            root=Path(td); (root/"model.json").write_text(json.dumps(canonical()))
            seed=root/"x.esa"; seed.write_bytes(b"SEN")
            h=hashlib.sha256(seed.read_bytes()).hexdigest()
            c=contract(); c["scia"].update({"seed_esa":"x.esa","seed_provenance":{"project_id":PROJECT_ID,"sha256":h},"xml_update":"u.xml","xml_definition":"u.def"})
            c["calculix"]["project_adapter"]="PAT001-ADAPTER-v1"
            cp=root/"c.json"; cp.write_text(json.dumps(c))
            r=assess(cp,root,root/"out")
            self.assertEqual(PREPARATION_READY,r["status"])
            self.assertFalse(r["live_scia_started"])
            self.assertFalse(r["live_calculix_started"])

    def test_10_reference_esa_inventory_not_project_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"reference_models/structural/ref.esa"; p.parent.mkdir(parents=True); p.write_bytes(b"SEN")
            inv=inventory_candidates(root)
            self.assertEqual("REFERENCE_MODEL_NOT_PAT001_EVIDENCE",inv[0]["role"])

    def test_11_runtime_candidate_unqualified(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"projects/runtime/PHOENIX-PAT-001/a.esa"; p.parent.mkdir(parents=True); p.write_bytes(b"SEN")
            inv=inventory_candidates(root)
            self.assertEqual("UNQUALIFIED_CANDIDATE",inv[0]["role"])

    def test_12_candidate_has_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"projects/runtime/PHOENIX-PAT-001/a.inp"; p.parent.mkdir(parents=True); p.write_text("*HEADING\n")
            self.assertEqual(64,len(inventory_candidates(root)[0]["sha256"]))

    def test_13_no_golden_reference_as_pat001_evidence(self):
        self.assertFalse(SAFETY["reference_model_is_pat001_project_evidence"])

    def test_14_no_binary_esa_synthesis(self):
        self.assertFalse(SAFETY["automatic_binary_esa_synthesis"])

    def test_15_no_live_solvers(self):
        self.assertFalse(SAFETY["automatic_live_scia"])
        self.assertFalse(SAFETY["automatic_live_calculix"])

    def test_16_no_auto_approval_or_compliance(self):
        self.assertFalse(SAFETY["automatic_professional_approval"])
        self.assertFalse(SAFETY["automatic_code_compliance_claim"])

    def test_17_release_locks(self):
        self.assertEqual("LOCKED",SAFETY["production_release"])
        self.assertEqual("LOCKED",SAFETY["for_construction_release"])

if __name__=="__main__":
    unittest.main()
