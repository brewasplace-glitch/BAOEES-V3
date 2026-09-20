import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import (
    AdapterSynthesisService,
    BoundedLevel3CycleService,
    DisabledRuntimeProvider,
    PodmanMachineRuntimeProvider,
    RuntimeProviderProbe,
    UniversalCapabilityExecutorRegistry,
    WindowsSandboxRuntimeProvider,
)
from phoenix.autonomy.isolated_runtime import build_adapter_harness


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs/phoenix"


def load(name):
    return json.loads((CFG / name).read_text(encoding="utf-8"))


def candidate():
    return {
        "schema": "PHOENIX_ENGINE_CANDIDATE_MANIFEST_V1",
        "engine_id": "future.phase9.proof",
        "display_name": "Phase 9 Runtime Proof",
        "mutation_capable": False,
        "gateway_required": False,
        "allowed_actions": ["research.inspect"],
        "allowed_domains": ["research"],
        "action_profiles": [
            {
                "action": "research.inspect",
                "risk": "LOW",
                "domain": "research",
                "mutating": False,
                "plan_dispatchable": True,
            }
        ],
        "adapters": [
            {
                "adapter_id": "future.phase9.proof.adapter",
                "actions": ["research.inspect"],
                "kind": "callable_scaffold",
                "mutation_capable": False,
                "gateway_required": False,
                "plan_dispatchable": True,
                "priority": 100,
            }
        ],
        "metadata": {"phase9_proof": True},
    }


class FakeBoundaryProvider:
    provider_id = "test.only.accepted_boundary"
    provider_version = "1.0.0"

    def __init__(self, *, available=True, mismatch=False, executed=True):
        self.available = available
        self.mismatch = mismatch
        self.executed = executed

    def probe(self):
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            self.available,
            True,
            self.available,
            () if self.available else ("TEST_BOUNDARY_UNAVAILABLE",),
            {"test_only": True, "network": "none"},
        )

    def execute(self, source, request):
        result = {
            "adapter_id": request["adapter_id"],
            "engine_id": request["engine_id"],
            "action": request["action"],
            "mode": "READ_ONLY_SYNTHESIZED_V1",
        }
        second = dict(result)
        if self.mismatch:
            second["mode"] = "MISMATCH"
        boundary = {
            "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
            "nonce": request["nonce"],
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "candidate_code_executed": self.executed,
            "results": [
                {"status": "COMPLETE", "result": result, "reason": None},
                {"status": "COMPLETE", "result": second, "reason": None},
            ],
        }
        return {
            "provider": self.probe().to_dict(),
            "boundary_result": boundary,
            "exit_code": 0,
            "elapsed_seconds": 0.001,
            "timed_out": False,
            "stdout_sha256": hashlib.sha256(b"result").hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "command_policy": {"network": "none", "host_mounts": False},
        }


class FakePodman(PodmanMachineRuntimeProvider):
    def __init__(self, policy, runtime_root, responses, environ):
        super().__init__(policy, runtime_root, environ=environ)
        self.executable = "podman"
        self.responses = list(responses)

    def _run(self, args, **kwargs):
        return self.responses.pop(0)


class Phase9Tests(unittest.TestCase):
    def candidate_record(self, td):
        service = AdapterSynthesisService(ROOT, Path(td))
        proposal = service.onboarding.build_proposal(candidate(), persist=True)
        adapter_id = proposal["executor_registry_patch"][0]["adapter_id"]
        record = service.build_candidate(
            Path(proposal["runtime_path"]), adapter_id, persist=True
        )
        return record

    def test_runtime_policy_is_conditional_fail_closed(self):
        policy = load("isolated_runtime_policy_v1.json")
        self.assertEqual(policy["status"], "ACTIVE_CONDITIONAL")
        self.assertTrue(policy["fail_closed"])
        self.assertEqual(policy["allowed_risk"], ["LOW"])

    def test_runtime_policy_forbids_auto_install_and_pull(self):
        policy = load("isolated_runtime_policy_v1.json")
        self.assertFalse(policy["automatic_provider_install"])
        self.assertFalse(policy["automatic_image_pull"])
        self.assertEqual(policy["podman"]["pull_policy"], "never")

    def test_level3_policy_bounded_to_one_task_and_three_repairs(self):
        policy = load("level3_autonomous_cycle_policy_v1.json")
        self.assertEqual(policy["allowed_risk"], ["LOW"])
        self.assertEqual(policy["max_tasks_per_invocation"], 1)
        self.assertEqual(policy["max_repair_attempts"], 3)

    def test_level3_policy_blocks_medium_high_critical(self):
        policy = load("level3_autonomous_cycle_policy_v1.json")
        self.assertEqual(policy["medium_risk"], "ESCALATE")
        self.assertEqual(policy["high_risk"], "DENY")
        self.assertEqual(policy["critical_risk"], "DENY")

    def test_level3_policy_preserves_repository_and_activation_boundaries(self):
        policy = load("level3_autonomous_cycle_policy_v1.json")
        self.assertFalse(policy["repository"]["write_during_runtime_proof"])
        self.assertFalse(policy["handoff"]["automatic_activation"])
        self.assertFalse(policy["handoff"]["automatic_phase7_transaction"])

    def test_provider_order_is_open_source_first(self):
        policy = load("isolated_runtime_policy_v1.json")
        self.assertEqual(
            policy["provider_order"][0], "containers.podman.machine.rootless"
        )

    def test_open_source_review_has_primary_and_fallback(self):
        review = load("open_source_level3_isolated_runtime_review_v1.json")
        self.assertEqual(review["primary"]["decision"], "CONDITIONAL_ADMISSION")
        self.assertEqual(review["fallback"]["decision"], "CONDITIONAL_ADMISSION")
        self.assertFalse(review["phase9_decision"]["automatic_download"])

    def test_disabled_provider_denies_execution(self):
        provider = DisabledRuntimeProvider("test")
        self.assertFalse(provider.probe().execution_enabled)
        with self.assertRaisesRegex(PermissionError, "NO_ACCEPTED_RUNTIME_PROVIDER"):
            provider.execute("pass", {})

    def test_harness_binds_source_nonce_action_and_two_repetitions(self):
        source = "class Demo: pass\n"
        harness = build_adapter_harness(
            source,
            {
                "action": "research.inspect",
                "class_name": "Demo",
                "nonce": "abc",
                "repetitions": 2,
            },
        )
        self.assertIn(hashlib.sha256(source.encode()).hexdigest(), harness)
        self.assertIn("NONCE = 'abc'", harness)
        self.assertIn("REPETITIONS = 2", harness)

    def test_windows_sandbox_config_is_hardened(self):
        provider = WindowsSandboxRuntimeProvider(
            load("isolated_runtime_policy_v1.json"), Path("runtime")
        )
        xml = provider.build_wsb_config(Path("C:/input"), Path("C:/output"), Path("C:/python"))
        for item in (
            "<Networking>Disable</Networking>",
            "<ClipboardRedirection>Disable</ClipboardRedirection>",
            "<PrinterRedirection>Disable</PrinterRedirection>",
            "<VGpu>Disable</VGpu>",
            "<ProtectedClient>Enable</ProtectedClient>",
        ):
            self.assertIn(item, xml)

    def test_windows_sandbox_input_and_python_are_read_only(self):
        provider = WindowsSandboxRuntimeProvider(
            load("isolated_runtime_policy_v1.json"), Path("runtime")
        )
        xml = provider.build_wsb_config(Path("C:/input"), Path("C:/output"), Path("C:/python"))
        self.assertEqual(xml.count("<ReadOnly>true</ReadOnly>"), 2)
        self.assertEqual(xml.count("<ReadOnly>false</ReadOnly>"), 1)
        script = provider.build_run_script("python.exe")
        result_write = script.index("WriteAllText($resultTmp")
        result_publish = script.index("Move($resultTmp,$result)")
        wrapper_write = script.index("WriteAllText($wrapperTmp")
        wrapper_publish = script.index("Move($wrapperTmp,$wrapperPath)")
        self.assertLess(result_write, result_publish)
        self.assertLess(result_publish, wrapper_write)
        self.assertLess(wrapper_write, wrapper_publish)

    def test_podman_requires_digest_bound_image(self):
        policy = load("isolated_runtime_policy_v1.json")
        provider = PodmanMachineRuntimeProvider(
            policy, Path("runtime"), environ={"PHOENIX_PHASE9_PODMAN_IMAGE": "python:3"}
        )
        probe = provider.probe()
        self.assertIn("PODMAN_IMAGE_NOT_DIGEST_BOUND", probe.reasons)

    def test_podman_command_contains_all_isolation_flags(self):
        policy = load("isolated_runtime_policy_v1.json")
        provider = PodmanMachineRuntimeProvider(policy, Path("runtime"), environ={})
        provider.executable = "podman"
        command = provider.execution_command("python@sha256:" + "a" * 64)
        joined = " ".join(command)
        for flag in (
            "--pull=never", "--network=none", "--read-only", "--cap-drop=all",
            "--security-opt=no-new-privileges", "--pids-limit",
        ):
            self.assertIn(flag, joined)

    def test_podman_probe_accepts_rootless_local_digest(self):
        digest = "a" * 64
        image = "localhost/phoenix@sha256:" + digest
        ok = lambda value: subprocess.CompletedProcess([], 0, value, "")
        provider = FakePodman(
            load("isolated_runtime_policy_v1.json"),
            Path("runtime"),
            [ok("{}"), ok(json.dumps({"host": {"os": "linux", "security": {"rootless": True}}})), ok(json.dumps({"Digest": "sha256:" + digest}))],
            {"PHOENIX_PHASE9_PODMAN_IMAGE": image},
        )
        probe = provider.probe()
        self.assertTrue(probe.execution_enabled)
        self.assertTrue(probe.security_boundary)

    def test_phase9_versions_advance(self):
        self.assertGreaterEqual(load("autonomy_policy_v2.json")["version"], "2.6.0")
        self.assertGreaterEqual(load("engine_registry_v1.json")["version"], "1.7.0")
        self.assertGreaterEqual(load("capability_executor_registry_v1.json")["version"], "1.4.0")
        self.assertGreaterEqual(load("future_engine_admission_contract_v1.json")["version"], "1.5.0")

    def test_level3_engine_and_adapter_are_gateway_bound(self):
        engines = load("engine_registry_v1.json")["engines"]
        engine = [x for x in engines if x["engine_id"] == "autonomy.level3_cycle"][0]
        self.assertTrue(engine["gateway_required"])
        self.assertEqual(engine["allowed_path_roots"], ["runtime://level3_cycle/"])
        adapters = load("capability_executor_registry_v1.json")["adapters"]
        adapter = [x for x in adapters if x["adapter_id"] == "builtin.level3.cycle.internal"][0]
        self.assertFalse(adapter["plan_dispatchable"])

    def test_registry_coverage_remains_complete(self):
        report = UniversalCapabilityExecutorRegistry.from_repo(ROOT).coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"], report["covered_engine_actions"])

    def test_unavailable_boundary_blocks_before_execution(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider(available=False)
            )
            with self.assertRaisesRegex(PermissionError, "SECURITY_BOUNDARY_REQUIRED"):
                service.execute_candidate(Path(record["runtime_path"]), "research.inspect")

    def test_action_outside_candidate_scope_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider()
            )
            with self.assertRaisesRegex(PermissionError, "ACTION_SCOPE_DENY"):
                service.execute_candidate(Path(record["runtime_path"]), "qa.execute")

    def test_deterministic_runtime_mismatch_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider(mismatch=True)
            )
            with self.assertRaisesRegex(PermissionError, "DETERMINISTIC_RUNTIME_REPLAY_FAILED"):
                service.execute_candidate(Path(record["runtime_path"]), "research.inspect")

    def test_provider_must_prove_candidate_execution(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider(executed=False)
            )
            with self.assertRaisesRegex(PermissionError, "EXECUTION_NOT_PROVEN"):
                service.execute_candidate(Path(record["runtime_path"]), "research.inspect")

    def test_level3_attestation_passes_and_preserves_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider()
            )
            att = service.execute_candidate(Path(record["runtime_path"]), "research.inspect")
            self.assertEqual(att["status"], "LEVEL3_LOW_RISK_RUNTIME_PROOF_PASS")
            self.assertEqual(att["deterministic_runtime_replay"], "PASS")
            self.assertFalse(att["repository_write_performed"])
            self.assertFalse(att["repository_commit_created"])
            self.assertFalse(att["repository_push_performed"])
            self.assertFalse(att["automatic_activation"])
            self.assertTrue(att["governed_phase7_handoff_eligible"])

    def test_attestation_hmac_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider()
            )
            att = service.execute_candidate(Path(record["runtime_path"]), "research.inspect")
            restarted = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider()
            )
            loaded = restarted.load_attestation(Path(att["runtime_path"]))
            self.assertEqual(loaded["attestation_id"], att["attestation_id"])

    def test_attestation_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider()
            )
            att = service.execute_candidate(Path(record["runtime_path"]), "research.inspect")
            path = Path(att["runtime_path"])
            obj = json.loads(path.read_text())
            obj["automatic_activation"] = True
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "HMAC"):
                service.load_attestation(path)

    def test_gateway_audit_records_phase9_attestation_write(self):
        with tempfile.TemporaryDirectory() as td:
            record = self.candidate_record(td)
            service = BoundedLevel3CycleService(
                ROOT, Path(td), provider=FakeBoundaryProvider()
            )
            service.execute_candidate(Path(record["runtime_path"]), "research.inspect")
            audit = Path(td) / "gateway" / "audit_v1.jsonl"
            self.assertIn("autonomy.level3.cycle.attestation.write", audit.read_text())

    def test_attestation_schema_is_draft_2020_12(self):
        schema = load("level3_cycle_attestation_v1.schema.json")
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIn("repository_write_performed", schema["required"])

    def test_policy_bundle_binds_phase9_policies(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in (
            "isolated_runtime_policy_v1.json",
            "level3_autonomous_cycle_policy_v1.json",
        ):
            self.assertTrue(manifest["files"][name]["required"])
            self.assertRegex(manifest["files"][name]["sha256"], r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
