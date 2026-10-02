from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import GovernedContinuousLevel5Service


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def run(command: list[str]) -> str:
    return subprocess.run(command, check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.strip()


class Phase16GovernedContinuousLevel5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((CFG / "governed_continuous_level5_policy_v1.json").read_text())

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"; self.remote = root / "remote.git"; self.runtime = root / "runtime"
        self.repo.mkdir(); (self.repo / "configs/phoenix").mkdir(parents=True)
        (self.repo / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='1'\n", encoding="utf-8")
        for name in ("policy_bundle_manifest_v1.json", "autonomous_backlog_v1.json", "isolated_runtime_policy_v1.json"):
            (self.repo / "configs/phoenix" / name).write_bytes((CFG / name).read_bytes())
        run(["git", "init", "--bare", str(self.remote)])
        run(["git", "init", "-b", "project-phoenix", str(self.repo)])
        run(["git", "-C", str(self.repo), "config", "user.name", "test"])
        run(["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"])
        run(["git", "-C", str(self.repo), "add", "."]); run(["git", "-C", str(self.repo), "commit", "-m", "baseline"])
        run(["git", "-C", str(self.repo), "remote", "add", "origin", str(self.remote)])
        run(["git", "-C", str(self.repo), "push", "-u", "origin", "project-phoenix"])
        self.baseline = run(["git", "-C", str(self.repo), "rev-parse", "HEAD"])
        self.now = 1800000000
        self.service = GovernedContinuousLevel5Service(
            self.repo, self.runtime, policy_root=ROOT, clock=lambda: self.now,
            isolation_probe=lambda: {"provider_id": "test.accepted", "available": True, "security_boundary": True, "execution_enabled": True},
        )

    def tearDown(self): self.temporary.cleanup()

    def test_01_schema(self): self.assertEqual(self.policy["schema"], "PHOENIX_GOVERNED_CONTINUOUS_LEVEL5_POLICY_V1")
    def test_02_mode(self): self.assertEqual(self.policy["mode"], "SCHEDULED_GOVERNED_HEALTH_WINDOWS")
    def test_03_monitoring_enabled(self): self.assertTrue(self.policy["monitoring_enabled"])
    def test_04_no_daemon(self): self.assertFalse(self.policy["persistent_daemon"])
    def test_05_no_repo_mutation(self): self.assertFalse(self.policy["automatic_repository_mutation"])
    def test_06_no_promotion(self): self.assertFalse(self.policy["automatic_promotion"])
    def test_07_no_engine_activation(self): self.assertFalse(self.policy["automatic_engine_activation"])
    def test_08_dependency_install_denied(self): self.assertEqual(self.policy["dependency_install"], "DENY")
    def test_09_force_push_denied(self): self.assertEqual(self.policy["force_push"], "DENY")
    def test_10_single_window(self): self.assertEqual(self.policy["max_windows_per_invocation"], 1)
    def test_11_single_task_observation(self): self.assertEqual(self.policy["max_tasks_selected_per_window"], 1)
    def test_12_scheduler_daily_0100(self):
        spec = self.service.scheduler_spec(); self.assertEqual((spec["frequency"], spec["local_time"]), ("DAILY", "01:00"))
    def test_13_scheduler_denies_overlap(self): self.assertEqual(self.service.scheduler_spec()["multiple_instances"], "IGNORE_NEW")
    def test_14_scheduler_no_daemon(self): self.assertFalse(self.service.scheduler_spec()["persistent_daemon"])

    def test_15_healthy_window(self):
        result = self.service.run_window(self.baseline)
        self.assertEqual(result["status"], "HEALTHY_NO_MUTATION"); self.assertFalse(result["repository_mutation"])

    def test_16_signed_state(self): self.assertRegex(self.service.run_window(self.baseline)["state_sha256"], r"^[0-9a-f]{64}$")
    def test_17_health_record_persisted(self):
        self.service.run_window(self.baseline); self.assertTrue((self.runtime / self.policy["health_record_filename"]).is_file())
    def test_18_audit_appended(self):
        self.service.run_window(self.baseline); self.assertEqual(len((self.runtime / self.policy["audit_filename"]).read_text().splitlines()), 1)
    def test_19_kill_switch(self):
        self.runtime.mkdir(); (self.runtime / "PHOENIX_LEVEL5_STOP").write_text("STOP")
        self.assertEqual(self.service.run_window(self.baseline)["status"], "PAUSED_KILL_SWITCH")
    def test_20_overlap_denied(self):
        self.runtime.mkdir(); (self.runtime / "PHOENIX_LEVEL5_WINDOW.lock").write_text("held")
        self.assertEqual(self.service.run_window(self.baseline)["status"], "SKIPPED_OVERLAP")
    def test_21_interval_enforced(self):
        self.service.run_window(self.baseline); self.assertEqual(self.service.run_window(self.baseline)["status"], "SKIPPED_INTERVAL")
    def test_22_dirty_repo_denied(self):
        (self.repo / "dirty.txt").write_text("x")
        with self.assertRaisesRegex(RuntimeError, "BASELINE_DENY"): self.service.run_window(self.baseline)
    def test_23_origin_mismatch_denied(self):
        run(["git", "-C", str(self.repo), "commit", "--allow-empty", "-m", "local"])
        with self.assertRaisesRegex(RuntimeError, "BASELINE_DENY"): self.service.run_window(self.baseline)
    def test_24_bad_isolation_denied(self):
        service = GovernedContinuousLevel5Service(self.repo, self.runtime, policy_root=ROOT, isolation_probe=lambda: {"available": False})
        with self.assertRaisesRegex(RuntimeError, "ISOLATION_PROVIDER_DENY"): service.run_window(self.baseline)
    def test_25_dependency_digest(self):
        result = self.service.run_window(self.baseline, persist=False)
        self.assertEqual(result["signals"]["dependency_manifest_digest"], hashlib.sha256((self.repo / "pyproject.toml").read_bytes()).hexdigest())
    def test_26_task_observation_bounded(self): self.assertLessEqual(self.service.run_window(self.baseline, persist=False)["task_count"], 1)
    def test_27_no_push(self): self.assertFalse(self.service.run_window(self.baseline, persist=False)["push_performed"])
    def test_28_status_no_promotion(self): self.assertFalse(self.service.status()["automatic_promotion"])
    def test_29_schema_file(self):
        schema = json.loads((CFG / "continuous_health_record_v1.schema.json").read_text()); self.assertIn("HEALTHY_NO_MUTATION", schema["properties"]["status"]["enum"])
    def test_30_policy_bundle_binding(self):
        manifest = json.loads((CFG / "policy_bundle_manifest_v1.json").read_text())
        expected = hashlib.sha256((CFG / "governed_continuous_level5_policy_v1.json").read_bytes()).hexdigest()
        self.assertEqual(manifest["files"]["governed_continuous_level5_policy_v1.json"]["sha256"], expected)


if __name__ == "__main__": unittest.main()
