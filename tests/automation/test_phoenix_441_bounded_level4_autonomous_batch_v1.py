from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import unittest

from phoenix.autonomy import (
    BatchTask,
    BoundedLevel4BatchService,
    DeterministicBatchSelector,
    UniversalCapabilityExecutorRegistry,
)
from test_phoenix_441_backlog_driven_level3_cycle_v1 import (
    FakeBoundary,
    git,
    make_repository,
)


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name: str) -> dict:
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


def passing_tests(_root: Path) -> dict:
    return {"status": "PASS", "test_count": 380, "output_sha256": "0" * 64}


class StrictGateway:
    def authorize(self, intent):
        return intent

    def consume(self, permit, *, engine_id, action, paths=()):
        normalized = tuple(str(path).replace("\\", "/").lstrip("./") for path in paths)
        if (permit.engine_id, permit.action, permit.paths) != (engine_id, action, normalized):
            raise PermissionError("STRICT_GATEWAY_BINDING_DENY")


class Phase13BoundedLevel4BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load("autonomous_batch_policy_v1.json")
        cls.backlog = load("autonomous_batch_v1.json")

    def selector(self, policy=None, backlog=None):
        return DeterministicBatchSelector(policy or self.policy, backlog or self.backlog)

    def service(self, repo, runtime, *, provider=None, executor=passing_tests, gateway=None):
        if gateway is not None:
            return BoundedLevel4BatchService(
                repo, runtime, policy_root=ROOT, provider=provider or FakeBoundary(),
                gateway=gateway, enable_gateway=False, test_executor=executor,
            )
        return BoundedLevel4BatchService(
            repo, runtime, policy_root=ROOT, provider=provider or FakeBoundary(),
            enable_gateway=False, test_only_gateway=True, test_executor=executor,
        )

    def test_01_policy_active_fail_closed(self):
        self.assertEqual(self.policy["schema"], "PHOENIX_AUTONOMOUS_BATCH_POLICY_V1")
        self.assertTrue(self.policy["fail_closed"])

    def test_02_exact_three_task_boundary(self):
        self.assertEqual(self.policy["min_tasks_per_batch"], 3)
        self.assertEqual(self.policy["max_tasks_per_batch"], 3)

    def test_03_low_risk_only(self):
        self.assertEqual(self.policy["allowed_risk"], ["LOW"])

    def test_04_partial_promotion_denied(self):
        self.assertEqual(self.policy["partial_batch_promotion"], "DENY")

    def test_05_unsafe_automatic_changes_disabled(self):
        for key in ("automatic_source_change", "automatic_dependency_change", "automatic_policy_change", "automatic_registry_change", "automatic_engine_activation"):
            self.assertFalse(self.policy[key])

    def test_06_explicit_380_test_allowlist(self):
        regression = self.policy["regression"]
        self.assertEqual(regression["command_profile"], "PYTHON_UNITTEST_EXPLICIT_ALLOWLIST")
        self.assertEqual(regression["expected_test_count"], 380)
        self.assertEqual(len(regression["test_files"]), 15)

    def test_07_repair_budget_one(self):
        self.assertEqual(self.policy["self_repair"]["max_repairs_per_batch"], 1)

    def test_08_repair_failure_code_exact(self):
        self.assertEqual(self.policy["self_repair"]["allowed_failure_codes"], ["TRAILING_WHITESPACE"])

    def test_09_backlog_has_three_tasks(self):
        self.assertEqual(len(self.backlog["tasks"]), 3)

    def test_10_batch_task_hash_stable(self):
        task = BatchTask.from_dict(self.backlog["tasks"][0])
        self.assertEqual(task.sha256, BatchTask.from_dict(self.backlog["tasks"][0]).sha256)

    def test_11_selection_order(self):
        with TemporaryDirectory() as td:
            result = self.selector().select(Path(td))
        self.assertEqual(result.task_ids, (
            "PHX-L4-GOVERNANCE-SUMMARY-001",
            "PHX-L4-REGRESSION-EVIDENCE-002",
            "PHX-L4-LESSONS-LEARNED-003",
        ))

    def test_12_selection_repeatable(self):
        with TemporaryDirectory() as td:
            one = self.selector().select(Path(td)).to_dict()
            two = self.selector().select(Path(td)).to_dict()
        self.assertEqual(one, two)

    def test_13_duplicate_task_id_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].append(deepcopy(backlog["tasks"][0]))
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE"):
            self.selector(backlog=backlog)

    def test_14_high_risk_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["risk"] = "HIGH"
        with self.assertRaisesRegex(PermissionError, "RISK"):
            self.selector(backlog=backlog)

    def test_15_executable_output_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["output_path"] = "docs/automation/autonomous_generated/x.py"
        with self.assertRaisesRegex(PermissionError, "EXTENSION"):
            self.selector(backlog=backlog)

    def test_16_protected_output_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["output_path"] = "phoenix/autonomy/x.md"
        with self.assertRaisesRegex(PermissionError, "OUTPUT_SCOPE"):
            self.selector(backlog=backlog)

    def test_17_unknown_dependency_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["depends_on"] = ["UNKNOWN"]
        with self.assertRaisesRegex(PermissionError, "DEPENDENCY"):
            self.selector(backlog=backlog)

    def test_18_dependency_cycle_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["depends_on"] = ["PHX-L4-LESSONS-LEARNED-003"]
        with self.assertRaisesRegex(RuntimeError, "CYCLE"):
            self.selector(backlog=backlog)

    def test_19_incomplete_batch_denied(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            output = root / self.backlog["tasks"][0]["output_path"]
            output.parent.mkdir(parents=True)
            output.write_text("existing\n")
            with self.assertRaisesRegex(RuntimeError, "NO_ELIGIBLE_COMPLETE_BATCH"):
                self.selector().select(root)

    def test_20_trailing_whitespace_detected(self):
        with TemporaryDirectory() as td:
            repo, _, _ = make_repository(Path(td))
            service = self.service(repo, Path(td) / "runtime")
            self.assertEqual(service._content_failure("# PROJECT PHOENIX — X\nline \n"), "TRAILING_WHITESPACE")

    def test_21_deterministic_repair_removes_only_horizontal_suffix(self):
        with TemporaryDirectory() as td:
            repo, _, _ = make_repository(Path(td))
            service = self.service(repo, Path(td) / "runtime")
            repaired = service._repair_content("# PROJECT PHOENIX — X\nline \t\n", "TRAILING_WHITESPACE")
            self.assertEqual(repaired, "# PROJECT PHOENIX — X\nline\n")

    def test_22_unapproved_repair_denied(self):
        with TemporaryDirectory() as td:
            repo, _, _ = make_repository(Path(td))
            service = self.service(repo, Path(td) / "runtime")
            with self.assertRaisesRegex(RuntimeError, "UNREPAIRABLE"):
                service._repair_content("bad", "STRUCTURE_INVALID")

    def test_23_missing_backup_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, _ = make_repository(Path(td))
            with self.assertRaisesRegex(RuntimeError, "BACKUP_RECEIPT_REQUIRED"):
                self.service(repo, Path(td) / "runtime").run_batch(baseline, Path(td) / "missing.json", persist=False, test_only=True)

    def test_24_backup_mismatch_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            value = json.loads(receipt.read_text())
            value["baseline"] = "0" * 40
            receipt.write_text(json.dumps(value))
            with self.assertRaisesRegex(RuntimeError, "BACKUP_BASELINE"):
                self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)

    def test_25_dirty_main_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            (repo / "dirty.txt").write_text("dirty\n")
            with self.assertRaisesRegex(RuntimeError, "main_worktree_dirty"):
                self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)

    def test_26_unavailable_boundary_denied(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            with self.assertRaisesRegex(PermissionError, "SECURITY_BOUNDARY_REQUIRED"):
                self.service(repo, Path(td) / "runtime", provider=FakeBoundary(available=False)).run_batch(baseline, receipt, persist=False, test_only=True)

    def test_27_failed_regression_denies_promotion(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            failed = lambda _root: {"status": "FAILED", "test_count": 379}
            with self.assertRaisesRegex(RuntimeError, "TEST_GATE"):
                self.service(repo, Path(td) / "runtime", executor=failed).run_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(git(repo, "rev-parse", "HEAD"), baseline)

    def test_28_real_git_backed_batch_passes(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["task_count"], 3)
            self.assertEqual(result["self_repair_count"], 1)

    def test_29_all_outputs_promoted(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)
            self.assertTrue(all((repo / row["output_path"]).is_file() for row in self.backlog["tasks"]))
            self.assertEqual(git(repo, "rev-parse", "HEAD"), result["promoted_commit"])

    def test_30_remote_matches_promoted_commit(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(git(repo, "rev-parse", "origin/project-phoenix"), result["promoted_commit"])

    def test_31_strict_gateway_with_bib_side_effect(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            hook = repo / ".git/hooks/pre-commit"
            hook.write_text("#!/bin/sh\nmkdir -p bib/PHOENIX_AUTO_SYNC\nprintf 'governance\\n' > bib/PHOENIX_AUTO_SYNC/BIB_BASELINE.md\ngit add bib/PHOENIX_AUTO_SYNC/BIB_BASELINE.md\n", encoding="utf-8", newline="\n")
            os.chmod(hook, 0o755)
            result = self.service(repo, Path(td) / "runtime", gateway=StrictGateway()).run_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(result["completion"]["governance_side_effect_paths"], ["bib/PHOENIX_AUTO_SYNC/BIB_BASELINE.md"])

    def test_32_second_batch_has_no_complete_selection(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            repo, baseline, receipt = make_repository(root)
            result = self.service(repo, root / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)
            new_head = result["promoted_commit"]
            bundle = root / "backup2.bundle"
            git(repo, "bundle", "create", str(bundle), "--all")
            snapshot = root / "snapshot2"
            import subprocess
            subprocess.run(["git", "clone", str(repo), str(snapshot)], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            receipt2 = root / "receipt2.json"
            receipt2.write_text(json.dumps({"status":"PASS", "baseline":new_head, "bundle_verified":True, "snapshot_verified":True, "bundle_path":str(bundle), "snapshot_path":str(snapshot)}))
            with self.assertRaisesRegex(RuntimeError, "NO_ELIGIBLE_COMPLETE_BATCH"):
                self.service(repo, root / "runtime2").run_batch(new_head, receipt2, persist=False, test_only=True)

    def test_33_completion_preserves_activation_boundary(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)
        self.assertFalse(result["automatic_engine_activation"])
        self.assertFalse(result["completion"]["automatic_engine_activation"])

    def test_34_completion_has_three_task_receipts(self):
        with TemporaryDirectory() as td:
            repo, baseline, receipt = make_repository(Path(td))
            result = self.service(repo, Path(td) / "runtime").run_batch(baseline, receipt, persist=False, test_only=True)
        self.assertEqual(len(result["completion"]["task_receipts"]), 3)

    def test_35_policy_bundle_binds_phase13_files(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in ("autonomous_batch_policy_v1.json", "autonomous_batch_v1.json", "autonomous_batch_completion_v1.schema.json"):
            self.assertEqual(manifest["files"][name]["sha256"], hashlib.sha256((CFG / name).read_bytes()).hexdigest())

    def test_36_versions_advance(self):
        self.assertEqual(load("autonomy_policy_v2.json")["version"], "3.0.0")
        self.assertEqual(load("engine_registry_v1.json")["version"], "2.1.0")
        self.assertEqual(load("capability_executor_registry_v1.json")["version"], "1.8.0")
        self.assertEqual(load("future_engine_admission_contract_v1.json")["version"], "1.9.0")

    def test_37_executor_registry_coverage(self):
        report = UniversalCapabilityExecutorRegistry.from_repo(ROOT).coverage_report()
        self.assertTrue(report["complete"])

    def test_38_engine_gateway_binding(self):
        engine = next(row for row in load("engine_registry_v1.json")["engines"] if row["engine_id"] == "autonomy.batch_cycle")
        self.assertTrue(engine["mutation_capable"] and engine["gateway_required"])
        self.assertIn("worktree://phase13/", engine["allowed_path_roots"])

    def test_39_future_contract(self):
        contract = load("future_engine_admission_contract_v1.json")["bounded_level4_batch_contract"]
        self.assertEqual(contract["max_tasks_per_batch"], 3)
        self.assertFalse(contract["automatic_activation"])

    def test_40_open_source_review(self):
        review = load("open_source_level4_batch_review_v1.json")
        self.assertEqual(review["primary"]["name"], "Python heapq")
        self.assertEqual(review["rejected_distributed_queue"]["decision"], "REJECT_FOR_PHASE13_RUNTIME")
        self.assertFalse(review["automatic_dependency_install"])


if __name__ == "__main__":
    unittest.main()
