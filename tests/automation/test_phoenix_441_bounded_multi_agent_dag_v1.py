from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
import hashlib
import json
import subprocess
import sys
import time
import types
import unittest

from phoenix.autonomy import (
    AgentTaskResult,
    AgentTaskSpec,
    BoundedDagScheduler,
    BoundedMultiAgentDagService,
    RuntimeProviderProbe,
    SpecializedAgentRegistry,
    UniversalCapabilityExecutorRegistry,
    build_parallel_dag_probe_source,
    phase11_fixture_tasks,
)


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name: str) -> dict:
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


def repository_baseline() -> str:
    completed = subprocess.run(
        ["git", "-c", "core.longpaths=true", "-C", str(ROOT), "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and len(value) == 40 else "1" * 40


class _Result:
    def __init__(self, status, result=None, reason=None):
        self.status = status
        self.result = result
        self.reason = reason


class FakePhase11Boundary:
    provider_id = "test.only.phase11.parallel_boundary"
    provider_version = "1.0.0"

    def probe(self):
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            True,
            True,
            True,
            (),
            {"test_only": True, "network": "none", "repository_mount": False},
        )

    def execute(self, source, request):
        stub = types.ModuleType("phoenix.autonomy.executor_adapters")
        stub.AdapterExecutionResult = _Result
        old = sys.modules.get("phoenix.autonomy.executor_adapters")
        try:
            sys.modules["phoenix.autonomy.executor_adapters"] = stub
            namespace = {"__name__": "phase11_test_candidate"}
            exec(compile(source, "phase11_candidate.py", "exec"), namespace, namespace)
            adapter = namespace[request["class_name"]](None)
            rows = []
            for _ in range(int(request["repetitions"])):
                item = adapter.execute(None)
                rows.append({"status": item.status, "result": item.result, "reason": item.reason})
        finally:
            if old is None:
                sys.modules.pop("phoenix.autonomy.executor_adapters", None)
            else:
                sys.modules["phoenix.autonomy.executor_adapters"] = old
        return {
            "provider": self.probe().to_dict(),
            "boundary_result": {
                "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
                "nonce": request["nonce"],
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "candidate_code_executed": True,
                "results": rows,
            },
            "exit_code": 0,
            "elapsed_seconds": 0.001,
            "timed_out": False,
            "stdout_sha256": "0" * 64,
            "stderr_sha256": "0" * 64,
            "command_policy": {"network": "none", "test_only": True},
        }


class UnavailableBoundary(FakePhase11Boundary):
    def probe(self):
        return RuntimeProviderProbe("disabled.test", "1.0.0", False, False, False, ("NO_PROVIDER",), {})


class NondeterministicBoundary(FakePhase11Boundary):
    def execute(self, source, request):
        value = super().execute(source, request)
        value["boundary_result"]["results"][1]["result"]["result_sha256"] = "f" * 64
        return value


class Phase11MultiAgentDagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load("multi_agent_dag_policy_v1.json")
        cls.registry_data = load("specialized_agent_registry_v1.json")
        cls.registry = SpecializedAgentRegistry(cls.registry_data)
        cls.scheduler = BoundedDagScheduler(cls.policy, cls.registry)

    def service(self, runtime, provider=None, enable_gateway=False):
        return BoundedMultiAgentDagService(
            ROOT,
            Path(runtime),
            provider=provider or FakePhase11Boundary(),
            enable_gateway=enable_gateway,
        )

    def test_01_policy_schema_active_fail_closed(self):
        self.assertEqual(self.policy["schema"], "PHOENIX_MULTI_AGENT_DAG_POLICY_V1")
        self.assertEqual(self.policy["status"], "ACTIVE_BOUNDED")
        self.assertTrue(self.policy["fail_closed"])

    def test_02_policy_bounds(self):
        self.assertEqual(self.policy["max_tasks_per_dag"], 12)
        self.assertEqual(self.policy["max_parallel_workers"], 3)
        self.assertEqual(self.policy["max_dag_depth"], 5)

    def test_03_policy_denies_effects(self):
        execution = self.policy["execution"]
        self.assertEqual((execution["network"], execution["arbitrary_shell"], execution["repository_write"]), ("DENY",) * 3)

    def test_04_registry_has_five_read_only_agents(self):
        agents = self.registry_data["agents"]
        self.assertEqual(len(agents), 5)
        self.assertTrue(all(x["read_only"] and x["status"] == "ACTIVE" for x in agents))

    def test_05_versions_advance(self):
        self.assertEqual(load("autonomy_policy_v2.json")["version"], "2.8.0")
        self.assertEqual(load("engine_registry_v1.json")["version"], "1.9.0")
        self.assertEqual(load("capability_executor_registry_v1.json")["version"], "1.6.0")
        self.assertEqual(load("future_engine_admission_contract_v1.json")["version"], "1.7.0")

    def test_06_engine_is_gateway_bound(self):
        engine = next(x for x in load("engine_registry_v1.json")["engines"] if x["engine_id"] == "autonomy.multi_agent_dag")
        self.assertTrue(engine["mutation_capable"] and engine["gateway_required"])
        self.assertIn("runtime://multi_agent_dag/", engine["allowed_path_roots"])

    def test_07_executor_registry_coverage(self):
        report = UniversalCapabilityExecutorRegistry.from_repo(ROOT).coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"], report["covered_engine_actions"])

    def test_08_policy_bundle_binds_phase11_files(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in ("multi_agent_dag_policy_v1.json", "specialized_agent_registry_v1.json"):
            self.assertEqual(manifest["files"][name]["sha256"], hashlib.sha256((CFG / name).read_bytes()).hexdigest())

    def test_09_task_round_trip(self):
        task = AgentTaskSpec.from_dict(phase11_fixture_tasks()[0].to_dict())
        self.assertEqual(task, phase11_fixture_tasks()[0])

    def test_10_fixture_batches_are_deterministic(self):
        _, batches = self.scheduler.plan(phase11_fixture_tasks())
        self.assertEqual(batches, (("observe",), ("plan", "qa", "research"), ("merge",)))

    def test_11_unknown_dependency_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze", ("missing",))
        with self.assertRaisesRegex(PermissionError, "UNKNOWN_DEPENDENCY"):
            self.scheduler.plan((task,))

    def test_12_cycle_denied(self):
        tasks = (
            AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze", ("b",)),
            AgentTaskSpec("b", "agent.planning.specialist", "planning.analyze", ("a",)),
        )
        with self.assertRaisesRegex(PermissionError, "DAG_CYCLE"):
            self.scheduler.plan(tasks)

    def test_13_duplicate_id_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze")
        with self.assertRaisesRegex(PermissionError, "DUPLICATE_TASK_ID"):
            self.scheduler.plan((task, task))

    def test_14_self_dependency_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze", ("a",))
        with self.assertRaisesRegex(PermissionError, "SELF_DEPENDENCY"):
            self.scheduler.plan((task,))

    def test_15_non_low_risk_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze", risk="MEDIUM")
        with self.assertRaisesRegex(PermissionError, "NON_LOW_RISK"):
            self.scheduler.plan((task,))

    def test_16_mutating_task_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze", mutating=True)
        with self.assertRaisesRegex(PermissionError, "PARALLEL_MUTATION"):
            self.scheduler.plan((task,))

    def test_17_task_bound_denied(self):
        tasks = tuple(AgentTaskSpec(f"t{x}", "agent.planning.specialist", "planning.analyze") for x in range(13))
        with self.assertRaisesRegex(PermissionError, "TASK_BOUND"):
            self.scheduler.plan(tasks)

    def test_18_dependency_bound_denied(self):
        roots = tuple(AgentTaskSpec(f"r{x}", "agent.planning.specialist", "planning.analyze") for x in range(5))
        leaf = AgentTaskSpec("leaf", "agent.planning.specialist", "planning.analyze", tuple(x.task_id for x in roots))
        with self.assertRaisesRegex(PermissionError, "DEPENDENCY_BOUND"):
            self.scheduler.plan(roots + (leaf,))

    def test_19_fanout_bound_denied(self):
        root = AgentTaskSpec("root", "agent.planning.specialist", "planning.analyze")
        leaves = tuple(AgentTaskSpec(f"l{x}", "agent.planning.specialist", "planning.analyze", ("root",)) for x in range(5))
        with self.assertRaisesRegex(PermissionError, "FANOUT_BOUND"):
            self.scheduler.plan((root,) + leaves)

    def test_20_depth_bound_denied(self):
        tasks = [AgentTaskSpec("d0", "agent.planning.specialist", "planning.analyze")]
        tasks.extend(AgentTaskSpec(f"d{x}", "agent.planning.specialist", "planning.analyze", (f"d{x-1}",)) for x in range(1, 6))
        with self.assertRaisesRegex(PermissionError, "DAG_DEPTH"):
            self.scheduler.plan(tuple(tasks))

    def test_21_payload_bound_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "planning.analyze", payload={"x": "z" * 17000})
        with self.assertRaisesRegex(PermissionError, "PAYLOAD_SIZE"):
            self.scheduler.plan((task,))

    def test_22_unknown_agent_denied(self):
        task = AgentTaskSpec("a", "agent.unknown", "planning.analyze")
        with self.assertRaisesRegex(PermissionError, "UNKNOWN_AGENT"):
            self.scheduler.plan((task,))

    def test_23_unregistered_action_denied(self):
        task = AgentTaskSpec("a", "agent.planning.specialist", "qa.execute")
        with self.assertRaisesRegex(PermissionError, "AGENT_ACTION"):
            self.scheduler.plan((task,))

    def test_24_execution_is_deterministic(self):
        one = self.scheduler.execute(phase11_fixture_tasks(), self.registry.execute)
        two = self.scheduler.execute(phase11_fixture_tasks(), self.registry.execute)
        self.assertEqual((one.dag_sha256, one.result_sha256), (two.dag_sha256, two.result_sha256))

    def test_25_results_merge_in_task_id_order(self):
        result = self.scheduler.execute(phase11_fixture_tasks(), self.registry.execute)
        self.assertEqual([x.task_id for x in result.results], sorted(x.task_id for x in result.results))

    def test_26_dependency_results_are_immutable(self):
        observed = []
        def runner(task, deps):
            observed.append(isinstance(deps, MappingProxyType))
            return self.registry.execute(task, deps)
        self.scheduler.execute(phase11_fixture_tasks(), runner)
        self.assertTrue(all(observed))

    def test_27_merge_binds_dependency_hashes(self):
        result = self.scheduler.execute(phase11_fixture_tasks(), self.registry.execute)
        merge = next(x for x in result.results if x.task_id == "merge")
        self.assertEqual(set(merge.output["dependency_output_sha256"]), {"plan", "qa", "research"})

    def test_28_agent_failure_fails_closed(self):
        def runner(task, deps):
            value = self.registry.execute(task, deps)
            return AgentTaskResult(value.task_id, value.agent_id, value.action, "FAILED" if task.task_id == "plan" else "PASS", value.output, value.output_sha256)
        with self.assertRaisesRegex(RuntimeError, "AGENT_RESULT_DENY"):
            self.scheduler.execute(phase11_fixture_tasks(), runner)

    def test_29_task_timeout_fails_closed(self):
        policy = dict(self.policy)
        policy["max_task_seconds"] = 0.001
        scheduler = BoundedDagScheduler(policy, self.registry)
        def runner(task, deps):
            time.sleep(0.01)
            return self.registry.execute(task, deps)
        with self.assertRaisesRegex(TimeoutError, "TASK_TIMEOUT"):
            scheduler.execute((phase11_fixture_tasks()[0],), runner)

    def test_30_boundary_source_is_digest_bound(self):
        tasks = phase11_fixture_tasks()
        source = build_parallel_dag_probe_source(tasks, self.registry.boundary_descriptors(tasks), 3)
        self.assertIn("EXPECTED_SPEC_SHA256", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("socket", source)

    def test_31_synthetic_proof_passes(self):
        with TemporaryDirectory() as tmp:
            result = self.service(tmp).run_synthetic_proof(repository_baseline())
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["parallel_overlap_proven"])

    def test_32_unavailable_boundary_denied(self):
        with TemporaryDirectory() as tmp, self.assertRaisesRegex(PermissionError, "SECURITY_BOUNDARY_REQUIRED"):
            self.service(tmp, UnavailableBoundary()).run_synthetic_proof(repository_baseline())

    def test_33_nondeterministic_boundary_denied(self):
        with TemporaryDirectory() as tmp, self.assertRaisesRegex(PermissionError, "NONDETERMINISTIC"):
            self.service(tmp, NondeterministicBoundary()).run_synthetic_proof(repository_baseline())

    def test_34_gateway_persist_and_hmac_tamper_denied(self):
        with TemporaryDirectory() as tmp:
            service = self.service(tmp, enable_gateway=True)
            result = service.run_synthetic_proof(repository_baseline(), persist=True)
            path = Path(result["attestation"]["runtime_path"])
            self.assertEqual(service.load_attestation(path)["status"], "PASS")
            value = json.loads(path.read_text(encoding="utf-8"))
            value["status"] = "TAMPERED"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "HMAC"):
                service.load_attestation(path)

    def test_35_future_contract_blocks_phase11_unsafe_patterns(self):
        contract = load("future_engine_admission_contract_v1.json")
        self.assertIn("phase11_parallel_repository_mutation", contract["prohibited_patterns"])
        self.assertFalse(contract["multi_agent_dag_contract"]["automatic_activation"])

    def test_36_open_source_review_and_activation_invariant(self):
        review = load("open_source_multi_agent_dag_review_v1.json")
        self.assertEqual(review["selected_primary"], "python.graphlib.TopologicalSorter")
        self.assertEqual(review["decision"], "EMBED_STDLIB_BOUNDED_SCHEDULER")
        self.assertFalse(self.policy["automatic_engine_activation"])


if __name__ == "__main__":
    unittest.main()
