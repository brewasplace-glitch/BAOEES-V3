import copy
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import (
    EngineManifestDiscovery,
    EngineOnboardingService,
    UniversalCapabilityExecutorRegistry,
)

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/"configs/phoenix"


def load(name):
    return json.loads((CFG/name).read_text(encoding="utf-8"))


def readonly_candidate():
    return {
        "schema":"PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id":"future.readonly.demo",
        "display_name":"Read-only Demo",
        "mutation_capable":False,
        "gateway_required":False,
        "allowed_actions":["research.inspect"],
        "allowed_domains":["research"],
        "action_profiles":[
            {
                "action":"research.inspect",
                "risk":"LOW",
                "domain":"research",
                "mutating":False,
                "plan_dispatchable":True
            }
        ],
        "adapters":[
            {
                "adapter_id":"future.readonly.demo.adapter",
                "actions":["research.inspect"],
                "kind":"callable_scaffold",
                "mutation_capable":False,
                "gateway_required":False,
                "plan_dispatchable":True,
                "priority":100
            }
        ],
        "metadata":{"test":True}
    }


def mutating_candidate():
    return {
        "schema":"PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id":"future.mutating.demo",
        "display_name":"Mutating Demo",
        "mutation_capable":True,
        "gateway_required":True,
        "allowed_actions":["demo.write"],
        "allowed_domains":["software"],
        "allowed_path_roots":["outputs/runtime/autonomy/demo/"],
        "action_profiles":[
            {
                "action":"demo.write",
                "risk":"LOW",
                "domain":"software",
                "mutating":True,
                "plan_dispatchable":True
            }
        ],
        "adapters":[
            {
                "adapter_id":"future.mutating.demo.adapter",
                "actions":["demo.write"],
                "kind":"callable_scaffold",
                "mutation_capable":True,
                "gateway_required":True,
                "plan_dispatchable":True,
                "priority":100
            }
        ],
        "metadata":{"test":True}
    }


class Phase6Tests(unittest.TestCase):
    def service(self,td):
        return EngineOnboardingService(ROOT,Path(td))

    def test_onboarding_policy_active_fail_closed(self):
        d=load("engine_onboarding_policy_v1.json")
        self.assertEqual(d["status"],"ACTIVE")
        self.assertTrue(d["fail_closed"])
        self.assertFalse(d["activation"]["automatic_mutating_engine_activation"])
        self.assertFalse(d["discovery"]["arbitrary_module_import"])

    def test_central_policy_version_23(self):
        d=load("autonomy_policy_v2.json")
        self.assertEqual(d["version"],"2.4.0")

    def test_phase6_engine_registered_gateway_required(self):
        d=load("engine_registry_v1.json")
        e=[x for x in d["engines"] if x["engine_id"]=="autonomy.engine_onboarding"][0]
        self.assertTrue(e["mutation_capable"])
        self.assertTrue(e["gateway_required"])
        self.assertEqual(len(e["allowed_actions"]),3)

    def test_phase6_adapter_coverage_registered(self):
        d=load("capability_executor_registry_v1.json")
        a=[x for x in d["adapters"] if x["adapter_id"]=="builtin.engine.onboarding.internal"][0]
        self.assertFalse(a["plan_dispatchable"])
        self.assertTrue(a["gateway_required"])
        self.assertEqual(len(a["actions"]),3)

    def test_phase5_registry_still_complete_with_phase6_engine(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        report=r.coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"],report["covered_engine_actions"])
        self.assertGreaterEqual(report["active_engines"],7)

    def test_candidate_and_proposal_schemas_draft_2020_12(self):
        for n in ("engine_candidate_manifest_v1.schema.json","engine_onboarding_proposal_v1.schema.json"):
            d=load(n)
            self.assertEqual(d["$schema"],"https://json-schema.org/draft/2020-12/schema")

    def test_readonly_candidate_admission_passes(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(readonly_candidate(),persist=False)
            self.assertEqual(p["admission"]["status"],"PASS")
            self.assertEqual(p["activation"]["status"],"SCAFFOLD_IMPLEMENTATION_REQUIRED")

    def test_readonly_candidate_generates_scaffold_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(readonly_candidate(),persist=False)
            self.assertEqual(len(p["generated_scaffolds"]),1)
            self.assertFalse(p["generated_scaffolds"][0]["activation_ready"])
            self.assertRegex(p["generated_scaffolds"][0]["sha256"],r"^[0-9a-f]{64}$")

    def test_persisted_scaffold_is_real_python_file(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(readonly_candidate(),persist=True)
            rel=p["generated_scaffolds"][0]["relative_path"]
            path=Path(td)/"engine_onboarding"/rel
            self.assertTrue(path.is_file())
            text=path.read_text(encoding="utf-8")
            self.assertIn("NotImplementedError",text)
            self.assertIn("NOT activated automatically",text)

    def test_persisted_proposal_is_hmac_signed(self):
        with tempfile.TemporaryDirectory() as td:
            s=self.service(td)
            p=s.build_proposal(readonly_candidate(),persist=True)
            stored=json.loads(Path(p["runtime_path"]).read_text(encoding="utf-8"))
            self.assertTrue(s.verify_signed_artifact(stored))

    def test_discovery_snapshot_is_signed_and_nonexecuting(self):
        with tempfile.TemporaryDirectory() as td:
            s=self.service(td)
            snap=s.discover(persist=False)
            self.assertFalse(snap["code_loaded_during_discovery"])
            self.assertTrue(s.verify_signed_artifact(snap))

    def test_repository_manifest_discovery_reads_json_without_import(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            manifest=root/"demo"/"phoenix_engine_manifest_v1.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps(readonly_candidate()),encoding="utf-8")
            policy=load("engine_onboarding_policy_v1.json")
            records=EngineManifestDiscovery(root,policy).repository_manifests()
            self.assertEqual(len(records),1)
            self.assertEqual(records[0].status,"DISCOVERED")
            self.assertEqual(records[0].engine_id,"future.readonly.demo")

    def test_invalid_json_discovery_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            manifest=root/"phoenix_engine_manifest_v1.json"
            manifest.write_text("{broken",encoding="utf-8")
            records=EngineManifestDiscovery(root,load("engine_onboarding_policy_v1.json")).repository_manifests()
            self.assertEqual(records[0].status,"REJECT_INVALID_JSON")

    def test_entry_point_discovery_contract_does_not_load_code(self):
        policy=load("engine_onboarding_policy_v1.json")
        records=EngineManifestDiscovery(ROOT,policy).entry_points()
        for r in records:
            self.assertEqual(r.status,"DISCOVERED_NOT_LOADED")
            self.assertFalse(r.details["code_loaded"])

    def test_existing_engine_id_collision_blocks(self):
        c=readonly_candidate()
        c["engine_id"]="autonomy.execution_planner"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertTrue(any("ENGINE_ID_COLLISION" in x for x in p["admission"]["errors"]))

    def test_existing_adapter_id_collision_blocks(self):
        c=readonly_candidate()
        c["adapters"][0]["adapter_id"]="builtin.planner.readonly"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertTrue(any("ADAPTER_ID_COLLISION" in x for x in p["admission"]["errors"]))

    def test_mutating_candidate_without_gateway_blocks(self):
        c=mutating_candidate()
        c["gateway_required"]=False
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertIn("gateway_required",p["admission"]["errors"])

    def test_mutating_candidate_without_scope_blocks(self):
        c=mutating_candidate()
        c.pop("allowed_path_roots")
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertIn("mutation_scope",p["admission"]["errors"])

    def test_adapter_action_scope_expansion_blocks(self):
        c=readonly_candidate()
        c["adapters"][0]["actions"].append("not.allowed")
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertTrue(any(x.startswith("adapter_action_scope") for x in p["admission"]["errors"]))

    def test_adapter_coverage_gap_blocks(self):
        c=readonly_candidate()
        c["allowed_actions"].append("qa.inspect")
        c["action_profiles"].append({
            "action":"qa.inspect","risk":"LOW","domain":"research",
            "mutating":False,"plan_dispatchable":True
        })
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertIn("adapter_coverage",p["admission"]["errors"])

    def test_profile_coverage_gap_blocks(self):
        c=readonly_candidate()
        c["action_profiles"]=[]
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertIn("action_profiles_coverage",p["admission"]["errors"])

    def test_profile_domain_must_be_declared(self):
        c=readonly_candidate()
        c["action_profiles"][0]["domain"]="qa"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertTrue(any(x.startswith("profile_domain") for x in p["admission"]["errors"]))

    def test_internal_gateway_adapter_cannot_be_plan_dispatchable(self):
        c=readonly_candidate()
        c["adapters"][0]["kind"]="internal_gateway_managed"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertTrue(any(x.startswith("internal_plan_dispatch") for x in p["admission"]["errors"]))

    def test_existing_implementation_requires_target(self):
        c=readonly_candidate()
        c["adapters"][0]["kind"]="existing_implementation"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertTrue(any(x.startswith("implementation_missing") for x in p["admission"]["errors"]))

    def test_existing_implementation_can_reach_governed_install_required(self):
        c=readonly_candidate()
        c["adapters"][0]["kind"]="existing_implementation"
        c["adapters"][0]["implementation"]="future_demo.adapters:ReadAdapter"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertEqual(p["admission"]["status"],"PASS")
            self.assertEqual(p["activation"]["status"],"GOVERNED_INSTALL_REQUIRED")
            self.assertFalse(p["activation"]["automatic_activation"])

    def test_unknown_mutating_action_is_policy_blocked_not_auto_activated(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(mutating_candidate(),persist=False)
            self.assertEqual(p["admission"]["status"],"PASS")
            self.assertEqual(p["activation"]["status"],"BLOCKED_POLICY_COVERAGE")
            self.assertIn("demo.write",p["activation"]["policy_denied_actions"])
            self.assertFalse(p["activation"]["automatic_activation"])

    def test_proposal_never_performs_repository_write(self):
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(readonly_candidate(),persist=False)
            self.assertFalse(p["activation"]["repository_write_performed"])

    def test_future_contract_has_autonomous_onboarding_rules(self):
        d=load("future_engine_admission_contract_v1.json")
        x=d["autonomous_onboarding_contract"]
        self.assertFalse(x["mutating_engine_automatic_activation"])
        self.assertTrue(x["discovery_must_not_import_candidate_code"])
        self.assertEqual(d["version"],"1.3.0")

    def test_open_source_review_pluggy_stevedore(self):
        d=load("open_source_engine_discovery_onboarding_review_v1.json")
        self.assertEqual(d["primary"]["name"],"pluggy")
        self.assertEqual(d["primary"]["license"],"MIT")
        self.assertEqual(d["fallback"]["name"],"stevedore")
        self.assertEqual(d["fallback"]["license"],"Apache-2.0")
        self.assertFalse(d["active_v1_backend"]["imports_plugin_code_during_discovery"])

    def test_policy_bundle_binds_onboarding_policy(self):
        d=load("policy_bundle_manifest_v1.json")
        self.assertIn("engine_onboarding_policy_v1.json",d["files"])
        self.assertTrue(d["files"]["engine_onboarding_policy_v1.json"]["required"])
        self.assertEqual(d["engine_onboarding_policy_version"],"1.0.0")

    def test_executor_registry_version_11_and_engine_registry_14(self):
        self.assertEqual(load("capability_executor_registry_v1.json")["version"],"1.2.0")
        self.assertEqual(load("engine_registry_v1.json")["version"],"1.5.0")

    def test_failed_admission_report_can_persist_without_scaffold(self):
        c=readonly_candidate()
        c["engine_id"]="autonomy.execution_planner"
        with tempfile.TemporaryDirectory() as td:
            s=self.service(td)
            p=s.build_proposal(c,persist=True)
            self.assertEqual(p["admission"]["status"],"FAIL")
            self.assertTrue(Path(p["runtime_path"]).is_file())
            self.assertFalse(p["generated_scaffolds"])

    def test_no_candidate_source_import_occurs_in_proposal(self):
        c=readonly_candidate()
        c["metadata"]["malicious_module"]="this.must.not.be.imported"
        with tempfile.TemporaryDirectory() as td:
            p=self.service(td).build_proposal(c,persist=False)
            self.assertFalse(p["admission"]["capability_discovery_code_loaded"])


if __name__=="__main__":
    unittest.main()
