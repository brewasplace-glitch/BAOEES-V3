import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from phoenix.autonomy import (
    AdapterImplementationValidator,
    EngineActivationService,
    EngineOnboardingService,
    LocalIntegrityKey,
    UniversalCapabilityExecutorRegistry,
)

ROOT=Path(__file__).resolve().parents[2]
CFG=ROOT/"configs/phoenix"


def load(name):
    return json.loads((CFG/name).read_text(encoding="utf-8"))


def candidate(engine_id="future.activation.demo",adapter_id="future.activation.demo.adapter"):
    return {
        "schema":"PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id":engine_id,
        "display_name":"Activation Demo",
        "mutation_capable":False,
        "gateway_required":False,
        "allowed_actions":["research.inspect"],
        "allowed_domains":["research"],
        "action_profiles":[{
            "action":"research.inspect","risk":"LOW","domain":"research",
            "mutating":False,"plan_dispatchable":True
        }],
        "adapters":[{
            "adapter_id":adapter_id,
            "actions":["research.inspect"],"kind":"callable_scaffold",
            "mutation_capable":False,"gateway_required":False,
            "plan_dispatchable":True,"priority":100
        }],
        "metadata":{"test":True}
    }


def safe_source(descriptor,engine_id):
    class_name=descriptor["implementation"].partition(":")[2]
    return (
        "from __future__ import annotations\n"
        "from phoenix.autonomy.executor_adapters import AdapterExecutionResult\n\n"
        f"class {class_name}:\n"
        f"    adapter_id = {descriptor['adapter_id']!r}\n"
        f"    engine_id = {engine_id!r}\n"
        f"    actions = {tuple(descriptor['actions'])!r}\n"
        f"    mutation_capable = {bool(descriptor['mutation_capable'])!r}\n"
        f"    gateway_required = {bool(descriptor['gateway_required'])!r}\n\n"
        "    def __init__(self, host):\n"
        "        self.host = host\n\n"
        "    def execute(self, ctx):\n"
        "        return AdapterExecutionResult(\"COMPLETE\", result={\"engine_id\": self.engine_id, \"action\": ctx.step.action})\n"
    )


def git(repo,*args):
    cp=subprocess.run(
        ["git","-c","core.longpaths=true","-C",str(repo),*args],
        text=True,encoding="utf-8",stdout=subprocess.PIPE,stderr=subprocess.STDOUT
    )
    if cp.returncode:
        raise RuntimeError(cp.stdout)
    return cp.stdout.strip()


class Phase7Tests(unittest.TestCase):
    def service(self,td,repo=ROOT):
        return EngineActivationService(repo,Path(td))

    def proposal_and_source(self,td,repo=ROOT):
        service=EngineActivationService(repo,Path(td))
        # Use the activation service's Phase-6 verifier/signer instance for the
        # normal helper path. Cross-instance persistence is tested separately.
        onboarding=service.onboarding
        proposal=onboarding.build_proposal(candidate(),persist=True)
        descriptor=proposal["executor_registry_patch"][0]
        path=Path(td)/"implementation.py"
        path.write_text(safe_source(descriptor,proposal["engine_id"]),encoding="utf-8")
        return service,proposal,Path(proposal["runtime_path"]),descriptor,path

    def test_activation_policy_active_fail_closed(self):
        d=load("engine_activation_policy_v1.json")
        self.assertEqual(d["status"],"ACTIVE")
        self.assertTrue(d["fail_closed"])
        self.assertFalse(d["implementation"]["candidate_code_execution_during_validation"])
        self.assertTrue(d["governed_install"]["explicit_approval_required"])

    def test_central_policy_version_24(self):
        self.assertEqual(load("autonomy_policy_v2.json")["version"],"2.6.0")

    def test_phase7_engine_registered_gateway_required(self):
        d=load("engine_registry_v1.json")
        e=[x for x in d["engines"] if x["engine_id"]=="autonomy.engine_activation"][0]
        self.assertTrue(e["mutation_capable"])
        self.assertTrue(e["gateway_required"])
        self.assertIn("engine.activation.repository.apply",e["allowed_actions"])
        self.assertIn("phoenix/autonomy/generated_adapters/",e["allowed_path_roots"])

    def test_phase7_internal_adapter_covers_activation_actions(self):
        d=load("capability_executor_registry_v1.json")
        a=[x for x in d["adapters"] if x["adapter_id"]=="builtin.engine.activation.internal"][0]
        self.assertFalse(a["plan_dispatchable"])
        self.assertTrue(a["gateway_required"])
        self.assertIn("engine.activation.repository.apply",a["actions"])

    def test_registry_coverage_remains_complete(self):
        r=UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        report=r.coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"],report["covered_engine_actions"])
        self.assertGreaterEqual(report["active_engines"],8)

    def test_phase7_schemas_draft_2020_12(self):
        for name in (
            "engine_activation_transaction_v1.schema.json",
            "generated_adapter_implementation_contract_v1.schema.json",
        ):
            self.assertEqual(load(name)["$schema"],"https://json-schema.org/draft/2020-12/schema")

    def test_safe_generated_implementation_passes(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            val=service.validator.validate(path.read_text(),engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertTrue(val.activation_ready)
            self.assertRegex(val.source_sha256,r"^[0-9a-f]{64}$")
            self.assertTrue(val.target_path.startswith("phoenix/autonomy/generated_adapters/"))

    def test_phase6_scaffold_is_not_activation_ready(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,_=self.proposal_and_source(td)
            scaffold=Path(td)/"engine_onboarding"/proposal["generated_scaffolds"][0]["relative_path"]
            val=service.validator.validate(scaffold.read_text(),engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertFalse(val.activation_ready)
            self.assertIn("IMPLEMENTATION_INCOMPLETE",val.errors)

    def test_forbidden_os_import_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            source="import os\n"+path.read_text()
            val=service.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertFalse(val.activation_ready)
            self.assertTrue(any("IMPORT_DENY" in x or "TOPLEVEL_NODE_DENY" in x for x in val.errors))

    def test_forbidden_open_call_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            source=path.read_text().replace(
                'return AdapterExecutionResult("COMPLETE", result={"engine_id": self.engine_id, "action": ctx.step.action})',
                'open("bad.txt","w")\n        return AdapterExecutionResult("COMPLETE", result={})'
            )
            val=service.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertIn("FORBIDDEN_CALL:open",val.errors)

    def test_class_decorator_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            source=path.read_text().replace("class ","@staticmethod\nclass ",1)
            val=service.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertIn("CLASS_DECORATOR_DENY",val.errors)

    def test_class_inheritance_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            class_name=descriptor["implementation"].partition(":")[2]
            source=path.read_text().replace(f"class {class_name}:",f"class {class_name}(object):")
            val=service.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertIn("CLASS_INHERITANCE_DENY",val.errors)

    def test_dunder_attribute_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            source=path.read_text().replace("ctx.step.action","ctx.__class__")
            val=service.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertIn("DUNDER_ATTRIBUTE_DENY:__class__",val.errors)

    def test_contract_value_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,_,descriptor,path=self.proposal_and_source(td)
            source=path.read_text().replace(descriptor["adapter_id"],"wrong.adapter",1)
            val=service.validator.validate(source,engine_id=proposal["engine_id"],descriptor=descriptor)
            self.assertIn("CONTRACT_VALUE_MISMATCH:adapter_id",val.errors)

    def test_phase6_proposal_hmac_persists_across_service_restart(self):
        with tempfile.TemporaryDirectory() as td:
            runtime=Path(td)
            first=EngineActivationService(ROOT,runtime)
            proposal=first.onboarding.build_proposal(candidate(),persist=True)
            proposal_path=Path(proposal["runtime_path"])

            # A fresh service instance must load exactly the persisted Phase-6
            # key and verify the already-signed proposal.
            second=EngineActivationService(ROOT,runtime)
            loaded=second.load_phase6_proposal(proposal_path)
            self.assertEqual(loaded["proposal_id"],proposal["proposal_id"])
            self.assertEqual(loaded["engine_id"],proposal["engine_id"])

    def test_local_integrity_key_is_binary_safe_on_windows(self):
        with tempfile.TemporaryDirectory() as td:
            key_path=Path(td)/"integrity"/"binary_hmac_v1.key"
            forced_key=b"\n"+(b"K"*31)
            with mock.patch(
                "phoenix.autonomy.approval_resume.secrets.token_bytes",
                return_value=forced_key,
            ):
                created=LocalIntegrityKey(key_path).load_or_create()

            self.assertEqual(created,forced_key)
            self.assertEqual(key_path.read_bytes(),forced_key)
            self.assertEqual(key_path.stat().st_size,32)
            self.assertEqual(LocalIntegrityKey(key_path).load_or_create(),forced_key)

    def test_missing_implementation_transaction_waits(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,proposal_path,_,_=self.proposal_and_source(td)
            tx=service.build_transaction(proposal_path,{},persist=False)
            self.assertEqual(tx["status"],"IMPLEMENTATION_REQUIRED")
            self.assertFalse(tx["automatic_activation"])

    def test_valid_implementation_transaction_ready(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,proposal_path,descriptor,path=self.proposal_and_source(td)
            tx=service.build_transaction(proposal_path,{descriptor["adapter_id"]:path},persist=False)
            self.assertEqual(tx["status"],"READY_FOR_GOVERNED_INSTALL")
            self.assertEqual(len(tx["planned_paths"]),4)
            self.assertIn(descriptor["adapter_id"],tx["implementation_sha256"])

    def test_persisted_bundle_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,proposal_path,descriptor,path=self.proposal_and_source(td)
            tx=service.build_transaction(proposal_path,{descriptor["adapter_id"]:path},persist=True)
            result=service.verify_bundle(Path(tx["bundle_dir"]))
            self.assertEqual(result["transaction"]["transaction_id"],tx["transaction_id"])

    def test_bundle_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,proposal_path,descriptor,path=self.proposal_and_source(td)
            tx=service.build_transaction(proposal_path,{descriptor["adapter_id"]:path},persist=True)
            bundle=Path(tx["bundle_dir"])
            target=bundle/"repo_files"/tx["planned_paths"][-1]
            target.write_text(target.read_text()+"#tamper\n",encoding="utf-8")
            with self.assertRaises(PermissionError):
                service.verify_bundle(bundle)

    def test_tampered_phase6_proposal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,proposal_path,descriptor,path=self.proposal_and_source(td)
            data=json.loads(proposal_path.read_text())
            data["engine_id"]="tampered.engine"
            proposal_path.write_text(json.dumps(data),encoding="utf-8")
            with self.assertRaises(PermissionError):
                service.build_transaction(proposal_path,{descriptor["adapter_id"]:path},persist=False)

    def test_policy_denied_candidate_blocks_activation(self):
        with tempfile.TemporaryDirectory() as td:
            service=EngineActivationService(ROOT,Path(td))
            onboarding=EngineOnboardingService(ROOT,Path(td),gateway=service.gateway)
            c=candidate("future.denied.demo","future.denied.demo.adapter")
            c["mutation_capable"]=True; c["gateway_required"]=True
            c["allowed_actions"]=["demo.write"]; c["allowed_domains"]=["software"]
            c["allowed_path_roots"]=["outputs/runtime/autonomy/demo/"]
            c["action_profiles"]=[{"action":"demo.write","risk":"LOW","domain":"software","mutating":True,"plan_dispatchable":True}]
            c["adapters"][0].update({"actions":["demo.write"],"mutation_capable":True,"gateway_required":True})
            p=onboarding.build_proposal(c,persist=True)
            self.assertEqual(p["activation"]["status"],"BLOCKED_POLICY_COVERAGE")
            proposal_path=Path(p["runtime_path"])
            source=Path(td)/"impl.py"; source.write_text("pass\n",encoding="utf-8")
            tx=service.build_transaction(proposal_path,{p["executor_registry_patch"][0]["adapter_id"]:source},persist=False)
            self.assertEqual(tx["status"],"BLOCKED")
            self.assertTrue(any(x.startswith("POLICY_DENIED_ACTIONS") for x in tx["errors"]))

    def test_apply_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as td:
            service,proposal,proposal_path,descriptor,path=self.proposal_and_source(td)
            tx=service.build_transaction(proposal_path,{descriptor["adapter_id"]:path},persist=True)
            with self.assertRaises(PermissionError):
                service.apply_bundle(Path(tx["bundle_dir"]),Path(td)/"none.json",set(),explicit_approval=False)

    def test_future_contract_activation_rules(self):
        d=load("future_engine_admission_contract_v1.json")
        self.assertEqual(d["version"],"1.5.0")
        x=d["governed_activation_contract"]
        self.assertTrue(x["explicit_activation_approval_required"])
        self.assertTrue(x["verified_backup_required"])
        self.assertTrue(x["policy_deny_cannot_be_auto_weakened"])

    def test_policy_bundle_binds_activation_policy(self):
        d=load("policy_bundle_manifest_v1.json")
        self.assertEqual(d["engine_activation_policy_version"],"1.0.0")
        self.assertTrue(d["files"]["engine_activation_policy_v1.json"]["required"])

    def test_open_source_review_keeps_execution_disabled(self):
        d=load("open_source_engine_activation_sandbox_review_v1.json")
        self.assertEqual(d["primary_defense_in_depth_candidate"]["name"],"RestrictedPython")
        self.assertEqual(d["primary_defense_in_depth_candidate"]["version_reviewed"],"8.5")
        self.assertEqual(d["fallback_isolation_candidate"]["name"],"Microsoft Execution Containers (MXC)")
        self.assertFalse(d["active_v1_strategy"]["candidate_code_executed_during_validation"])

    def test_generated_adapter_package_exists(self):
        self.assertTrue((ROOT/"phoenix/autonomy/generated_adapters/__init__.py").is_file())

    def test_powershell_activation_runner_requires_explicit_approval_and_backup(self):
        text=(ROOT/"runners/PROJECT_PHOENIX_4_41_governed_engine_activation_v1.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("ApproveActivation",text)
        self.assertIn("PROJECT_PHOENIX_4_41_full_backup_v1.ps1",text)
        self.assertIn("REMOTE_RACE_GUARD",text)
        self.assertNotIn("push --force",text.lower())
        self.assertNotIn("reset --hard",text.lower())

    def test_real_apply_to_isolated_git_repo(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            repo=base/"repo"
            # The installed regression runs with ROOT at the real repository.
            # Never copy its .git directory into the isolated fixture: doing so
            # inherits the live branch/remotes and makes git init non-isolated.
            shutil.copytree(
                ROOT,
                repo,
                ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc"),
            )
            git(repo,"init")
            git(repo,"config","user.email","phase7@test.invalid")
            git(repo,"config","user.name","PHOENIX Phase7 Test")
            # -B is stable whether the user's global init.defaultBranch already
            # selected project-phoenix or git init selected another branch.
            git(repo,"checkout","-B","project-phoenix")
            git(repo,"add",".")
            git(repo,"commit","-m","baseline")
            remote=base/"remote.git"
            subprocess.run(["git","init","--bare",str(remote)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            git(repo,"remote","add","origin",str(remote))
            git(repo,"push","-u","origin","project-phoenix")

            runtime=base/"runtime"
            service=EngineActivationService(repo,runtime)
            onboarding=EngineOnboardingService(repo,runtime,gateway=service.gateway)
            proposal=onboarding.build_proposal(candidate(),persist=True)
            descriptor=proposal["executor_registry_patch"][0]
            implementation=base/"impl.py"
            implementation.write_text(safe_source(descriptor,proposal["engine_id"]),encoding="utf-8")
            tx=service.build_transaction(
                Path(proposal["runtime_path"]),{descriptor["adapter_id"]:implementation},persist=True
            )
            head=git(repo,"rev-parse","HEAD")
            receipt=base/"BACKUP_RECEIPT.json"
            receipt.write_text(json.dumps({
                "status":"PASS","baseline":head,"bundle_verified":True,"snapshot_verified":True
            }),encoding="utf-8")
            result=service.apply_bundle(
                Path(tx["bundle_dir"]),receipt,set(tx["implementation_sha256"].values()),explicit_approval=True
            )
            self.assertEqual(result["status"],"ACTIVATION_IN_PROGRESS")
            for rel in result["planned_paths"]:
                self.assertTrue((repo/rel).is_file())
            r=UniversalCapabilityExecutorRegistry.from_repo(repo)
            self.assertTrue(r.coverage_report()["complete"])
            new_engine=[e for e in load_from(repo,"engine_registry_v1.json")["engines"] if e["engine_id"]==proposal["engine_id"]]
            self.assertEqual(len(new_engine),1)


def load_from(repo,name):
    return json.loads((Path(repo)/"configs/phoenix"/name).read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
