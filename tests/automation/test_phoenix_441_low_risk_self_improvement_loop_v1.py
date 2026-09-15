import json, subprocess, tempfile, unittest
from pathlib import Path

from phoenix.autonomy import (
    AutonomyPolicy,
    Capability,
    CapabilityRegistry,
    LearningStore,
    LowRiskExecutionPolicy,
    LowRiskMainlinePromotionPolicy,
    LowRiskSelfImprovementPolicy,
    LowRiskSelfImprovementLoop,
    OpenSourceScout,
)

def git(cwd,*args,check=True):
    cp=subprocess.run(
        ["git","-c","core.longpaths=true","-C",str(cwd),*args],
        text=True,encoding="utf-8",
        stdout=subprocess.PIPE,stderr=subprocess.PIPE
    )
    if check and cp.returncode:
        raise RuntimeError(cp.stderr or cp.stdout)
    return cp.stdout.rstrip("\r\n")

class TestSelfImprovementLoop(unittest.TestCase):
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

    def receipt(self,repo,td,head):
        snap=Path(td)/"snapshot"
        subprocess.run(["git","clone",str(repo),str(snap)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        bundle=Path(td)/"backup.bundle"
        git(repo,"bundle","create",str(bundle),"--all")
        git(repo,"bundle","verify",str(bundle))
        p=Path(td)/"receipt.json"
        p.write_text(json.dumps({
            "status":"PASS",
            "baseline":head,
            "bundle_verified":True,
            "snapshot_verified":True,
            "bundle_path":str(bundle),
            "snapshot_path":str(snap),
            "bundle_sha256":"test"
        }),encoding="utf-8")
        return p

    def policies(self,td):
        execution=Path(td)/"execution.json"
        execution.write_text(json.dumps({
            "enabled":True,
            "execution_mode":"candidate_branch_only",
            "mainline_promotion":"LOCKED",
            "allowed_roots":["docs/automation/autonomous_generated/","outputs/runtime/autonomy/"],
            "allowed_extensions":[".md",".txt",".json"],
            "max_files":5,
            "max_file_bytes":65536,
            "max_total_bytes":262144,
            "forbidden_path_segments":[".git","bib","phoenix","runners","configs","tests",".github"],
            "forbidden_content_patterns":["(?i)password\\\\s*[:=]","(?i)secret\\\\s*[:=]"]
        }),encoding="utf-8")

        promotion=Path(td)/"promotion.json"
        promotion.write_text(json.dumps({
            "enabled":True,
            "mode":"backup_gated_fast_forward_only",
            "main_branch":"project-phoenix",
            "candidate_branch_prefix":"auto/lowrisk-low-",
            "max_commits_ahead":1,
            "allowed_status_codes":["A","M"],
            "allowed_roots":["docs/automation/autonomous_generated/","outputs/runtime/autonomy/"],
            "allowed_extensions":[".md",".txt",".json"],
            "max_files":5,
            "max_file_bytes":65536,
            "max_total_bytes":262144,
            "require_backup_receipt":True,
            "require_bundle_verified":True,
            "require_snapshot_verified":True,
            "promotion_engine":"git_merge_ff_only",
            "delete_candidate_after_success":True,
            "allowed_governance_side_effect_paths":[],
            "max_governance_files":0,
            "max_governance_file_bytes":0,
            "max_governance_total_bytes":0
        }),encoding="utf-8")

        selfp=Path(td)/"self.json"
        selfp.write_text(json.dumps({
            "enabled":True,
            "mode":"bounded_single_cycle",
            "max_cycles_per_invocation":1,
            "max_candidates_per_cycle":1,
            "stop_on_first_failure":True,
            "require_clean_synced_baseline":True,
            "require_verified_backup_before_promotion":True,
            "require_open_source_review":True,
            "require_low_risk_classification":True,
            "target_root":"docs/automation/autonomous_generated/self_improvement/",
            "target_extension":".md",
            "mainline_promotion":"ENABLED_FF_ONLY_BACKUP_GATED",
            "source_self_modification":"BLOCKED",
            "medium_high_critical":"BLOCKED"
        }),encoding="utf-8")

        return (
            LowRiskExecutionPolicy.from_json(execution),
            LowRiskMainlinePromotionPolicy.from_json(promotion),
            LowRiskSelfImprovementPolicy.from_json(selfp),
        )

    def scout(self):
        return OpenSourceScout({
            "schema":"TEST",
            "candidates":[
                {"id":"prefect","capability":"orchestration","role":"primary","name":"Prefect","license":"Apache-2.0"},
                {"id":"langgraph","capability":"orchestration","role":"fallback","name":"LangGraph","license":"MIT"},
            ]
        })

    def test_end_to_end_bounded_low_risk_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.receipt(repo,td,head)
            execution,promotion,selfp=self.policies(td)
            registry=CapabilityRegistry([
                Capability("AUTO-GAP-TEST","Test Capability Gap","planning","planned",100)
            ])
            loop=LowRiskSelfImprovementLoop(
                repo,
                AutonomyPolicy(low_risk_auto_enabled=True),
                execution,
                promotion,
                selfp,
                self.scout(),
                LearningStore(Path(td)/"learning.jsonl"),
                registry=registry,
                runtime_root=Path(td)/"runtime",
            )
            r=loop.run_once(head,receipt)
            self.assertEqual(r["status"],"PASS")
            self.assertEqual(r["risk"],"LOW")
            self.assertEqual(r["repository_end_state"],"CLEAN_SYNCED")
            self.assertEqual(git(repo,"rev-parse","HEAD"),r["baseline_after"])
            self.assertEqual(git(repo,"rev-parse","origin/project-phoenix"),r["baseline_after"])
            self.assertTrue((repo/r["target_path"]).is_file())
            self.assertEqual(git(repo,"branch","--list","auto/lowrisk-*"),"")

    def test_missing_backup_blocks_before_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            execution,promotion,selfp=self.policies(td)
            loop=LowRiskSelfImprovementLoop(
                repo,
                AutonomyPolicy(low_risk_auto_enabled=True),
                execution,promotion,selfp,self.scout(),
                LearningStore(Path(td)/"learning.jsonl"),
                registry=CapabilityRegistry([
                    Capability("AUTO-GAP-TEST","Gap","planning","planned",100)
                ]),
                runtime_root=Path(td)/"runtime",
            )
            with self.assertRaises(RuntimeError):
                loop.run_once(head,Path(td)/"missing.json")
            self.assertEqual(git(repo,"rev-parse","HEAD"),head)
            self.assertEqual(git(repo,"branch","--list","auto/lowrisk-*"),"")

    def test_source_self_modification_policy_must_be_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.receipt(repo,td,head)
            execution,promotion,selfp=self.policies(td)
            bad=LowRiskSelfImprovementPolicy(
                selfp.enabled,selfp.mode,selfp.max_cycles_per_invocation,
                selfp.max_candidates_per_cycle,selfp.stop_on_first_failure,
                selfp.require_clean_synced_baseline,
                selfp.require_verified_backup_before_promotion,
                selfp.require_open_source_review,
                selfp.require_low_risk_classification,
                selfp.target_root,selfp.target_extension,
                selfp.mainline_promotion,"ENABLED",selfp.medium_high_critical
            )
            loop=LowRiskSelfImprovementLoop(
                repo,AutonomyPolicy(low_risk_auto_enabled=True),
                execution,promotion,bad,self.scout(),
                LearningStore(Path(td)/"learning.jsonl"),
                runtime_root=Path(td)/"runtime",
            )
            with self.assertRaises(RuntimeError):
                loop.run_once(head,receipt)

    def test_open_source_primary_and_fallback_required(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.make_repo(td)
            head=git(repo,"rev-parse","HEAD")
            receipt=self.receipt(repo,td,head)
            execution,promotion,selfp=self.policies(td)
            scout=OpenSourceScout({
                "schema":"TEST",
                "candidates":[
                    {"id":"prefect","capability":"orchestration","role":"primary","name":"Prefect"}
                ]
            })
            loop=LowRiskSelfImprovementLoop(
                repo,AutonomyPolicy(low_risk_auto_enabled=True),
                execution,promotion,selfp,scout,
                LearningStore(Path(td)/"learning.jsonl"),
                runtime_root=Path(td)/"runtime",
            )
            with self.assertRaises(RuntimeError):
                loop.run_once(head,receipt)

    def test_medium_high_critical_gate_must_remain_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            execution,promotion,selfp=self.policies(td)
            bad=LowRiskSelfImprovementPolicy(
                selfp.enabled,selfp.mode,selfp.max_cycles_per_invocation,
                selfp.max_candidates_per_cycle,selfp.stop_on_first_failure,
                selfp.require_clean_synced_baseline,
                selfp.require_verified_backup_before_promotion,
                selfp.require_open_source_review,
                selfp.require_low_risk_classification,
                selfp.target_root,selfp.target_extension,
                selfp.mainline_promotion,selfp.source_self_modification,"ENABLED"
            )
            self.assertEqual(bad.medium_high_critical,"ENABLED")

    def test_prefect_primary_langgraph_fallback_selection(self):
        review=self.scout().select("orchestration")
        self.assertEqual(review["primary"]["name"],"Prefect")
        self.assertEqual(review["fallback"]["name"],"LangGraph")

if __name__=="__main__":
    unittest.main()
