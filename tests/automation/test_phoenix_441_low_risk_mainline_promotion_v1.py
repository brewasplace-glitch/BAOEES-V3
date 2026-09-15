import json, subprocess, tempfile, unittest
from pathlib import Path
from phoenix.autonomy import LowRiskMainlinePromotionPolicy, LowRiskMainlinePromoter

GOV="bib/PHOENIX_AUTO_SYNC/BIB_CURRENT_STATE.json"

def git(cwd,*args,check=True):
    cp=subprocess.run(
        ["git","-c","core.longpaths=true","-C",str(cwd),*args],
        text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE
    )
    if check and cp.returncode:
        raise RuntimeError(cp.stderr or cp.stdout)
    return cp.stdout.rstrip("\r\n")

class TestLowRiskMainlinePromotion(unittest.TestCase):
    def make_repo(self,td):
        repo=Path(td)/"repo"
        remote=Path(td)/"remote.git"
        subprocess.run(["git","init","--bare",str(remote)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        subprocess.run(["git","init",str(repo)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        git(repo,"config","user.name","Phoenix Test")
        git(repo,"config","user.email","phoenix@example.invalid")
        (repo/"README.md").write_text("base\n",encoding="utf-8")
        git(repo,"add","README.md")
        git(repo,"commit","-m","baseline")
        git(repo,"branch","-M","project-phoenix")
        git(repo,"remote","add","origin",str(remote))
        git(repo,"push","-u","origin","project-phoenix")
        return repo

    def policy(self,td):
        p=Path(td)/"policy.json"
        p.write_text(json.dumps({
            "enabled":True,
            "mode":"backup_gated_fast_forward_only",
            "main_branch":"project-phoenix",
            "candidate_branch_prefix":"auto/lowrisk-low-",
            "max_commits_ahead":1,
            "allowed_status_codes":["A","M"],
            "allowed_roots":["docs/automation/autonomous_generated/"],
            "allowed_extensions":[".md",".txt",".json"],
            "max_files":5,
            "max_file_bytes":65536,
            "max_total_bytes":262144,
            "require_backup_receipt":True,
            "require_bundle_verified":True,
            "require_snapshot_verified":True,
            "promotion_engine":"git_merge_ff_only",
            "delete_candidate_after_success":True,
            "allowed_governance_side_effect_paths":[GOV],
            "max_governance_files":1,
            "max_governance_file_bytes":1048576,
            "max_governance_total_bytes":1048576
        }),encoding="utf-8")
        return LowRiskMainlinePromotionPolicy.from_json(p)

    def backup(self,repo,td,head):
        snap=Path(td)/"snapshot"
        subprocess.run(["git","clone",str(repo),str(snap)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        bundle=Path(td)/"backup.bundle"
        git(repo,"bundle","create",str(bundle),"--all")
        git(repo,"bundle","verify",str(bundle))
        receipt=Path(td)/"receipt.json"
        receipt.write_text(json.dumps({
            "status":"PASS",
            "baseline":head,
            "bundle_verified":True,
            "snapshot_verified":True,
            "bundle_path":str(bundle),
            "snapshot_path":str(snap),
            "bundle_sha256":"test"
        }),encoding="utf-8")
        return receipt

    def candidate(self,repo,head,name="auto/lowrisk-low-test",with_governance=False):
        git(repo,"checkout","-b",name)
        p=repo/"docs/automation/autonomous_generated/probe.md"
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text("# Probe\n\nPASS\n",encoding="utf-8")
        git(repo,"add","docs/automation/autonomous_generated/probe.md")
        if with_governance:
            g=repo/GOV
            g.parent.mkdir(parents=True,exist_ok=True)
            g.write_text('{"state":"synced"}\n',encoding="utf-8")
            git(repo,"add",GOV)
        git(repo,"commit","-m","chore(autonomy): low-risk candidate LOW-TEST")
        cand=git(repo,"rev-parse","HEAD")
        git(repo,"checkout","project-phoenix")
        self.assertEqual(git(repo,"rev-parse","HEAD"),head)
        return name,cand

    def test_backup_gated_ff_promotion_passes(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch,cand=self.candidate(repo,head)
            r=LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,receipt)
            self.assertEqual(r["status"],"PASS")
            self.assertEqual(r["governance_side_effect_paths"],[])
            self.assertEqual(git(repo,"rev-parse","HEAD"),cand)
            self.assertEqual(git(repo,"rev-parse","origin/project-phoenix"),cand)

    def test_governance_side_effect_allowlist_passes(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch,cand=self.candidate(repo,head,with_governance=True)
            r=LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,receipt)
            self.assertEqual(r["status"],"PASS")
            self.assertEqual(r["governance_side_effect_paths"],[GOV])
            self.assertTrue(r["governance_side_effects_validated"])
            self.assertEqual(git(repo,"rev-parse","HEAD"),cand)


    def test_governance_utf8_output_with_0x9d_byte_passes(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch="auto/lowrisk-low-utf8"
            git(repo,"checkout","-b",branch)

            p=repo/"docs/automation/autonomous_generated/probe.md"
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("# UTF-8 probe\n\nPASS\n",encoding="utf-8")

            g=repo/GOV
            g.parent.mkdir(parents=True,exist_ok=True)
            # U+011D encodes as C4 9D, directly covering the Windows cp1252 failure.
            g.write_text(
                json.dumps({"state":"synced","unicode":"ĝ"},ensure_ascii=False)+"\n",
                encoding="utf-8",
            )

            git(
                repo,"add",
                "docs/automation/autonomous_generated/probe.md",
                GOV,
            )
            git(
                repo,"commit","-m",
                "chore(autonomy): low-risk candidate LOW-UTF8",
            )
            candidate=git(repo,"rev-parse","HEAD")
            git(repo,"checkout","project-phoenix")

            r=LowRiskMainlinePromoter(
                repo,self.policy(td),Path(td)/"runtime"
            ).promote(branch,head,receipt)

            self.assertEqual(r["status"],"PASS")
            self.assertEqual(r["governance_side_effect_paths"],[GOV])
            self.assertEqual(git(repo,"rev-parse","HEAD"),candidate)

    def test_unknown_bib_path_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch="auto/lowrisk-low-unknown-bib"
            git(repo,"checkout","-b",branch)
            p=repo/"docs/automation/autonomous_generated/probe.md"
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("PASS\n",encoding="utf-8")
            q=repo/"bib/PHOENIX_AUTO_SYNC/UNKNOWN.json"
            q.parent.mkdir(parents=True,exist_ok=True)
            q.write_text("{}\n",encoding="utf-8")
            git(repo,"add","docs/automation/autonomous_generated/probe.md","bib/PHOENIX_AUTO_SYNC/UNKNOWN.json")
            git(repo,"commit","-m","chore(autonomy): low-risk candidate LOW-BAD-BIB")
            git(repo,"checkout","project-phoenix")
            with self.assertRaises(RuntimeError):
                LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,receipt)

    def test_missing_backup_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            branch,_=self.candidate(repo,head)
            with self.assertRaises(RuntimeError):
                LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,Path(td)/"missing.json")

    def test_two_commits_ahead_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch,_=self.candidate(repo,head)
            git(repo,"checkout",branch)
            p=repo/"docs/automation/autonomous_generated/second.md"
            p.write_text("second\n",encoding="utf-8")
            git(repo,"add","docs/automation/autonomous_generated/second.md")
            git(repo,"commit","-m","chore(autonomy): low-risk candidate LOW-SECOND")
            git(repo,"checkout","project-phoenix")
            with self.assertRaises(RuntimeError):
                LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,receipt)

    def test_source_path_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch="auto/lowrisk-low-source"
            git(repo,"checkout","-b",branch)
            p=repo/"phoenix/x.py"
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text("x=1\n",encoding="utf-8")
            git(repo,"add","phoenix/x.py")
            git(repo,"commit","-m","chore(autonomy): low-risk candidate LOW-SOURCE")
            git(repo,"checkout","project-phoenix")
            with self.assertRaises(RuntimeError):
                LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,receipt)

    def test_delete_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            base=repo/"docs/automation/autonomous_generated/existing.md"
            base.parent.mkdir(parents=True,exist_ok=True)
            base.write_text("existing\n",encoding="utf-8")
            git(repo,"add","docs/automation/autonomous_generated/existing.md")
            git(repo,"commit","-m","add existing")
            git(repo,"push","origin","project-phoenix")
            head=git(repo,"rev-parse","HEAD")
            receipt=self.backup(repo,td,head)
            branch="auto/lowrisk-low-delete"
            git(repo,"checkout","-b",branch)
            base.unlink()
            git(repo,"add","-A")
            git(repo,"commit","-m","chore(autonomy): low-risk candidate LOW-DELETE")
            git(repo,"checkout","project-phoenix")
            with self.assertRaises(RuntimeError):
                LowRiskMainlinePromoter(repo,self.policy(td),Path(td)/"runtime").promote(branch,head,receipt)

if __name__=="__main__":
    unittest.main()
