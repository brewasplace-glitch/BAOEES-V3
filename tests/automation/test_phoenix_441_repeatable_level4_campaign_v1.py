from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import sqlite3
import unittest

from phoenix.autonomy import (
    CampaignTask,
    DeterministicCampaignSelector,
    RepeatableLevel4CampaignService,
    RuntimeProviderProbe,
    SQLiteCampaignStateStore,
    UniversalCapabilityExecutorRegistry,
)
from test_phoenix_441_backlog_driven_level3_cycle_v1 import (
    FakeBoundary,
    git,
    make_repository,
    run,
)
from test_phoenix_441_bounded_level4_autonomous_batch_v1 import StrictGateway


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name: str) -> dict:
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


def passing_tests(_root: Path) -> dict:
    return {
        "status": "PASS", "test_count": 424, "test_file_count": 16,
        "output_sha256": "0" * 64,
    }


def make_backup(repo: Path, root: Path, baseline: str, label: str) -> Path:
    target = root / label
    target.mkdir()
    bundle = target / "backup.bundle"
    snapshot = target / "snapshot"
    git(repo, "bundle", "create", str(bundle), "--all")
    git(repo, "bundle", "verify", str(bundle))
    run(["git", "clone", str(repo), str(snapshot)])
    receipt = target / "receipt.json"
    receipt.write_text(json.dumps({
        "status": "PASS", "baseline": baseline,
        "bundle_verified": True, "snapshot_verified": True,
        "bundle_path": str(bundle), "snapshot_path": str(snapshot),
    }), encoding="utf-8")
    return receipt


class UnavailableBoundary(FakeBoundary):
    def __init__(self):
        super().__init__(available=False)


class Phase14RepeatableLevel4CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load("autonomous_campaign_policy_v1.json")
        cls.backlog = load("autonomous_campaign_v1.json")

    def selector(self, policy=None, backlog=None):
        return DeterministicCampaignSelector(policy or self.policy, backlog or self.backlog)

    def service(self, repo, runtime, *, provider=None, executor=passing_tests, gateway=None):
        if gateway is not None:
            return RepeatableLevel4CampaignService(
                repo, runtime, policy_root=ROOT, provider=provider or FakeBoundary(),
                gateway=gateway, enable_gateway=False, test_executor=executor,
            )
        return RepeatableLevel4CampaignService(
            repo, runtime, policy_root=ROOT, provider=provider or FakeBoundary(),
            enable_gateway=False, test_only_gateway=True, test_executor=executor,
        )

    def two_batches(self, root: Path, *, persist=False, gateway=None, simulate_windows_checkout=False):
        repo, baseline, receipt = make_repository(root)
        runtime = root / "runtime"
        first_service = self.service(repo, runtime, gateway=gateway)
        first = first_service.run_next_batch(baseline, receipt, persist=persist, test_only=True)
        second_baseline = first["promoted_commit"]
        if simulate_windows_checkout:
            git(repo, "config", "core.autocrlf", "true")
            for row in self.backlog["tasks"][:3]:
                path = repo / row["output_path"]
                path.unlink()
                run(["git", "-C", str(repo), "checkout", "HEAD", "--", row["output_path"]])
                self.assertIn(b"\r\n", path.read_bytes())
            self.assertEqual(run(["git", "-C", str(repo), "status", "--porcelain=v1"]), "")
        second_receipt = make_backup(repo, root, second_baseline, "backup-2")
        second_service = first_service if not persist else self.service(repo, runtime, gateway=gateway)
        second = second_service.run_next_batch(second_baseline, second_receipt, persist=persist, test_only=True)
        return repo, runtime, first, second

    def test_01_policy_active_fail_closed(self):
        self.assertEqual(self.policy["schema"], "PHOENIX_AUTONOMOUS_CAMPAIGN_POLICY_V1")
        self.assertTrue(self.policy["fail_closed"])

    def test_02_exact_two_batch_boundary(self):
        self.assertEqual(self.policy["max_batches_per_campaign"], 2)

    def test_03_exact_three_tasks_per_batch(self):
        self.assertEqual(self.policy["tasks_per_batch"], 3)

    def test_04_low_risk_only(self):
        self.assertEqual(self.policy["allowed_risk"], ["LOW"])

    def test_05_continuous_monitoring_forbidden(self):
        self.assertFalse(self.policy["continuous_monitoring"])

    def test_06_unsafe_automatic_changes_disabled(self):
        for key in (
            "automatic_source_change", "automatic_dependency_change",
            "automatic_policy_change", "automatic_registry_change",
            "automatic_engine_activation",
        ):
            self.assertFalse(self.policy[key])

    def test_07_repair_budget_exact(self):
        self.assertEqual(self.policy["self_repair"]["max_repairs_per_batch"], 1)
        self.assertEqual(self.policy["self_repair"]["max_repairs_per_campaign"], 2)

    def test_08_explicit_424_test_allowlist(self):
        regression = self.policy["regression"]
        self.assertEqual(regression["expected_test_count"], 424)
        self.assertEqual(len(regression["test_files"]), 16)
        self.assertEqual(len(regression["test_files"]), len(set(regression["test_files"])))

    def test_09_resume_backend_sqlite_hmac(self):
        resume = self.policy["resume"]
        self.assertEqual(resume["state_backend"], "SQLITE_ATOMIC_HMAC_BOUND")
        self.assertTrue(resume["require_completed_output_hash_revalidation"])

    def test_10_backlog_has_six_tasks(self):
        self.assertEqual(len(self.backlog["tasks"]), 6)

    def test_11_campaign_task_hash_stable(self):
        one = CampaignTask.from_dict(self.backlog["tasks"][0])
        two = CampaignTask.from_dict(self.backlog["tasks"][0])
        self.assertEqual(one.sha256, two.sha256)

    def test_12_first_batch_selection_order(self):
        with TemporaryDirectory() as td:
            result = self.selector().select(Path(td), ())
        self.assertEqual(result.task_ids, (
            "PHX-L4-CAMPAIGN-PLAN-101",
            "PHX-L4-CROSS-BATCH-GATES-102",
            "PHX-L4-RESUME-EVIDENCE-103",
        ))

    def test_13_second_batch_selection_order(self):
        first = tuple(row["task_id"] for row in self.backlog["tasks"][:3])
        with TemporaryDirectory() as td:
            result = self.selector().select(Path(td), first)
        self.assertEqual(result.task_ids, (
            "PHX-L4-LESSON-APPLICATION-201",
            "PHX-L4-CAMPAIGN-REGRESSION-202",
            "PHX-L4-CAMPAIGN-COMPLETION-203",
        ))

    def test_14_selection_repeatable(self):
        with TemporaryDirectory() as td:
            one = self.selector().select(Path(td), ()).to_dict()
            two = self.selector().select(Path(td), ()).to_dict()
        self.assertEqual(one, two)

    def test_15_duplicate_task_id_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][1]["task_id"] = backlog["tasks"][0]["task_id"]
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE"):
            self.selector(backlog=backlog)

    def test_16_high_risk_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["risk"] = "HIGH"
        with self.assertRaisesRegex(PermissionError, "RISK"):
            self.selector(backlog=backlog)

    def test_17_executable_output_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["output_path"] = "docs/automation/autonomous_generated/x.py"
        with self.assertRaisesRegex(PermissionError, "EXTENSION"):
            self.selector(backlog=backlog)

    def test_18_protected_output_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["output_path"] = "phoenix/autonomy/x.md"
        with self.assertRaisesRegex(PermissionError, "SCOPE"):
            self.selector(backlog=backlog)

    def test_19_unknown_dependency_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["depends_on"] = ["PHX-UNKNOWN-999"]
        with self.assertRaisesRegex(PermissionError, "DEPENDENCY"):
            self.selector(backlog=backlog)

    def test_20_dependency_cycle_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"][0]["depends_on"] = [backlog["tasks"][1]["task_id"]]
        with self.assertRaisesRegex(RuntimeError, "CYCLE"):
            self.selector(backlog=backlog)

    def test_21_incomplete_campaign_backlog_denied(self):
        backlog = deepcopy(self.backlog)
        backlog["tasks"].pop()
        with self.assertRaisesRegex(RuntimeError, "BACKLOG_SIZE"):
            self.selector(backlog=backlog)

    def test_22_unrecorded_existing_output_denied(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            output = root / self.backlog["tasks"][0]["output_path"]
            output.parent.mkdir(parents=True)
            output.write_text("unrecorded\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "UNRECORDED_OUTPUT"):
                self.selector().select(root, ())

    def test_23_sqlite_store_volatile_roundtrip(self):
        with TemporaryDirectory() as td:
            store = SQLiteCampaignStateStore(Path(td) / "state.sqlite3")
            store.save({"value": 1}, persist=False)
            self.assertEqual(store.load(persist=False), {"value": 1})

    def test_24_sqlite_store_persistent_roundtrip(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "state.sqlite3"
            store = SQLiteCampaignStateStore(path)
            store.save({"value": 2}, persist=True)
            self.assertEqual(SQLiteCampaignStateStore(path).load(persist=True), {"value": 2})
            path.unlink()
            self.assertFalse(path.exists())

    def test_25_sqlite_store_digest_tamper_denied(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "state.sqlite3"
            store = SQLiteCampaignStateStore(path)
            store.save({"value": 3}, persist=True)
            connection = sqlite3.connect(path)
            try:
                connection.execute("UPDATE campaign_state SET payload_json='{}' WHERE singleton_id=1")
                connection.commit()
            finally:
                connection.close()
            with self.assertRaisesRegex(RuntimeError, "DIGEST"):
                store.load(persist=True)

    def test_26_missing_backup_denied(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, _ = make_repository(root)
            with self.assertRaisesRegex(RuntimeError, "BACKUP_RECEIPT"):
                self.service(repo, root / "runtime").run_next_batch(baseline, root / "missing.json", persist=False, test_only=True)

    def test_27_backup_baseline_mismatch_denied(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, receipt = make_repository(root)
            value = json.loads(receipt.read_text()); value["baseline"] = "0" * 40
            receipt.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "BACKUP_BASELINE"):
                self.service(repo, root / "runtime").run_next_batch(baseline, receipt, persist=False, test_only=True)

    def test_28_dirty_main_denied(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, receipt = make_repository(root)
            (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "dirty"):
                self.service(repo, root / "runtime").run_next_batch(baseline, receipt, persist=False, test_only=True)

    def test_29_unavailable_boundary_denied(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, receipt = make_repository(root)
            with self.assertRaises(PermissionError):
                self.service(repo, root / "runtime", provider=UnavailableBoundary()).run_next_batch(baseline, receipt, persist=False, test_only=True)

    def test_30_failed_regression_denies_promotion(self):
        def failed(_root):
            return {"status": "FAIL", "test_count": 424}
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, receipt = make_repository(root)
            with self.assertRaisesRegex(RuntimeError, "TEST_GATE"):
                self.service(repo, root / "runtime", executor=failed).run_next_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(git(repo, "rev-parse", "HEAD"), baseline)

    def test_31_real_first_batch_passes(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, receipt = make_repository(root)
            result = self.service(repo, root / "runtime").run_next_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual((result["status"], result["batch_number"], result["test_count"]), ("PASS", 1, 424))

    def test_32_first_batch_promotes_all_outputs(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, baseline, receipt = make_repository(root)
            result = self.service(repo, root / "runtime").run_next_batch(baseline, receipt, persist=False, test_only=True)
            self.assertEqual(git(repo, "rev-parse", "HEAD"), result["promoted_commit"])
            for row in self.backlog["tasks"][:3]:
                self.assertTrue((repo / row["output_path"]).is_file())

    def test_33_process_restart_resumes_second_batch(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, runtime, first, second = self.two_batches(
                root, persist=True, simulate_windows_checkout=True
            )
            self.assertEqual((first["batch_number"], second["batch_number"]), (1, 2))
            self.assertEqual(second["remaining_batches"], 0)

    def test_34_two_batches_promote_six_outputs(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, _, _, _ = self.two_batches(root, persist=True)
            for row in self.backlog["tasks"]:
                self.assertTrue((repo / row["output_path"]).is_file())

    def test_35_second_batch_consumes_prior_completion_digest(self):
        with TemporaryDirectory() as td:
            root = Path(td); _, _, first, second = self.two_batches(root, persist=True)
            self.assertEqual(
                second["completion"]["prior_batch_completion_sha256"],
                first["completion"]["completion_sha256"],
            )

    def test_36_campaign_finalization_passes(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, runtime, _, second = self.two_batches(root, persist=True)
            result = self.service(repo, runtime).finalize_campaign(second["promoted_commit"], persist=True, test_only=True)
            self.assertEqual((result["completed_batches"], result["completed_tasks"], result["total_self_repairs"]), (2, 6, 2))

    def test_37_campaign_finalization_is_idempotent(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, runtime, _, second = self.two_batches(root, persist=True)
            self.service(repo, runtime).finalize_campaign(second["promoted_commit"], persist=True, test_only=True)
            again = self.service(repo, runtime).finalize_campaign(second["promoted_commit"], persist=True, test_only=True)
            self.assertTrue(again["already_completed"])

    def test_38_strict_gateway_campaign_passes(self):
        with TemporaryDirectory() as td:
            root = Path(td); repo, runtime, _, second = self.two_batches(root, persist=True, gateway=StrictGateway())
            result = self.service(repo, runtime, gateway=StrictGateway()).finalize_campaign(second["promoted_commit"], persist=True, test_only=True)
            self.assertEqual(result["status"], "PASS")

    def test_39_one_repair_per_batch(self):
        with TemporaryDirectory() as td:
            root = Path(td); _, _, first, second = self.two_batches(root, persist=True)
            self.assertEqual((first["self_repair_count"], second["self_repair_count"]), (1, 1))

    def test_40_policy_bundle_binds_phase14_files(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in (
            "autonomous_campaign_policy_v1.json",
            "autonomous_campaign_v1.json",
            "autonomous_campaign_completion_v1.schema.json",
        ):
            self.assertEqual(manifest["files"][name]["sha256"], hashlib.sha256((CFG / name).read_bytes()).hexdigest())

    def test_41_versions_advance(self):
        self.assertEqual(load("autonomy_policy_v2.json")["version"], "3.1.0")
        self.assertEqual(load("engine_registry_v1.json")["version"], "2.2.0")
        self.assertEqual(load("capability_executor_registry_v1.json")["version"], "1.9.0")
        self.assertEqual(load("future_engine_admission_contract_v1.json")["version"], "2.0.0")

    def test_42_executor_registry_coverage(self):
        registry = UniversalCapabilityExecutorRegistry.from_repo(ROOT)
        descriptor = registry.descriptor_for(
            "autonomy.campaign_cycle", "autonomy.campaign.state.write",
            plan_dispatch_only=False,
        )
        self.assertEqual(descriptor.adapter_id, "builtin.campaign.cycle.internal")

    def test_43_future_contract(self):
        contract = load("future_engine_admission_contract_v1.json")["repeatable_level4_campaign_contract"]
        self.assertTrue(contract["atomic_hmac_bound_resume_state_required"])
        self.assertFalse(contract["continuous_monitoring"])
        self.assertFalse(contract["automatic_activation"])

    def test_44_open_source_review(self):
        review = load("open_source_level4_campaign_review_v1.json")
        self.assertEqual(review["selected"]["resume_state"], "python.sqlite3")
        self.assertEqual([row["project"] for row in review["considered"]], ["APScheduler", "Prefect"])
        self.assertFalse(review["automatic_dependency_install"])


if __name__ == "__main__":
    unittest.main()
