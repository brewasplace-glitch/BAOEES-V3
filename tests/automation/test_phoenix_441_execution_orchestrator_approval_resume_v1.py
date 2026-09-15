import json, tempfile, unittest
from pathlib import Path
from phoenix.autonomy import AutonomousExecutionOrchestrator, AutonomousExecutionPlanner, GoalSpec

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/"configs/phoenix"

def goal(goal_type="generic.analysis",**kwargs):
    d={"schema":"PHOENIX_GOAL_SPEC_V1","goal_id":"P4TEST","objective":"Test durable governed execution.",
       "goal_type":goal_type,"domain":"planning","success_criteria":["safe completion"],
       "constraints":[],"available_gates":[],"context":{},"subgoals":[]}
    d.update(kwargs)
    return GoalSpec.from_dict(d)

def medium_template():
    tr=json.loads((CFG/"goal_template_registry_v1.json").read_text(encoding="utf-8"))
    tr["templates"]["test.medium.read"]={"description":"approval test","steps":[{
        "key":"decision","title":"Human decision required","action":"unknown.medium.read",
        "risk":"MEDIUM","mutating":False,"domain":"planning",
        "engine_id":"autonomy.execution_planner","depends_on":[],"gates":[]
    }]}
    return tr

class Phase4Tests(unittest.TestCase):
    def test_policy_active_fail_closed(self):
        p=json.loads((CFG/"execution_orchestrator_policy_v1.json").read_text(encoding="utf-8"))
        self.assertTrue(p["fail_closed"])
        self.assertFalse(p["automatic_replay_of_in_progress_mutation"])

    def test_runtime_engines_gateway_required(self):
        r=json.loads((CFG/"engine_registry_v1.json").read_text(encoding="utf-8"))
        for eid in ("autonomy.execution_orchestrator","autonomy.approval_resume"):
            e=[x for x in r["engines"] if x["engine_id"]==eid][0]
            self.assertTrue(e["mutation_capable"]); self.assertTrue(e["gateway_required"])

    def test_phase4_policy_rules_exist(self):
        p=json.loads((CFG/"autonomy_policy_v2.json").read_text(encoding="utf-8"))
        ids={x["id"] for x in p["rules"]}
        self.assertTrue({"P4-ALLOW-ORCHESTRATION-CHECKPOINT","P4-ALLOW-APPROVAL-REQUEST","P4-ALLOW-APPROVAL-RECEIPT"} <= ids)

    def test_generic_read_only_completes(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT).plan(goal())
            s=AutonomousExecutionOrchestrator(ROOT,Path(td)).run(p)
            self.assertEqual(s["status"],"COMPLETE")
            self.assertTrue(all(x["status"]=="COMPLETE" for x in s["step_states"].values()))

    def test_restart_does_not_replay(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT).plan(goal())
            o=AutonomousExecutionOrchestrator(ROOT,Path(td))
            a=o.run(p); attempts={k:v["attempts"] for k,v in a["step_states"].items()}
            b=o.run(p)
            self.assertEqual(b["status"],"COMPLETE")
            self.assertEqual(attempts,{k:v["attempts"] for k,v in b["step_states"].items()})

    def test_escalation_pauses(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT,template_registry=medium_template()).plan(goal("test.medium.read"))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); s=o.run(p)
            self.assertEqual(s["status"],"PAUSED_APPROVAL")
            self.assertTrue(o.approvals.request_path(p.plan_id,p.steps[0].step_id).is_file())

    def test_approve_read_only_resumes(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT,template_registry=medium_template()).plan(goal("test.medium.read"))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); o.run(p)
            sid=p.steps[0].step_id
            o.approvals.record_decision(plan_id=p.plan_id,step_id=sid,decision="APPROVE",reason="test")
            s=o.run(p)
            self.assertEqual(s["status"],"COMPLETE")
            self.assertEqual(s["step_states"][sid]["status"],"COMPLETE_HUMAN_APPROVED")

    def test_reject_terminates(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT,template_registry=medium_template()).plan(goal("test.medium.read"))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); o.run(p)
            sid=p.steps[0].step_id
            o.approvals.record_decision(plan_id=p.plan_id,step_id=sid,decision="REJECT")
            self.assertEqual(o.run(p)["status"],"REJECTED")

    def test_defer_stays_paused(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT,template_registry=medium_template()).plan(goal("test.medium.read"))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); o.run(p)
            sid=p.steps[0].step_id
            o.approvals.record_decision(plan_id=p.plan_id,step_id=sid,decision="DEFER")
            self.assertEqual(o.run(p)["status"],"PAUSED_APPROVAL")

    def test_mutating_approval_does_not_bypass_gateway(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT).plan(goal("phoenix.feature_build",domain="software",
                context={"source_paths":["phoenix/new.py"]}))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); s=o.run(p)
            self.assertEqual(s["status"],"PAUSED_APPROVAL")
            sid=s["pause"]["step_id"]
            o.approvals.record_decision(plan_id=p.plan_id,step_id=sid,decision="APPROVE")
            s2=o.run(p)
            self.assertEqual(s2["status"],"WAITING_APPROVED_MUTATION")
            self.assertEqual(s2["pause"]["action"],"source.modify")

    def test_deny_never_requests_approval(self):
        with tempfile.TemporaryDirectory() as td:
            tr=json.loads((CFG/"goal_template_registry_v1.json").read_text(encoding="utf-8"))
            tr["templates"]["test.deny"]={"description":"deny","steps":[{
                "key":"x","title":"denied","action":"git.force_push","risk":"CRITICAL",
                "mutating":True,"domain":"git","engine_id":"autonomy.mainline_promoter",
                "depends_on":[],"gates":[]
            }]}
            p=AutonomousExecutionPlanner(ROOT,template_registry=tr).plan(goal("test.deny"))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); s=o.run(p)
            self.assertEqual(s["status"],"BLOCKED")
            self.assertFalse(o.approvals.request_path(p.plan_id,p.steps[0].step_id).exists())

    def test_approval_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT,template_registry=medium_template()).plan(goal("test.medium.read"))
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); o.run(p)
            sid=p.steps[0].step_id
            o.approvals.record_decision(plan_id=p.plan_id,step_id=sid,decision="APPROVE")
            path=o.approvals.receipt_path(p.plan_id,sid)
            d=json.loads(path.read_text(encoding="utf-8")); d["decision"]="REJECT"
            path.write_text(json.dumps(d),encoding="utf-8")
            with self.assertRaises(PermissionError): o.run(p)

    def test_state_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT).plan(goal())
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); o.run(p)
            path=o.store.state_path(p.plan_id)
            d=json.loads(path.read_text(encoding="utf-8")); d["status"]="BLOCKED"
            path.write_text(json.dumps(d),encoding="utf-8")
            with self.assertRaises(PermissionError): o.run(p)

    def test_in_progress_mutation_requires_reconciliation(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT).plan(goal())
            o=AutonomousExecutionOrchestrator(ROOT,Path(td)); o.run(p)
            s=o.store.load_state(p.plan_id); sid=p.steps[0].step_id
            s["step_states"][sid]["status"]="IN_PROGRESS_MUTATION"; s["status"]="RUNNING"
            o.store.write_state(s)
            self.assertEqual(o.run(p)["status"],"RECOVERY_REQUIRED")

    def test_stale_plan_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=AutonomousExecutionPlanner(ROOT).plan(goal())
            object.__setattr__(p,"policy_bundle_sha256","0"*64)
            with self.assertRaises(RuntimeError):
                AutonomousExecutionOrchestrator(ROOT,Path(td)).run(p)

    def test_low_risk_template_has_promotion(self):
        tr=json.loads((CFG/"goal_template_registry_v1.json").read_text(encoding="utf-8"))
        self.assertIn("promote",[x["key"] for x in tr["templates"]["phoenix.low_risk_documentation"]["steps"]])

    def test_schemas(self):
        for n in ("approval_receipt_v1.schema.json","orchestration_state_v1.schema.json"):
            d=json.loads((CFG/n).read_text(encoding="utf-8"))
            self.assertEqual(d["$schema"],"https://json-schema.org/draft/2020-12/schema")

    def test_open_source_review(self):
        d=json.loads((CFG/"open_source_execution_orchestrator_review_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(d["primary"]["name"],"Temporal")
        self.assertEqual(d["primary"]["license"],"MIT")
        self.assertEqual(d["fallback"]["name"],"Prefect")
        self.assertEqual(d["fallback"]["license"],"Apache-2.0")

    def test_no_external_dependency_required(self):
        d=json.loads((CFG/"execution_orchestrator_policy_v1.json").read_text(encoding="utf-8"))
        self.assertFalse(d["external_runtime_dependency_required"])

if __name__=="__main__":
    unittest.main()
