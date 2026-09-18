import copy
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import (
    AutonomousExecutionOrchestrator,
    AutonomousExecutionPlanner,
    GoalSpec,
    UniversalCapabilityExecutorRegistry,
)

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/"configs/phoenix"

def load(name):
    return json.loads((CFG/name).read_text(encoding="utf-8"))

def generic_goal():
    return GoalSpec.from_dict({
        "schema":"PHOENIX_GOAL_SPEC_V1",
        "goal_id":"P5-READONLY",
        "objective":"Prove universal capability executor adapter dispatch.",
        "goal_type":"generic.analysis",
        "domain":"planning",
        "success_criteria":["all ready steps dispatch through registered adapters"],
        "constraints":[],
        "available_gates":[],
        "context":{},
        "subgoals":[]
    })

class Phase5Tests(unittest.TestCase):
    def test_registry_active_fail_closed(self):
        d=load("capability_executor_registry_v1.json")
        self.assertEqual(d["status"],"ACTIVE")
        self.assertTrue(d["fail_closed"])
        self.assertEqual(d["future_action_default"],"DENY_NO_REGISTERED_ADAPTER")

    def test_registry_complete_coverage(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        report=r.coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"],report["covered_engine_actions"])

    def test_every_active_engine_action_is_covered(self):
        cfg=load("capability_executor_registry_v1.json")
        eng=load("engine_registry_v1.json")
        covered={(a["engine_id"],x) for a in cfg["adapters"] if a["status"]=="ACTIVE" for x in a["actions"]}
        for e in eng["engines"]:
            if e["status"]!="ACTIVE":
                continue
            for action in e["allowed_actions"]:
                self.assertIn((e["engine_id"],action),covered)

    def test_mutating_adapters_gateway_required(self):
        d=load("capability_executor_registry_v1.json")
        for a in d["adapters"]:
            if a["status"]=="ACTIVE" and a["mutation_capable"]:
                self.assertTrue(a["gateway_required"])

    def test_plan_dispatch_bindings_are_unique(self):
        d=load("capability_executor_registry_v1.json")
        seen=set()
        for a in d["adapters"]:
            if not a["plan_dispatchable"] or a["status"]!="ACTIVE":
                continue
            for action in a["actions"]:
                key=(a["engine_id"],action)
                self.assertNotIn(key,seen)
                seen.add(key)

    def test_resolve_readonly_adapter(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT,host=object())
        d,a=r.resolve("autonomy.execution_planner","research.inspect")
        self.assertEqual(d.adapter_id,"builtin.planner.readonly")
        self.assertEqual(a.adapter_id,d.adapter_id)

    def test_resolve_lowrisk_adapter(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT,host=object())
        d,a=r.resolve("autonomy.low_risk_executor","documentation.update")
        self.assertEqual(d.adapter_id,"builtin.lowrisk.plan")
        self.assertTrue(d.gateway_required)

    def test_resolve_promoter_adapter(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT,host=object())
        d,a=r.resolve("autonomy.mainline_promoter","git.fast_forward_promotion")
        self.assertEqual(d.adapter_id,"builtin.mainline.promoter")

    def test_internal_action_not_plan_dispatchable(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT,host=object())
        self.assertIsNone(r.resolve("bib.auto_sync","bib.auto_sync"))
        d=r.descriptor_for("bib.auto_sync","bib.auto_sync",plan_dispatch_only=False)
        self.assertIsNotNone(d)
        self.assertFalse(d.plan_dispatchable)

    def test_unknown_engine_action_fails_closed(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT,host=object())
        self.assertIsNone(r.resolve("future.unknown","do.anything"))

    def test_action_scope_expansion_rejected(self):
        c=load("capability_executor_registry_v1.json")
        e=load("engine_registry_v1.json")
        bad=copy.deepcopy(c)
        bad["adapters"][0]["actions"].append("not.allowed")
        with self.assertRaises(RuntimeError):
            UniversalCapabilityExecutorRegistry(bad,e)

    def test_missing_engine_action_coverage_rejected(self):
        c=load("capability_executor_registry_v1.json")
        e=load("engine_registry_v1.json")
        bad=copy.deepcopy(c)
        bad["adapters"]=[a for a in bad["adapters"] if a["adapter_id"]!="builtin.bib.autosync"]
        with self.assertRaises(RuntimeError):
            UniversalCapabilityExecutorRegistry(bad,e)

    def test_mutation_capability_mismatch_rejected(self):
        c=load("capability_executor_registry_v1.json")
        e=load("engine_registry_v1.json")
        bad=copy.deepcopy(c)
        bad["adapters"][0]["mutation_capable"]=True
        bad["adapters"][0]["gateway_required"]=True
        with self.assertRaises(RuntimeError):
            UniversalCapabilityExecutorRegistry(bad,e)

    def test_duplicate_adapter_id_rejected(self):
        c=load("capability_executor_registry_v1.json")
        e=load("engine_registry_v1.json")
        bad=copy.deepcopy(c)
        bad["adapters"].append(copy.deepcopy(bad["adapters"][0]))
        with self.assertRaises(RuntimeError):
            UniversalCapabilityExecutorRegistry(bad,e)

    def test_duplicate_plan_binding_rejected(self):
        c=load("capability_executor_registry_v1.json")
        e=load("engine_registry_v1.json")
        bad=copy.deepcopy(c)
        dup=copy.deepcopy(bad["adapters"][0])
        dup["adapter_id"]="duplicate.readonly"
        dup["implementation"]="phoenix.autonomy.executor_adapters:ReadOnlyPlannerAdapter"
        with self.assertRaises(RuntimeError):
            UniversalCapabilityExecutorRegistry(bad|{"adapters":bad["adapters"]+[dup]},e)

    def test_future_engine_admission_success(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        engine={
            "engine_id":"future.demo","status":"ACTIVE","mutation_capable":True,
            "gateway_required":True,"allowed_actions":["demo.write"]
        }
        adapters=[{
            "adapter_id":"future.demo.adapter","status":"ACTIVE","engine_id":"future.demo",
            "actions":["demo.write"],"mutation_capable":True,"gateway_required":True,
            "plan_dispatchable":True,"implementation":"future.demo:Adapter","priority":100
        }]
        r.assert_future_engine_admission(engine,adapters)

    def test_future_mutating_engine_without_gateway_rejected(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        engine={
            "engine_id":"future.demo","status":"ACTIVE","mutation_capable":True,
            "gateway_required":False,"allowed_actions":["demo.write"]
        }
        with self.assertRaises(PermissionError):
            r.assert_future_engine_admission(engine,[])

    def test_future_engine_missing_action_adapter_rejected(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        engine={
            "engine_id":"future.demo","status":"ACTIVE","mutation_capable":False,
            "gateway_required":False,"allowed_actions":["demo.read"]
        }
        with self.assertRaises(PermissionError):
            r.assert_future_engine_admission(engine,[])

    def test_future_adapter_wrong_engine_binding_rejected(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        engine={
            "engine_id":"future.demo","status":"ACTIVE","mutation_capable":False,
            "gateway_required":False,"allowed_actions":["demo.read"]
        }
        adapters=[{
            "adapter_id":"wrong","status":"ACTIVE","engine_id":"future.other",
            "actions":["demo.read"],"mutation_capable":False,"gateway_required":False,
            "plan_dispatchable":True,"implementation":"future.demo:Adapter","priority":100
        }]
        with self.assertRaises(PermissionError):
            r.assert_future_engine_admission(engine,adapters)

    def test_engine_registry_declares_adapter_ids(self):
        e=load("engine_registry_v1.json")
        for engine in e["engines"]:
            if engine["status"]=="ACTIVE":
                self.assertTrue(engine.get("executor_adapter_ids"))

    def test_policy_bundle_integrity_binds_registry(self):
        m=load("policy_bundle_manifest_v1.json")
        self.assertIn("capability_executor_registry_v1.json",m["files"])
        self.assertTrue(m["files"]["capability_executor_registry_v1.json"]["required"])
        self.assertTrue(str(m["capability_executor_registry_version"]).startswith("1.3."))

    def test_future_admission_contract_requires_adapter_coverage(self):
        d=load("future_engine_admission_contract_v1.json")
        x=d["executor_adapter_contract"]
        self.assertTrue(x["all_active_engine_actions_require_registry_coverage"])
        self.assertEqual(x["future_action_default"],"DENY_NO_REGISTERED_ADAPTER")

    def test_open_source_review_primary_and_fallback(self):
        d=load("open_source_executor_adapter_registry_review_v1.json")
        self.assertEqual(d["primary"]["name"],"pluggy")
        self.assertEqual(d["primary"]["license"],"MIT")
        self.assertEqual(d["fallback"]["name"],"stevedore")
        self.assertEqual(d["fallback"]["license"],"Apache-2.0")

    def test_schemas_are_draft_2020_12(self):
        for name in (
            "capability_executor_registry_v1.schema.json",
            "executor_adapter_contract_v1.schema.json",
        ):
            d=load(name)
            self.assertEqual(d["$schema"],"https://json-schema.org/draft/2020-12/schema")

    def test_orchestrator_dispatches_readonly_via_registry_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            plan=AutonomousExecutionPlanner(ROOT).plan(generic_goal())
            orch=AutonomousExecutionOrchestrator(ROOT,Path(td))
            state=orch.run(plan)
            self.assertEqual(state["status"],"COMPLETE")
            starts=[x for x in state["events"] if x["event"]=="READ_ONLY_STEP_START"]
            self.assertTrue(starts)
            self.assertTrue(all(x["payload"]["adapter_id"]=="builtin.planner.readonly" for x in starts))

    def test_orchestrator_has_universal_registry(self):
        with tempfile.TemporaryDirectory() as td:
            orch=AutonomousExecutionOrchestrator(ROOT,Path(td))
            report=orch.executor_registry.coverage_report()
            self.assertTrue(report["complete"])

if __name__=="__main__":
    unittest.main()
