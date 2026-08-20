from __future__ import annotations
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/"phoenix"/"knowledge"/"bib_auto_sync.py"
class T(unittest.TestCase):
    def repo(self):
        td=tempfile.TemporaryDirectory(); r=Path(td.name)
        subprocess.run(["git","init"],cwd=r,check=True,capture_output=True)
        subprocess.run(["git","config","user.email","phoenix-test@example.invalid"],cwd=r,check=True)
        subprocess.run(["git","config","user.name","Phoenix Test"],cwd=r,check=True)
        (r/"seed.txt").write_text("seed\n",encoding="utf-8"); subprocess.run(["git","add","seed.txt"],cwd=r,check=True); subprocess.run(["git","commit","-m","seed"],cwd=r,check=True,capture_output=True)
        subprocess.run(["git","config","core.hooksPath",".githooks"],cwd=r,check=True); return td,r
    def invoke_engine(self,r,*args):
        cp=subprocess.run([sys.executable,str(ENGINE),*args,"--repo",str(r)],cwd=r,text=True,capture_output=True)
        self.assertEqual(cp.returncode,0,cp.stdout+"\n"+cp.stderr); return cp
    def test_git_dotfiles_keep_exact_index_path(self):
        td,r=self.repo(); self.addCleanup(td.cleanup)
        (r/".pre-commit-config.yaml").write_text("repos: []\n",encoding="utf-8")
        (r/".github/workflows").mkdir(parents=True)
        (r/".github/workflows/ci.yml").write_text("name: ci\n",encoding="utf-8")
        subprocess.run(["git","add",".pre-commit-config.yaml",".github/workflows/ci.yml"],cwd=r,check=True)
        cp=self.invoke_engine(r,"sync","--mode","git-index")
        self.assertIn("BIB_UP_TO_DATE=YES",cp.stdout)
        manifest=json.loads((r/"bib/PHOENIX_AUTO_SYNC/BIB_MANIFEST.json").read_text(encoding="utf-8"))
        paths={item["path"] for item in manifest["files"]}
        self.assertIn(".pre-commit-config.yaml",paths)
        self.assertIn(".github/workflows/ci.yml",paths)
        self.assertNotIn("pre-commit-config.yaml",paths)
        self.assertNotIn("github/workflows/ci.yml",paths)

    def test_full_backfill_and_code_fingerprint(self):
        td,r=self.repo(); self.addCleanup(td.cleanup); (r/"docs").mkdir(); (r/"configs").mkdir(); (r/"phoenix").mkdir()
        (r/"docs/a.md").write_text("PROJECT PHOENIX knowledge\n",encoding="utf-8"); (r/"configs/p.json").write_text('{"knowledge":"beta"}\n',encoding="utf-8"); (r/"phoenix/x.py").write_text("VALUE=42\n",encoding="utf-8")
        subprocess.run(["git","add","."],cwd=r,check=True); cp=self.invoke_engine(r,"sync","--mode","git-index"); self.assertIn("BIB_UP_TO_DATE=YES",cp.stdout)
        m=json.loads((r/"bib/PHOENIX_AUTO_SYNC/BIB_MANIFEST.json").read_text(encoding="utf-8")); by={x["path"]:x for x in m["files"]}
        self.assertEqual(by["docs/a.md"]["classification"],"full-content"); self.assertGreater(by["docs/a.md"]["chunks"],0); self.assertEqual(by["phoenix/x.py"]["classification"],"source-metadata")
    def test_normalize_only_removes_literal_dot_slash_prefix(self):
        source=ENGINE.read_text(encoding="utf-8")
        self.assertNotIn('lstrip("./")',source)
        self.assertIn('while p.startswith("./"):',source)

    def test_git_index_ignores_unstaged(self):
        td,r=self.repo(); self.addCleanup(td.cleanup); (r/"docs").mkdir(); p=r/"docs/state.md"; p.write_text("STAGED KNOWLEDGE\n",encoding="utf-8"); subprocess.run(["git","add","docs/state.md"],cwd=r,check=True); p.write_text("UNSTAGED DIFFERENT\n",encoding="utf-8")
        self.invoke_engine(r,"sync","--mode","git-index"); f=(r/"bib/PHOENIX_AUTO_SYNC/BIB_KNOWLEDGE_FALLBACK.jsonl").read_text(encoding="utf-8"); self.assertIn("STAGED KNOWLEDGE",f); self.assertNotIn("UNSTAGED DIFFERENT",f)
    def test_runtime_excluded(self):
        td,r=self.repo(); self.addCleanup(td.cleanup); (r/"docs").mkdir(); (r/"projects/runtime/X").mkdir(parents=True); (r/"docs/g.md").write_text("good\n",encoding="utf-8"); (r/"projects/runtime/X/noise.json").write_text('{"noise":1}\n',encoding="utf-8")
        subprocess.run(["git","add","."],cwd=r,check=True); self.invoke_engine(r,"sync","--mode","git-index"); m=json.loads((r/"bib/PHOENIX_AUTO_SYNC/BIB_MANIFEST.json").read_text(encoding="utf-8")); paths={x["path"] for x in m["files"]}; self.assertIn("docs/g.md",paths); self.assertNotIn("projects/runtime/X/noise.json",paths)
    def test_tracked_test_source_contains_no_literal_aws_key_shape(self):
        source=Path(__file__).read_text(encoding="utf-8")
        import re
        self.assertIsNone(re.search(r"AKIA[0-9A-Z]{16}",source))

    def test_secret_redaction(self):
        td,r=self.repo(); self.addCleanup(td.cleanup); (r/"docs").mkdir(); secret="AK"+"IA"+"ABCDEFGHIJKLMNOP"; (r/"docs/s.md").write_text(secret+"\n",encoding="utf-8"); subprocess.run(["git","add","."],cwd=r,check=True); self.invoke_engine(r,"sync","--mode","git-index")
        f=(r/"bib/PHOENIX_AUTO_SYNC/BIB_KNOWLEDGE_FALLBACK.jsonl").read_text(encoding="utf-8"); self.assertNotIn(secret,f); self.assertIn("[REDACTED_AWS_ACCESS_KEY]",f)
    def test_precommit_runner_reconciles_managed_bib_worktree(self):
        runner=(ROOT/"runners"/"PROJECT_PHOENIX_bib_precommit_v1_0.ps1").read_text(encoding="utf-8")
        self.assertIn('git -C $Repo restore --worktree -- "bib/PHOENIX_AUTO_SYNC"',runner)
        self.assertIn("BIB_WORKTREE_RECONCILIATION=PASS",runner)
        self.assertIn('git -C $Repo diff --name-only -- "bib/PHOENIX_AUTO_SYNC"',runner)

    def test_staged_source_change_requires_resync_before_validation(self):
        td,r=self.repo(); self.addCleanup(td.cleanup)
        (r/"docs").mkdir()
        p=r/"docs/order.md"
        p.write_text("version one\n",encoding="utf-8")
        subprocess.run(["git","add","docs/order.md"],cwd=r,check=True)
        self.invoke_engine(r,"sync","--mode","git-index")
        subprocess.run(["git","add","bib/PHOENIX_AUTO_SYNC"],cwd=r,check=True)

        p.write_text("version two\n",encoding="utf-8")
        subprocess.run(["git","add","docs/order.md"],cwd=r,check=True)

        stale=subprocess.run(
            [sys.executable,str(ENGINE),"validate","--repo",str(r),"--mode","git-index"],
            cwd=r,text=True,capture_output=True
        )
        self.assertNotEqual(stale.returncode,0)
        self.assertIn("BIB source digest is stale",stale.stdout+stale.stderr)

        self.invoke_engine(r,"sync","--mode","git-index")
        subprocess.run(["git","add","bib/PHOENIX_AUTO_SYNC"],cwd=r,check=True)
        current=self.invoke_engine(r,"validate","--mode","git-index")
        self.assertIn("BIB_UP_TO_DATE=YES",current.stdout)

    def test_machine_managed_bib_root_contract(self):
        source=ROOT/"bib"/"PHOENIX_AUTO_SYNC"/"README.md"
        if not source.exists():
            source=ROOT/"BIB"/"PHOENIX_AUTO_SYNC"/"README.md"
        if source.exists():
            text=source.read_text(encoding="utf-8")
            self.assertIn("Machine-managed BIB",text)

    def test_managed_root_case_matches_git_tracked_path(self):
        engine_source=ENGINE.read_text(encoding="utf-8")
        runner_source=(ROOT/"runners"/"PROJECT_PHOENIX_bib_precommit_v1_0.ps1").read_text(encoding="utf-8")
        self.assertIn('MANAGED_REL="bib/PHOENIX_AUTO_SYNC"',engine_source)
        self.assertNotIn('MANAGED_REL="BIB/PHOENIX_AUTO_SYNC"',engine_source)
        self.assertIn('git -C $Repo restore --worktree -- "bib/PHOENIX_AUTO_SYNC"',runner_source)
        self.assertNotIn('git -C $Repo restore --worktree -- "BIB/PHOENIX_AUTO_SYNC"',runner_source)

    def test_sync_creates_canonical_lowercase_managed_root_entry(self):
        td,r=self.repo(); self.addCleanup(td.cleanup)
        (r/"docs").mkdir()
        (r/"docs/a.md").write_text("lowercase root contract\n",encoding="utf-8")
        subprocess.run(["git","add","docs/a.md"],cwd=r,check=True)
        self.invoke_engine(r,"sync","--mode","git-index")
        self.assertTrue((r/"bib/PHOENIX_AUTO_SYNC/BIB_MANIFEST.json").exists())
        matching=[p.name for p in r.iterdir() if p.name.lower()=="bib"]
        self.assertEqual(matching,["bib"])

    def test_validate_index_snapshot(self):
        td,r=self.repo(); self.addCleanup(td.cleanup); (r/"docs").mkdir(); (r/"docs/a.md").write_text("PROJECT PHOENIX BIB\n",encoding="utf-8"); subprocess.run(["git","add","."],cwd=r,check=True); self.invoke_engine(r,"sync","--mode","git-index"); subprocess.run(["git","add","bib/PHOENIX_AUTO_SYNC"],cwd=r,check=True)
        cp=self.invoke_engine(r,"validate","--mode","git-index"); self.assertIn("BIB_CURRENT_BASELINE=PASS",cp.stdout); self.assertIn("BIB_AUTO_SYNC=ENABLED",cp.stdout)
if __name__=="__main__": unittest.main(verbosity=2)
