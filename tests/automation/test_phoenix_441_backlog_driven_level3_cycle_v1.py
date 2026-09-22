from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import subprocess
import sys
import types
import unittest
from unittest import mock

from phoenix.autonomy import (
    BacklogDrivenLevel3CycleService,
    BacklogTask,
    DeterministicBacklogSelector,
    RuntimeProviderProbe,
    UniversalCapabilityExecutorRegistry,
)


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name: str) -> dict:
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command, check=True, text=True, encoding="utf-8", errors="strict",
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def git(root: Path, *args: str) -> str:
    return run(["git", "-c", "core.longpaths=true", "-C", str(root), *args])


class _Result:
    def __init__(self, status, result=None, reason=None):
        self.status = status
        self.result = result
        self.reason = reason


class FakeBoundary:
    provider_id = "test.only.phase12.boundary"
    provider_version = "1.0.0"

    def __init__(self, *, available=True, nondeterministic=False):
        self.available = available
        self.nondeterministic = nondeterministic

    def probe(self):
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            self.available,
            self.available,
            self.available,
            () if self.available else ("NO_TEST_BOUNDARY",),
            {"test_only": True, "network": "none", "repository_mount": False},
        )

    def execute(self, source, request):
        stub = types.ModuleType("phoenix.autonomy.executor_adapters")
        stub.AdapterExecutionResult = _Result
        old = sys.modules.get("phoenix.autonomy.executor_adapters")
        try:
            sys.modules["phoenix.autonomy.executor_adapters"] = stub
            namespace = {"__name__": "phase12_test_candidate"}
            exec(compile(source, "phase12_candidate.py", "exec"), namespace, namespace)
            adapter = namespace[request["class_name"]](None)
            rows = []
            for _ in range(int(request["repetitions"])):
                value = adapter.execute(None)
                rows.append({"status": value.status, "result": value.result, "reason": value.reason})
        finally:
            if old is None:
                sys.modules.pop("phoenix.autonomy.executor_adapters", None)
            else:
                sys.modules["phoenix.autonomy.executor_adapters"] = old
        if self.nondeterministic and len(rows) > 1:
            rows[1] = deepcopy(rows[1])
            rows[1]["result"]["status"] = "TAMPERED"
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


def make_repository(root: Path) -> tuple[Path, str, Path]:
    repo = root / "repo"
    remote = root / "remote.git"
    snapshot = root / "snapshot"
    run(["git", "init", "--bare", str(remote)])
    run(["git", "init", "-b", "project-phoenix", str(repo)])
    git(repo, "config", "user.name", "Phoenix Test")
    git(repo, "config", "user.email", "phoenix@test.invalid")
    (repo / "README.md").write_text("phase12 fixture\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "fixture baseline")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "project-phoenix")
    baseline = git(repo, "rev-parse", "HEAD")
    bundle = root / "backup.bundle"
    git(repo, "bundle", "create", str(bundle), "--all")
    git(repo, "bundle", "verify", str(bundle))
    run(["git", "clone", str(repo), str(snapshot)])
    receipt = root / "receipt.json"
    receipt.write_text(json.dumps({
        "status": "PASS", "baseline": baseline,
        "bundle_verified": True, "snapshot_verified": True,
        "bundle_path": str(bundle), "snapshot_path": str(snapshot),
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
    }), encoding="utf-8")
    return repo, baseline, receipt


def passing_tests(_root: Path) -> dict:
    return {"status": "PASS", "test_count": 340, "output_sha256": "0" * 64}


class Phase12BacklogDrivenLevel3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load("autonomous_backlog_policy_v1.json")
        cls.backlog = load("autonomous_backlog_v1.json")

    def selector(self, policy=None, backlog=None):
        return DeterministicBacklogSelector(policy or self.policy, backlog or self.backlog)

    def service(self, repo, runtime, *, provider=None, executor=passing_tests):
        return BacklogDrivenLevel3CycleService(
            repo, runtime, policy_root=ROOT,
            provider=provider or FakeBoundary(),
            enable_gateway=False, test_only_gateway=True,
            test_executor=executor,
        )

    def second_task(self, **updates):
        task = deepcopy(self.backlog["tasks"][0])
        task.update({
            "task_id": "PHX-L3-CAPABILITY-EVIDENCE-002",
            "priority": 50,
            "output_path": "docs/automation/autonomous_generated/phase12-second.md",
        })
        task.update(updates)
        return task

    def test_01_policy_active_fail_closed(self):
        self.assertEqual(self.policy["schema"], "PHOENIX_AUTONOMOUS_BACKLOG_POLICY_V1")
        self.assertEqual(self.policy["status"], "ACTIVE_BOUNDED")
        self.assertTrue(self.policy["fail_closed"])

    def test_02_one_low_risk_task_only(self):
        self.assertEqual(self.policy["allowed_risk"], ["LOW"])
        self.assertEqual(self.policy["max_tasks_per_invocation"], 1)
        regression = self.policy["regression"]
        self.assertEqual(regression["command_profile"], "PYTHON_UNITTEST_EXPLICIT_ALLOWLIST")
        self.assertEqual(len(regression["test_files"]), 14)
        self.assertEqual(len(regression["test_files"]), len(set(regression["test_files"])))
        self.assertNotIn("*", "".join(regression["test_files"]))

    def test_03_unsafe_automatic_changes_disabled(self):
        for key in ("automatic_source_change", "automatic_dependency_change", "automatic_policy_change", "automatic_registry_change", "automatic_engine_activation"):
            self.assertFalse(self.policy[key])

    def test_04_backlog_contract(self):
        self.assertEqual(self.backlog["schema"], "PHOENIX_AUTONOMOUS_BACKLOG_V1")
        self.assertEqual(len(self.backlog["tasks"]), 1)
        self.assertEqual(self.backlog["tasks"][0]["status"], "READY")

    def test_05_versions_advance(self):
        self.assertEqual(load("autonomy_policy_v2.json")["version"], "3.0.0")
        self.assertEqual(load("engine_registry_v1.json")["version"], "2.1.0")
        self.assertEqual(load("capability_executor_registry_v1.json")["version"], "1.8.0")
        self.assertEqual(load("future_engine_admission_contract_v1.json")["version"], "1.9.0")

    def test_06_executor_registry_coverage(self):
        report = UniversalCapabilityExecutorRegistry.from_repo(ROOT).coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"], report["covered_engine_actions"])

    def test_07_engine_gateway_binding(self):
        engine = next(x for x in load("engine_registry_v1.json")["engines"] if x["engine_id"] == "autonomy.backlog_cycle")
        self.assertTrue(engine["mutation_capable"] and engine["gateway_required"])
        self.assertIn("worktree://phase12/", engine["allowed_path_roots"])

    def test_08_policy_bundle_binds_backlog(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in ("autonomous_backlog_policy_v1.json", "autonomous_backlog_v1.json"):
            self.assertEqual(manifest["files"][name]["sha256"], hashlib.sha256((CFG / name).read_bytes()).hexdigest())

    def test_09_task_parse_and_hash(self):
        task = BacklogTask.from_dict(self.backlog["tasks"][0])
        self.assertEqual(task.task_id, "PHX-L3-CAPABILITY-EVIDENCE-001")
        self.assertRegex(task.sha256, r"^[a-f0-9]{64}$")

    def test_10_highest_priority_selected(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].append(self.second_task())
        with TemporaryDirectory() as td:
            selected = self.selector(backlog=backlog).select(Path(td))
        self.assertEqual(selected.task.task_id, "PHX-L3-CAPABILITY-EVIDENCE-001")

    def test_11_task_id_breaks_priority_tie(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].append(self.second_task(priority=100))
        with TemporaryDirectory() as td:
            selected = self.selector(backlog=backlog).select(Path(td))
        self.assertEqual(selected.task.task_id, "PHX-L3-CAPABILITY-EVIDENCE-001")

    def test_12_completed_task_is_skipped(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].append(self.second_task())
        with TemporaryDirectory() as td:
            selected = self.selector(backlog=backlog).select(Path(td), completed_task_ids=("PHX-L3-CAPABILITY-EVIDENCE-001",))
        self.assertEqual(selected.task.task_id, "PHX-L3-CAPABILITY-EVIDENCE-002")

    def test_13_existing_output_is_skipped(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].append(self.second_task())
        with TemporaryDirectory() as td:
            output = Path(td) / self.backlog["tasks"][0]["output_path"]
            output.parent.mkdir(parents=True)
            output.write_text("exists\n", encoding="utf-8")
            selected = self.selector(backlog=backlog).select(Path(td))
        self.assertEqual(selected.task.task_id, "PHX-L3-CAPABILITY-EVIDENCE-002")

    def test_14_no_eligible_task_fails_closed(self):
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, "NO_ELIGIBLE"):
                self.selector().select(Path(td), completed_task_ids=("PHX-L3-CAPABILITY-EVIDENCE-001",))

    def test_15_duplicate_task_id_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].append(deepcopy(backlog["tasks"][0]))
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE"):
            self.selector(backlog=backlog)

    def test_16_non_low_risk_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["risk"] = "MEDIUM"
        with self.assertRaisesRegex(PermissionError, "RISK"):
            self.selector(backlog=backlog)

    def test_17_unknown_task_type_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["task_type"] = "SOURCE_CODE"
        with self.assertRaisesRegex(PermissionError, "TASK_TYPE"):
            self.selector(backlog=backlog)

    def test_18_unknown_action_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["action"] = "source.modify"
        with self.assertRaisesRegex(PermissionError, "ACTION"):
            self.selector(backlog=backlog)

    def test_19_output_scope_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["output_path"] = "phoenix/autonomy/unsafe.md"
        with self.assertRaisesRegex(PermissionError, "OUTPUT_SCOPE"):
            self.selector(backlog=backlog)

    def test_20_output_extension_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["output_path"] = "docs/automation/autonomous_generated/unsafe.py"
        with self.assertRaisesRegex(PermissionError, "OUTPUT_EXTENSION"):
            self.selector(backlog=backlog)

    def test_21_unknown_generator_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["generator"] = "external.plugin"
        with self.assertRaisesRegex(PermissionError, "GENERATOR"):
            self.selector(backlog=backlog)

    def test_22_non_lane_a_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["promotion_lane"] = "LOW_EXECUTABLE_APPROVAL_BOUND"
        with self.assertRaisesRegex(PermissionError, "PROMOTION_LANE"):
            self.selector(backlog=backlog)

    def test_23_priority_bound_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["priority"] = 1001
        with self.assertRaisesRegex(PermissionError, "PRIORITY"):
            self.selector(backlog=backlog)

    def test_24_selector_is_repeatable(self):
        with TemporaryDirectory() as td:
            one = self.selector().select(Path(td)).to_dict()
            two = self.selector().select(Path(td)).to_dict()
        self.assertEqual(one, two)

    def test_25_missing_backup_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, _ = make_repository(Path(td))
            with self.assertRaisesRegex(RuntimeError, "BACKUP_RECEIPT_REQUIRED"):
                self.service(repo, Path(td) / "runtime").run_cycle(baseline, Path(td) / "missing.json", persist=False, test_only=True)

    def test_26_backup_baseline_mismatch_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            value = json.loads(receipt.read_text())
            value["baseline"] = "0" * 40
            receipt.write_text(json.dumps(value))
            with self.assertRaisesRegex(RuntimeError, "BACKUP_BASELINE"):
                self.service(repo, Path(td) / "runtime").run_cycle(baseline, receipt, persist=False, test_only=True)

    def test_27_dirty_main_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            (repo / "dirty.txt").write_text("dirty\n")
            with self.assertRaisesRegex(RuntimeError, "main_worktree_dirty"):
                self.service(repo, Path(td) / "runtime").run_cycle(baseline, receipt, persist=False, test_only=True)

    def test_28_unavailable_boundary_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            with self.assertRaisesRegex(PermissionError, "SECURITY_BOUNDARY_REQUIRED"):
                self.service(repo, Path(td) / "runtime", provider=FakeBoundary(available=False)).run_cycle(baseline, receipt, persist=False, test_only=True)

    def test_29_nondeterministic_boundary_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            with self.assertRaisesRegex(PermissionError, "NONDETERMINISTIC"):
                self.service(repo, Path(td) / "runtime", provider=FakeBoundary(nondeterministic=True)).run_cycle(baseline, receipt, persist=False, test_only=True)

    def test_30_failed_regression_denies_promotion(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            failed = lambda _root: {"status": "FAILED", "test_count": 339}
            with self.assertRaisesRegex(RuntimeError, "TEST_GATE"):
                self.service(repo, Path(td) / "runtime", executor=failed).run_cycle(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(git(repo, "rev-parse", "HEAD"), baseline)

    def test_31_real_git_backed_cycle_passes(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            (repo / "README.md").write_bytes(b"phase12 fixture\r\n")
            config = Path(td) / "windows-global-gitconfig"
            config.write_text("[core]\n\tautocrlf = true\n\teol = native\n", encoding="utf-8", newline="\n")
            with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
                git(repo, "add", "README.md")
                service = self.service(repo, Path(td) / "runtime")
                with mock.patch.object(
                    service.promoter,
                    "_paths",
                    return_value=(
                        ("docs/automation/autonomous_generated/phase12-proof.md",),
                        ("bib/PHOENIX_AUTO_SYNC/BIB_BASELINE.md",),
                    ),
                ):
                    self.assertEqual(
                        service._promotion_paths(baseline, "candidate"),
                        (
                            "docs/automation/autonomous_generated/phase12-proof.md",
                            "bib/PHOENIX_AUTO_SYNC/BIB_BASELINE.md",
                        ),
                    )
                self.assertTrue(service.worktrees.snapshot().clean)
                candidate = service.worktrees.create_candidate(
                    "crlf-proof", baseline, parent=Path(td) / "newline-proof"
                )
                try:
                    self.assertEqual((candidate.path / "README.md").read_bytes(), b"phase12 fixture\n")
                finally:
                    service.worktrees.cleanup(candidate)
                result = service.run_cycle(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["test_count"], 340)
            self.assertTrue(result["repository_push_performed"])

    def test_32_promoted_output_and_remote_match(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_cycle(baseline, receipt, persist=False, test_only=True)
            self.assertTrue((repo / self.backlog["tasks"][0]["output_path"]).is_file())
            self.assertEqual(git(repo, "rev-parse", "HEAD"), result["promoted_commit"])
            self.assertEqual(git(repo, "rev-parse", "origin/project-phoenix"), result["promoted_commit"])

    def test_33_second_cycle_has_no_eligible_task(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            first = self.service(repo, Path(td) / "runtime")
            result = first.run_cycle(baseline, receipt, persist=False, test_only=True)
            new_head = result["promoted_commit"]
            bundle = Path(td) / "backup2.bundle"
            git(repo, "bundle", "create", str(bundle), "--all")
            snapshot = Path(td) / "snapshot2"
            run(["git", "clone", str(repo), str(snapshot)])
            receipt2 = Path(td) / "receipt2.json"
            receipt2.write_text(json.dumps({"status":"PASS","baseline":new_head,"bundle_verified":True,"snapshot_verified":True,"bundle_path":str(bundle),"snapshot_path":str(snapshot)}))
            with self.assertRaisesRegex(RuntimeError, "NO_ELIGIBLE"):
                self.service(repo, Path(td) / "runtime2").run_cycle(new_head, receipt2, persist=False, test_only=True)

    def test_34_completion_preserves_activation_boundary(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_cycle(baseline, receipt, persist=False, test_only=True)
        self.assertFalse(result["automatic_engine_activation"])
        self.assertFalse(result["completion"]["automatic_engine_activation"])

    def test_35_future_contract(self):
        contract = load("future_engine_admission_contract_v1.json")
        self.assertTrue(contract["backlog_driven_level3_contract"]["one_task_per_invocation"])
        self.assertFalse(contract["backlog_driven_level3_contract"]["automatic_activation"])

    def test_36_open_source_review(self):
        review = load("open_source_backlog_selection_review_v1.json")
        self.assertEqual(review["primary"]["name"], "Python heapq")
        self.assertIn("sqlite3", review["fallback"]["name"])
        self.assertFalse(review["automatic_dependency_install"])


if __name__ == "__main__":
    unittest.main()
