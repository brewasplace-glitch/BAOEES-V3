import hashlib, json, tempfile, unittest
from pathlib import Path
from phoenix.release_framework import ReleaseManifestLoader, PhoenixReleaseFramework

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"configs/phoenix/releases/bb18_release_framework_v1_0.json"

class Tests(unittest.TestCase):
    def setUp(self):
        self.loader=ReleaseManifestLoader(); self.framework=PhoenixReleaseFramework()
        self.manifest=self.loader.load_file(MANIFEST)

    def test_policies(self):
        self.assertEqual({"track","ignore","clean"},{a.policy for a in self.manifest.artifacts})

    def test_unsafe_path(self):
        d=json.loads(MANIFEST.read_text()); d["artifacts"][0]["path"]="../bad"
        with self.assertRaises(ValueError): self.loader.load_dict(d)

    def test_duplicate_path(self):
        d=json.loads(MANIFEST.read_text()); d["artifacts"].append(dict(d["artifacts"][0]))
        with self.assertRaises(ValueError): self.loader.load_dict(d)

    def test_missing_required(self):
        with tempfile.TemporaryDirectory() as td: plan=self.framework.build_plan(td,self.manifest)
        self.assertFalse(plan["ready"])

    def test_ready_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for a in self.manifest.artifacts:
                if a.policy=="track":
                    p=root/a.path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("x")
            plan=self.framework.build_plan(root,self.manifest)
        self.assertTrue(plan["ready"])

    def test_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"a.txt").write_text("phoenix")
            sha=hashlib.sha256(b"phoenix").hexdigest()
            m=self.loader.load_dict({"id":"PHX-HASH-TEST","name":"Hash","version":"1",
              "branch":"project-phoenix","commit_message":"test",
              "artifacts":[{"path":"a.txt","policy":"track","sha256":sha}],"gates":[]})
            result=self.framework.verify_hashes(root,m)
        self.assertTrue(result[0]["matches"])

    def test_fingerprint(self):
        self.assertEqual(self.framework.fingerprint(self.manifest),self.framework.fingerprint(self.manifest))

    def test_journal(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.framework.rollback_journal(self.manifest,"abc",Path(td)/"j.json")
            d=json.loads(p.read_text())
        self.assertEqual("abc",d["base_commit"])

if __name__=="__main__": unittest.main()
