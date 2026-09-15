import json, tempfile, unittest
from pathlib import Path

from phoenix.autonomy import (
    ActionRequest,
    AutonomousExecutionPlanner,
    ExecutionCoordinator,
    GoalSpec,
)

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/"configs/phoenix"

def goal(goal_type="generic.analysis",**kwargs):
    data={
        "schema":"PHOENIX_GOAL_SPEC_V1",
        "goal_id":"G1",
        "objective":"Produce a safe machine-readable execution plan.",
        "goal_type":goal_type,
        "domain":"planning",
        "success_criteria":["plan is valid"],
        "constraints":[],
        "available_gates":[],
        "context":{},
        "subgoals":[],
    }
    data.update(kwargs)
    return GoalSpec.from_dict(data)

class TestExecutionPlanner(unittest.TestCase):
    def test_policy_active_and_fail_closed(self):
        p=json.loads((CFG/"execution_planner_policy_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(p["status"],"ACTIVE")
        self.assertTrue(p["fail_closed"])
        self.assertTrue(p["central_policy_evaluation_required_for_every_step"])
        self.assertTrue(p["universal_gateway_required_at_every_mutation_boundary"])

    def test_goal_schema_and_plan_schema_are_draft_2020_12(self):
        for n in ("goal_spec_v1.schema.json","execution_plan_v1.schema.json"):
            d=json.loads((CFG/n).read_text(encoding="utf-8"))
            self.assertEqual(d["$schema"],"https://json-schema.org/draft/2020-12/schema")

    def test_generic_goal_produces_ready_read_only_plan(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal())
        self.assertEqual(p.status,"READY")
        self.assertTrue(p.steps)
        self.assertTrue(all(not s.mutating for s in p.steps))
        self.assertTrue(all(s.policy_effect=="ALLOW" for s in p.steps))

    def test_unknown_goal_type_falls_back_safely(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal("never.seen.type"))
        self.assertEqual(p.status,"READY")
        self.assertEqual([s.key for s in p.steps],["observe","analyze","validate"])

    def test_feature_build_source_change_escalates(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal(
            "phoenix.feature_build",
            context={"source_paths":["phoenix/autonomy/new.py"]},
        ))
        source=[s for s in p.steps if s.action=="source.modify"][0]
        self.assertEqual(source.policy_effect,"ESCALATE")
        self.assertEqual(source.step_status,"ESCALATE")
        self.assertEqual(p.status,"HUMAN_DECISION_REQUIRED")

    def test_high_risk_custom_template_denies(self):
        tr=json.loads((CFG/"goal_template_registry_v1.json").read_text(encoding="utf-8"))
        tr["templates"]["test.high"]={
            "description":"test",
            "steps":[{
                "key":"x","title":"x","action":"unknown.high","risk":"HIGH",
                "mutating":True,"domain":"software","engine_id":"future.x",
                "depends_on":[],"gates":[]
            }]
        }
        p=AutonomousExecutionPlanner(ROOT,template_registry=tr).plan(goal("test.high"))
        self.assertEqual(p.status,"BLOCKED")
        self.assertEqual(p.steps[0].policy_effect,"DENY")

    def test_authorized_mutation_unknown_engine_is_denied(self):
        tr=json.loads((CFG/"goal_template_registry_v1.json").read_text(encoding="utf-8"))
        tr["templates"]["test.unknown.engine"]={
            "description":"test",
            "steps":[{
                "key":"x","title":"x","action":"documentation.update","risk":"LOW",
                "mutating":True,"domain":"documentation","engine_id":"future.unknown",
                "depends_on":[],
                "gates":["clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"],
                "default_paths":["docs/automation/autonomous_generated/x.md"]
            }]
        }
        p=AutonomousExecutionPlanner(ROOT,template_registry=tr).plan(goal(
            "test.unknown.engine",
            available_gates=[
                "clean_synced","verified_backup","open_source_review",
                "risk_low","allowlisted_path","audit_log",
                "candidate_validated","tests_pass","evidence_pass","ff_only",
                "normal_non_force_push","remote_race_guard"
            ],
        ))
        self.assertEqual(p.steps[0].policy_effect,"ALLOW_WITH_GATES")
        self.assertTrue(p.steps[0].policy_execution_authorized)
        self.assertEqual(p.steps[0].step_status,"DENY_UNREGISTERED_ENGINE")
        self.assertEqual(p.status,"BLOCKED")

    def test_low_risk_documentation_with_gates_is_ready(self):
        g=goal(
            "phoenix.low_risk_documentation",
            available_gates=[
                "clean_synced","verified_backup","open_source_review",
                "risk_low","allowlisted_path","audit_log",
                "candidate_validated","tests_pass","evidence_pass","ff_only",
                "normal_non_force_push","remote_race_guard"
            ],
            context={"target_paths":["docs/automation/autonomous_generated/test.md"]},
        )
        p=AutonomousExecutionPlanner(ROOT).plan(g)
        update=[s for s in p.steps if s.action=="documentation.update"][0]
        self.assertEqual(update.step_status,"READY")
        self.assertTrue(update.gateway_required)
        self.assertEqual(p.status,"READY")

    def test_low_risk_documentation_missing_gate_is_gated(self):
        g=goal(
            "phoenix.low_risk_documentation",
            available_gates=["clean_synced"],
            context={"target_paths":["docs/automation/autonomous_generated/test.md"]},
        )
        p=AutonomousExecutionPlanner(ROOT).plan(g)
        update=[s for s in p.steps if s.action=="documentation.update"][0]
        self.assertEqual(update.step_status,"GATED_PENDING")
        self.assertIn("verified_backup",update.missing_gates)
        self.assertEqual(p.status,"GATED")

    def test_dependency_order_is_topological(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal("phoenix.low_risk_documentation"))
        pos={x:i for i,x in enumerate(p.topological_order)}
        for s in p.steps:
            for dep in s.dependencies:
                self.assertLess(pos[dep],pos[s.step_id])

    def test_plan_has_execution_batches(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal())
        flat=[x for batch in p.execution_batches for x in batch]
        self.assertEqual(set(flat),set(p.topological_order))

    def test_plan_hash_is_deterministic(self):
        planner=AutonomousExecutionPlanner(ROOT)
        a=planner.plan(goal())
        b=planner.plan(goal())
        self.assertEqual(a.goal_sha256,b.goal_sha256)
        self.assertEqual(a.plan_sha256,b.plan_sha256)

    def test_policy_bundle_bound_to_every_step(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal())
        self.assertTrue(p.policy_bundle_sha256)
        self.assertTrue(all(s.policy_bundle_sha256==p.policy_bundle_sha256 for s in p.steps))

    def test_recursive_subgoal_decomposition(self):
        sub={
            "schema":"PHOENIX_GOAL_SPEC_V1",
            "goal_id":"SUB",
            "objective":"Analyze a subgoal",
            "goal_type":"generic.analysis",
            "domain":"planning",
            "success_criteria":["subgoal valid"],
            "constraints":[],"available_gates":[],"context":{},"subgoals":[]
        }
        g=goal(subgoals=[sub])
        p=AutonomousExecutionPlanner(ROOT).plan(g)
        self.assertGreater(len(p.steps),3)
        self.assertTrue(any(".sg1-sub." in s.step_id for s in p.steps))

    def test_depth_bound_blocks_excessive_recursion(self):
        p=json.loads((CFG/"execution_planner_policy_v1.json").read_text(encoding="utf-8"))
        maxd=p["bounds"]["max_goal_depth"]
        raw={
            "schema":"PHOENIX_GOAL_SPEC_V1","goal_id":"ROOT","objective":"x",
            "goal_type":"generic.analysis","domain":"planning",
            "success_criteria":["x"],"constraints":[],"available_gates":[],"context":{},"subgoals":[]
        }
        cursor=raw
        for i in range(maxd+1):
            child={
                "schema":"PHOENIX_GOAL_SPEC_V1","goal_id":f"S{i}","objective":"x",
                "goal_type":"generic.analysis","domain":"planning",
                "success_criteria":["x"],"constraints":[],"available_gates":[],"context":{},"subgoals":[]
            }
            cursor["subgoals"]=[child]
            cursor=child
        with self.assertRaises(RuntimeError):
            AutonomousExecutionPlanner(ROOT).plan(GoalSpec.from_dict(raw))

    def test_fanout_bound_blocks(self):
        p=json.loads((CFG/"execution_planner_policy_v1.json").read_text(encoding="utf-8"))
        n=p["bounds"]["max_subgoals_per_goal"]+1
        subs=[{
            "schema":"PHOENIX_GOAL_SPEC_V1","goal_id":f"S{i}","objective":"x",
            "goal_type":"generic.analysis","domain":"planning","success_criteria":["x"],
            "constraints":[],"available_gates":[],"context":{},"subgoals":[]
        } for i in range(n)]
        with self.assertRaises(RuntimeError):
            AutonomousExecutionPlanner(ROOT).plan(goal(subgoals=subs))

    def test_cycle_in_custom_template_is_denied_by_dag(self):
        tr=json.loads((CFG/"goal_template_registry_v1.json").read_text(encoding="utf-8"))
        tr["templates"]["test.cycle"]={
            "description":"cycle",
            "steps":[
                {"key":"a","title":"a","action":"planning.analyze","risk":"LOW","mutating":False,"domain":"planning","engine_id":"autonomy.execution_planner","depends_on":["b"],"gates":[]},
                {"key":"b","title":"b","action":"planning.validate","risk":"LOW","mutating":False,"domain":"planning","engine_id":"autonomy.execution_planner","depends_on":["a"],"gates":[]}
            ]
        }
        with self.assertRaises(RuntimeError):
            AutonomousExecutionPlanner(ROOT,template_registry=tr).plan(goal("test.cycle"))

    def test_execution_coordinator_respects_dependencies(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal())
        c=ExecutionCoordinator()
        first=c.next_ready(p,set())
        self.assertEqual(len(first),1)
        second=c.next_ready(p,{first[0].step_id})
        self.assertEqual(len(second),1)

    def test_execution_ticket_is_not_gateway_permit(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal())
        s=ExecutionCoordinator().next_ready(p,set())[0]
        ticket=ExecutionCoordinator().execution_ticket(s)
        self.assertEqual(ticket["schema"],"PHOENIX_EXECUTION_TICKET_V1")
        self.assertIn("not a gateway permit",ticket["note"])

    def test_mutating_ready_ticket_requires_gateway(self):
        g=goal(
            "phoenix.low_risk_documentation",
            available_gates=[
                "clean_synced","verified_backup","open_source_review",
                "risk_low","allowlisted_path","audit_log",
                "candidate_validated","tests_pass","evidence_pass","ff_only",
                "normal_non_force_push","remote_race_guard"
            ],
            context={"target_paths":["docs/automation/autonomous_generated/test.md"]},
        )
        p=AutonomousExecutionPlanner(ROOT).plan(g)
        update=[s for s in p.steps if s.action=="documentation.update"][0]
        ticket=ExecutionCoordinator().execution_ticket(update)
        self.assertTrue(ticket["gateway_required"])
        self.assertEqual(ticket["engine_id"],"autonomy.low_risk_executor")

    def test_planner_engine_is_registered_read_only(self):
        reg=json.loads((CFG/"engine_registry_v1.json").read_text(encoding="utf-8"))
        e=[x for x in reg["engines"] if x["engine_id"]=="autonomy.execution_planner"][0]
        self.assertFalse(e["mutation_capable"])
        self.assertFalse(e["gateway_required"])

    def test_policy_bundle_includes_planner_inputs(self):
        m=json.loads((CFG/"policy_bundle_manifest_v1.json").read_text(encoding="utf-8"))
        self.assertIn("execution_planner_policy_v1.json",m["files"])
        self.assertIn("goal_template_registry_v1.json",m["files"])
        self.assertTrue(m["files"]["execution_planner_policy_v1.json"]["required"])

    def test_open_source_review_primary_and_fallback(self):
        d=json.loads((CFG/"open_source_execution_planner_review_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(d["primary"]["name"],"NetworkX")
        self.assertEqual(d["primary"]["license"],"BSD-3-Clause")
        self.assertEqual(d["fallback_or_richer_future_adapter"]["name"],"Unified Planning")
        self.assertEqual(d["fallback_or_richer_future_adapter"]["license"],"Apache-2.0")

    def test_no_plan_step_can_self_authorize(self):
        p=AutonomousExecutionPlanner(ROOT).plan(goal())
        for s in p.steps:
            self.assertIn(s.policy_effect,{"ALLOW","ALLOW_WITH_GATES","ESCALATE","DENY"})
            self.assertTrue(s.policy_rule_id)
            self.assertTrue(s.policy_bundle_sha256)

    def test_goal_requires_success_criterion(self):
        with self.assertRaises(ValueError):
            AutonomousExecutionPlanner(ROOT).plan(goal(success_criteria=[]))

if __name__=="__main__":
    unittest.main()
