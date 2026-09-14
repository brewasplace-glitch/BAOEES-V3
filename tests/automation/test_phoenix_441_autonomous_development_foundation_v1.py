import json
import tempfile
import subprocess
import unittest
from pathlib import Path

from phoenix.autonomy import (
    AutonomyPolicy, RiskClassifier, RiskLevel, CycleMode, Task,
    CapabilityRegistry, BacklogGenerator, OpenSourceScout,
    EvidenceGate, AutoRepairFSM, RepairState, LearningStore, LearningEvent
)
from phoenix.autonomy.dashboard import render_dashboard
from phoenix.autonomy.cycle import normalize_status_paths
from phoenix.autonomy.worktree import SafeWorktreeManager

class TestAutonomyFoundation(unittest.TestCase):
    def setUp(self):
        self.policy=AutonomyPolicy()
        self.classifier=RiskClassifier(self.policy)

    def test_low_risk_is_narrow_and_locked(self):
        task=Task("T1","Update docs","AUTO","update",("docs/automation/x.md",))
        risk,evidence=self.classifier.classify(task)
        self.assertEqual(risk,RiskLevel.LOW)
        decision=self.classifier.decide(task,CycleMode.LOW_RISK_AUTO)
        self.assertFalse(decision.allowed)

    def test_source_code_is_not_low_risk(self):
        task=Task("T2","Change engine","AUTO","modify",("phoenix/core.py",))
        risk,_=self.classifier.classify(task)
        self.assertEqual(risk,RiskLevel.MEDIUM)

    def test_protected_path_is_high(self):
        task=Task(
            "T3","Change CAD bridge","AUTO","modify",
            ("phoenix/local_app/static/official_start_v3_0/phoenix_detv_cad_bridge.js",)
        )
        risk,_=self.classifier.classify(task)
        self.assertEqual(risk,RiskLevel.HIGH)

    def test_dry_run_never_allows_execution(self):
        task=Task("T4","Analyze","AUTO","analyze",())
        decision=self.classifier.decide(task,CycleMode.DRY_RUN)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.risk,RiskLevel.LOW)

    def test_registry_backlog(self):
        reg=CapabilityRegistry()
        tasks=BacklogGenerator().generate(reg)
        ids={t.capability_id for t in tasks}
        self.assertIn("AUTO-LOWRISK-002",ids)
        self.assertIn("AUTO-BIB-002",ids)

    def test_open_source_primary_and_fallback(self):
        scout=OpenSourceScout()
        orch=scout.select("orchestration")
        git=scout.select("git")
        self.assertEqual(orch["primary"]["id"],"langgraph")
        self.assertEqual(orch["fallback"]["id"],"prefect")
        self.assertEqual(git["primary"]["id"],"gitpython")
        self.assertEqual(git["fallback"]["id"],"dulwich")

    def test_evidence_gate_blocks_missing(self):
        gate=EvidenceGate().evaluate({"baseline":True})
        self.assertFalse(gate.passed)
        self.assertIn("tests",gate.missing)

    def test_repair_fsm_hard_stops_after_retries(self):
        fsm=AutoRepairFSM(max_attempts=2)
        fsm.transition(RepairState.DETECTED)
        fsm.transition(RepairState.DIAGNOSED)
        fsm.transition(RepairState.PATCH_PLANNED)
        fsm.transition(RepairState.PATCHED)
        fsm.transition(RepairState.TESTING)
        fsm.transition(RepairState.RETRY)
        fsm.transition(RepairState.DIAGNOSED)
        fsm.transition(RepairState.PATCH_PLANNED)
        fsm.transition(RepairState.PATCHED)
        fsm.transition(RepairState.TESTING)
        state=fsm.transition(RepairState.RETRY)
        self.assertEqual(state,RepairState.BLOCKED)


    def test_status_scope_normalization(self):
        lines=(
            "?? docs/automation/new.md",
            " M phoenix/autonomy/cycle.py",
            "R  old/name.py -> new/name.py",
        )
        self.assertEqual(
            normalize_status_paths(lines),
            ("docs/automation/new.md","phoenix/autonomy/cycle.py","new/name.py"),
        )


    def test_git_porcelain_first_leading_space_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            subprocess.run(["git","init",str(repo)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            subprocess.run(["git","-C",str(repo),"config","user.email","phoenix-test@example.invalid"],check=True)
            subprocess.run(["git","-C",str(repo),"config","user.name","Phoenix Test"],check=True)
            f=repo/"tracked.txt"
            f.write_text("one\n",encoding="utf-8")
            subprocess.run(["git","-C",str(repo),"add","tracked.txt"],check=True)
            subprocess.run(["git","-C",str(repo),"commit","-m","baseline"],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            f.write_text("two\n",encoding="utf-8")

            mgr=SafeWorktreeManager(repo,branch="master")
            raw=mgr.git("status","--porcelain=v1","--untracked-files=all")
            self.assertTrue(raw.startswith(" M tracked.txt"),repr(raw))
            snap=mgr.snapshot(fetch=False)
            self.assertEqual(snap.status[0]," M tracked.txt")
            self.assertEqual(normalize_status_paths(snap.status),("tracked.txt",))

    def test_learning_jsonl_and_dashboard(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            store=LearningStore(td/"learning.jsonl")
            event=LearningEvent.create("C1","test",{"pass":True})
            store.append(event)
            self.assertEqual(len(store.read_all()),1)
            render_dashboard(
                {"mode":"dry-run","task":{"title":"X"},"decision":{"risk":"LOW","allowed":False}},
                td/"dashboard.html"
            )
            self.assertTrue((td/"dashboard.html").exists())

if __name__=="__main__":
    unittest.main()
