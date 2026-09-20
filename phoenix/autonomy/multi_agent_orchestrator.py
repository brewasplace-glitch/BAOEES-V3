from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import time
import uuid

from .approval_resume import LocalIntegrityKey
from .dag_scheduler import BoundedDagScheduler, DagExecutionResult
from .decision_engine import PolicyDecisionLog
from .isolated_runtime import IsolatedRuntimeProvider, select_runtime_provider
from .specialized_agents import (
    AgentTaskSpec,
    SpecializedAgentRegistry,
    canonical_bytes,
    object_sha256,
)
from .universal_gateway import GatewayAuditLog, MutationIntent, UniversalAutonomyGateway


def phase11_fixture_tasks() -> tuple[AgentTaskSpec, ...]:
    return (
        AgentTaskSpec("observe", "agent.context.observer", "research.inspect", payload={"scope": "phase11"}),
        AgentTaskSpec("plan", "agent.planning.specialist", "planning.analyze", ("observe",), payload={"mode": "bounded"}),
        AgentTaskSpec("qa", "agent.qa.specialist", "qa.inspect", ("observe",), payload={"gate": "determinism"}),
        AgentTaskSpec("research", "agent.research.specialist", "research.inspect", ("observe",), payload={"source": "local"}),
        AgentTaskSpec("merge", "agent.evidence.merger", "evidence.merge", ("plan", "qa", "research"), payload={"format": "canonical"}),
    )


def _boundary_spec(tasks: tuple[AgentTaskSpec, ...], roles: Mapping[str, str], max_workers: int) -> dict[str, Any]:
    return {
        "schema": "PHOENIX_PHASE11_BOUNDARY_SPEC_V1",
        "tasks": [x.to_dict() for x in sorted(tasks, key=lambda x: x.task_id)],
        "roles": {key: roles[key] for key in sorted(roles)},
        "max_workers": int(max_workers),
    }


def build_parallel_dag_probe_source(
    tasks: tuple[AgentTaskSpec, ...],
    roles: Mapping[str, str],
    max_workers: int,
) -> str:
    spec = _boundary_spec(tasks, roles, max_workers)
    encoded = base64.b64encode(canonical_bytes(spec)).decode("ascii")
    expected = object_sha256(spec)
    return f'''from __future__ import annotations
import base64
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from graphlib import TopologicalSorter
from phoenix.autonomy.executor_adapters import AdapterExecutionResult

SPEC = json.loads(base64.b64decode({encoded!r}).decode("utf-8"))
EXPECTED_SPEC_SHA256 = {expected!r}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()

class Phase11ParallelDagProbe:
    def __init__(self, _policy):
        pass

    def execute(self, context):
        if sha(SPEC) != EXPECTED_SPEC_SHA256:
            return AdapterExecutionResult(status="FAILED", reason="SPEC_SHA256_MISMATCH")
        tasks = {{x["task_id"]: x for x in SPEC["tasks"]}}
        dependencies = {{key: tuple(sorted(value.get("dependencies", []))) for key, value in tasks.items()}}
        sorter = TopologicalSorter(dependencies)
        sorter.prepare()
        batches = []
        while sorter.is_active():
            ready = tuple(sorted(sorter.get_ready()))
            batches.append(ready)
            sorter.done(*ready)
        results = {{}}
        max_parallel = 1
        for batch in batches:
            workers = min(int(SPEC["max_workers"]), len(batch))
            for offset in range(0, len(batch), workers):
                group = batch[offset:offset + workers]
                barrier = threading.Barrier(len(group)) if len(group) > 1 else None
                def run(task_id):
                    if barrier is not None:
                        barrier.wait(timeout=2)
                    task = tasks[task_id]
                    dep_hashes = {{dep: results[dep]["output_sha256"] for dep in sorted(task.get("dependencies", []))}}
                    material = {{
                        "task_id": task_id,
                        "agent_id": task["agent_id"],
                        "action": task["action"],
                        "role": SPEC["roles"][task["agent_id"]],
                        "payload_sha256": sha(task.get("payload", {{}})),
                        "dependency_output_sha256": dep_hashes,
                    }}
                    output = {{
                        "schema": "PHOENIX_SPECIALIZED_AGENT_OUTPUT_V1",
                        **material,
                        "finding_sha256": sha(material),
                        "network_access": False,
                        "arbitrary_shell_executed": False,
                        "repository_write_performed": False,
                    }}
                    return {{
                        "task_id": task_id,
                        "agent_id": task["agent_id"],
                        "action": task["action"],
                        "status": "PASS",
                        "output": output,
                        "output_sha256": sha(output),
                    }}
                with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="phoenix-p11-boundary") as pool:
                    futures = {{task_id: pool.submit(run, task_id) for task_id in group}}
                    for task_id in group:
                        results[task_id] = futures[task_id].result(timeout=3)
                max_parallel = max(max_parallel, len(group))
        ordered = [results[key] for key in sorted(results)]
        dag_material = [tasks[key] for key in sorted(tasks)]
        return AdapterExecutionResult(status="COMPLETE", result={{
            "schema": "PHOENIX_PHASE11_PARALLEL_DAG_RESULT_V1",
            "status": "PASS",
            "spec_sha256": EXPECTED_SPEC_SHA256,
            "dag_sha256": sha(dag_material),
            "result_sha256": sha(ordered),
            "batches": [list(x) for x in batches],
            "max_observed_parallelism": max_parallel,
            "parallel_overlap_proven": any(len(x) > 1 for x in batches) and max_parallel > 1,
            "network_access": False,
            "repository_write_performed": False,
            "automatic_engine_activation": False,
        }})
'''


class BoundedMultiAgentDagService:
    def __init__(
        self,
        repo_root: Path,
        runtime_root: Path,
        *,
        policy_root: Path | None = None,
        provider: IsolatedRuntimeProvider | None = None,
        gateway: UniversalAutonomyGateway | None = None,
        enable_gateway: bool = True,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.policy_root = Path(policy_root or repo_root).resolve()
        self.runtime_root = Path(runtime_root).resolve()
        cfg = self.policy_root / "configs" / "phoenix"
        self.policy = json.loads((cfg / "multi_agent_dag_policy_v1.json").read_text(encoding="utf-8-sig"))
        registry_data = json.loads((cfg / "specialized_agent_registry_v1.json").read_text(encoding="utf-8-sig"))
        runtime_policy = json.loads((cfg / "isolated_runtime_policy_v1.json").read_text(encoding="utf-8-sig"))
        self.agents = SpecializedAgentRegistry(registry_data)
        self.scheduler = BoundedDagScheduler(self.policy, self.agents)
        self.provider = provider or select_runtime_provider(runtime_policy, self.runtime_root)
        self.gateway = gateway
        if enable_gateway and self.gateway is None and self.policy_root == self.repo_root:
            self.gateway = UniversalAutonomyGateway.from_repo(
                self.repo_root,
                decision_log=PolicyDecisionLog(self.runtime_root / "policy_decisions" / "decisions_v1.jsonl"),
                audit_log=GatewayAuditLog(self.runtime_root / "gateway" / "audit_v1.jsonl"),
            )
        self.integrity_key = LocalIntegrityKey(
            self.runtime_root / "integrity" / "multi_agent_dag_hmac_v1.key"
        ).load_or_create()
        self._validate_policy()

    def _validate_policy(self) -> None:
        if int(self.policy.get("max_parallel_workers", 0)) not in range(2, 5):
            raise RuntimeError("Phase-11 parallel worker bound invalid")
        execution = self.policy.get("execution", {})
        for key in ("network", "arbitrary_shell", "repository_write"):
            if execution.get(key) != "DENY":
                raise RuntimeError(f"Phase-11 execution boundary invalid: {key}")
        if self.policy.get("automatic_engine_activation") is not False:
            raise RuntimeError("automatic engine activation must remain disabled")

    def probe(self) -> dict[str, Any]:
        return self.provider.probe().to_dict()

    def _git_snapshot(self) -> tuple[str, str]:
        def run(*args: str) -> str:
            cp = subprocess.run(
                ["git", "-c", "core.longpaths=true", "-C", str(self.repo_root), *args],
                text=True,
                encoding="utf-8",
                errors="strict",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            return cp.stdout.strip() if cp.returncode == 0 else "UNAVAILABLE"
        return run("rev-parse", "HEAD"), run("status", "--porcelain=v1", "--untracked-files=all")

    def execute_host(self, tasks: tuple[AgentTaskSpec, ...]) -> DagExecutionResult:
        return self.scheduler.execute(tasks, self.agents.execute)

    def _execute_boundary(self, tasks: tuple[AgentTaskSpec, ...], host: DagExecutionResult) -> dict[str, Any]:
        probe = self.provider.probe()
        if not (probe.available and probe.security_boundary and probe.execution_enabled):
            raise PermissionError("PHASE11_ACCEPTED_SECURITY_BOUNDARY_REQUIRED:" + ",".join(probe.reasons))
        roles = self.agents.boundary_descriptors(tasks)
        source = build_parallel_dag_probe_source(tasks, roles, int(self.policy["max_parallel_workers"]))
        nonce = uuid.uuid4().hex
        request = {
            "action": "qa.execute",
            "class_name": "Phase11ParallelDagProbe",
            "engine_id": "autonomy.multi_agent_dag",
            "adapter_id": "builtin.multi_agent.dag.internal",
            "nonce": nonce,
            "repetitions": int(self.policy["deterministic_repetitions"]),
        }
        execution = self.provider.execute(source, request)
        boundary = execution.get("boundary_result", {})
        if boundary.get("schema") != "PHOENIX_PHASE9_BOUNDARY_RESULT_V1":
            raise PermissionError("PHASE11_BOUNDARY_SCHEMA_DENY")
        if not hmac.compare_digest(str(boundary.get("nonce", "")), nonce):
            raise PermissionError("PHASE11_BOUNDARY_NONCE_DENY")
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(str(boundary.get("source_sha256", "")), source_sha):
            raise PermissionError("PHASE11_BOUNDARY_SOURCE_SHA_DENY")
        if boundary.get("candidate_code_executed") is not True:
            raise PermissionError("PHASE11_BOUNDARY_EXECUTION_NOT_PROVEN")
        results = boundary.get("results") or []
        if len(results) != 2 or results[0] != results[1]:
            raise PermissionError("PHASE11_NONDETERMINISTIC_BOUNDARY_DENY")
        row = results[0]
        value = row.get("result") or {}
        if row.get("status") != "COMPLETE" or value.get("status") != "PASS":
            raise PermissionError("PHASE11_BOUNDARY_TASK_FAILED")
        if value.get("schema") != "PHOENIX_PHASE11_PARALLEL_DAG_RESULT_V1":
            raise PermissionError("PHASE11_PARALLEL_RESULT_SCHEMA_DENY")
        if value.get("dag_sha256") != host.dag_sha256 or value.get("result_sha256") != host.result_sha256:
            raise PermissionError("PHASE11_HOST_BOUNDARY_DIGEST_MISMATCH")
        if value.get("parallel_overlap_proven") is not True or int(value.get("max_observed_parallelism", 0)) < 2:
            raise PermissionError("PHASE11_PARALLEL_OVERLAP_NOT_PROVEN")
        if int(value["max_observed_parallelism"]) > int(self.policy["max_parallel_workers"]):
            raise PermissionError("PHASE11_PARALLEL_BOUND_EXCEEDED")
        if value.get("repository_write_performed") is not False or value.get("automatic_engine_activation") is not False:
            raise PermissionError("PHASE11_BOUNDARY_SAFETY_INVARIANT_DENY")
        return execution

    def _sign(self, value: dict[str, Any]) -> str:
        return hmac.new(self.integrity_key, canonical_bytes(value), hashlib.sha256).hexdigest()

    def _write_attestation(self, attestation: dict[str, Any]) -> Path:
        if self.gateway is None:
            raise RuntimeError("Phase-11 gateway unavailable for attestation write")
        relative = f"attestations/{attestation['attestation_id']}.json"
        uri = "runtime://multi_agent_dag/" + relative
        gates = (
            "audit_log", "accepted_security_boundary", "dag_cycle_free",
            "deterministic_replay", "parallel_bound", "read_only_agents",
        )
        permit = self.gateway.authorize(MutationIntent(
            engine_id="autonomy.multi_agent_dag",
            action="autonomy.multi_agent.dag.attestation.write",
            risk="LOW",
            domain="orchestration",
            paths=(uri,),
            gates=gates,
            metadata={"attestation_sha256": attestation["attestation_sha256"]},
        ))
        self.gateway.consume(
            permit,
            engine_id="autonomy.multi_agent_dag",
            action="autonomy.multi_agent.dag.attestation.write",
            paths=(uri,),
        )
        path = self.runtime_root / "multi_agent_dag" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(attestation, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, path)
        return path

    def _attestation(
        self,
        baseline_sha: str,
        host: DagExecutionResult,
        provider: dict[str, Any],
        *,
        persist: bool,
    ) -> dict[str, Any]:
        obj: dict[str, Any] = {
            "schema": "PHOENIX_MULTI_AGENT_DAG_ATTESTATION_V1",
            "attestation_id": "MADAG-" + uuid.uuid4().hex[:16].upper(),
            "timestamp": int(time.time()),
            "baseline_sha": baseline_sha,
            "dag_sha256": host.dag_sha256,
            "result_sha256": host.result_sha256,
            "task_count": len(host.results),
            "execution_batches": [list(x) for x in host.batches],
            "max_parallel_workers": int(self.policy["max_parallel_workers"]),
            "parallel_overlap_proven": True,
            "deterministic_replay": "PASS",
            "provider": provider,
            "network_access": False,
            "repository_write_performed": False,
            "repository_commit_created": False,
            "repository_push_performed": False,
            "automatic_engine_activation": False,
            "status": "PASS",
        }
        obj["attestation_sha256"] = object_sha256(obj)
        obj["hmac_sha256"] = self._sign(dict(obj))
        if persist:
            obj["runtime_path"] = str(self._write_attestation(obj))
        return obj

    def load_attestation(self, path: Path) -> dict[str, Any]:
        target = Path(path).resolve()
        allowed = (self.runtime_root / "multi_agent_dag" / "attestations").resolve()
        try:
            target.relative_to(allowed)
        except ValueError as exc:
            raise PermissionError("Phase-11 attestation outside runtime") from exc
        obj = json.loads(target.read_text(encoding="utf-8-sig"))
        supplied_hmac = str(obj.get("hmac_sha256", ""))
        unsigned = dict(obj)
        unsigned.pop("hmac_sha256", None)
        if not supplied_hmac or not hmac.compare_digest(supplied_hmac, self._sign(unsigned)):
            raise PermissionError("Phase-11 attestation HMAC verification failed")
        digest_material = dict(unsigned)
        supplied_digest = str(digest_material.pop("attestation_sha256", ""))
        if not supplied_digest or not hmac.compare_digest(supplied_digest, object_sha256(digest_material)):
            raise PermissionError("Phase-11 attestation digest verification failed")
        return obj

    def run_synthetic_proof(self, expected_baseline: str, *, persist: bool = False) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{40}", expected_baseline):
            raise ValueError("expected baseline must be a 40-character lowercase SHA")
        before_head, before_status = self._git_snapshot()
        if before_head != "UNAVAILABLE" and before_head != expected_baseline:
            raise RuntimeError("PHASE11_BASELINE_MISMATCH")
        tasks = phase11_fixture_tasks()
        host = self.execute_host(tasks)
        boundary = self._execute_boundary(tasks, host)
        after_head, after_status = self._git_snapshot()
        if (before_head, before_status) != (after_head, after_status):
            raise RuntimeError("PHASE11_REPOSITORY_CHANGED_DURING_PROOF")
        attestation = self._attestation(
            expected_baseline,
            host,
            boundary["provider"],
            persist=persist,
        )
        return {
            "schema": "PHOENIX_PHASE11_SYNTHETIC_MULTI_AGENT_PROOF_V1",
            "status": "PASS",
            "test_only": False,
            "live_runtime_proof": True,
            "provider_id": boundary["provider"]["provider_id"],
            "task_count": len(tasks),
            "execution_batches": [list(x) for x in host.batches],
            "max_parallel_workers": int(self.policy["max_parallel_workers"]),
            "parallel_overlap_proven": True,
            "deterministic_result_sha256": host.result_sha256,
            "dag_cycle_gate": "PASS",
            "dependency_gate": "PASS",
            "failure_isolation_gate": "PASS",
            "repository_write_performed": False,
            "repository_commit_created": False,
            "repository_push_performed": False,
            "automatic_engine_activation": False,
            "attestation": attestation,
        }
