from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import AtomicHmacStateStore, ContinuousDevelopmentPilotService


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def run(command: list[str]) -> str:
    cp = subprocess.run(command, check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return cp.stdout.strip()


def git(root: Path, *args: str) -> str:
    return run(["git", "-c", "core.autocrlf=false", "-C", str(root), *args])


class Phase15ContinuousDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((CFG / "continuous_development_policy_v1.json").read_text())
        cls.pilot = json.loads((CFG / "monitored_level5_pilot_v1.json").read_text())

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.remote = root / "remote.git"
        self.runtime = root / "runtime"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        run(["git", "init", "--bare", str(self.remote)])
        run(["git", "init", "-b", "project-phoenix", str(self.repo)])
        git(self.repo, "config", "user.name", "test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "baseline")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "push", "-u", "origin", "project-phoenix")
        self.baseline = git(self.repo, "rev-parse", "HEAD")
        self.service = ContinuousDevelopmentPilotService(self.repo, self.runtime, policy_root=ROOT, clock=lambda: 1800000000.0)

    def tearDown(self):
        self.temporary.cleanup()

    def test_01_policy_schema(self): self.assertEqual(self.policy["schema"], "PHOENIX_CONTINUOUS_DEVELOPMENT_POLICY_V1")
    def test_02_pilot_mode(self):
        self.assertEqual(self.policy["mode"], "MONITORED_LEVEL5_PILOT")
        probe = self.service.probe()
        self.assertIn("provider_id", probe)
    def test_03_monitoring_enabled(self): self.assertTrue(self.policy["monitoring_enabled"])
    def test_04_daemon_disabled(self): self.assertFalse(self.policy["continuous_daemon_activation"])
    def test_05_engine_activation_disabled(self): self.assertFalse(self.policy["automatic_engine_activation"])
    def test_06_dependency_install_denied(self): self.assertEqual(self.policy["dependency_install"], "DENY")
    def test_07_network_denied(self): self.assertEqual(self.policy["network_access"], "DENY_BY_DEFAULT")
    def test_08_force_push_denied(self): self.assertEqual(self.policy["force_push"], "DENY")
    def test_09_history_rewrite_denied(self): self.assertEqual(self.policy["history_rewrite"], "DENY")
    def test_10_single_cycle_bound(self): self.assertEqual(self.policy["max_cycles_per_window"], 1)
    def test_11_single_task_bound(self): self.assertEqual(self.policy["max_tasks_per_cycle"], 1)
    def test_12_single_repair_bound(self): self.assertEqual(self.policy["max_self_repairs_per_cycle"], 1)
    def test_13_live_cycles_zero(self): self.assertEqual(self.pilot["maximum_live_cycles"], 0)
    def test_14_promotion_disabled(self): self.assertFalse(self.pilot["promotion_enabled"])
    def test_15_scheduler_not_installed(self): self.assertFalse(self.policy["scheduler"]["persistent_os_task_install"])
    def test_16_regression_allowlist(self): self.assertEqual(len(self.policy["regression"]["test_files"]), 17)

    def test_17_observe_clean_synced(self):
        value = self.service.observe(self.baseline)
        self.assertTrue(value.clean); self.assertEqual(value.origin_head, self.baseline)

    def test_18_wrong_baseline_denied(self):
        with self.assertRaisesRegex(RuntimeError, "BASELINE_DENY"):
            self.service.observe("0" * 40)

    def test_19_bad_baseline_format(self):
        with self.assertRaises(ValueError): self.service.observe("bad")

    def test_20_dirty_repo_denied(self):
        (self.repo / "dirty.txt").write_text("x")
        with self.assertRaisesRegex(RuntimeError, "BASELINE_DENY"):
            self.service.observe(self.baseline)

    def test_21_origin_mismatch_denied(self):
        git(self.repo, "commit", "--allow-empty", "-m", "local")
        with self.assertRaisesRegex(RuntimeError, "BASELINE_DENY"):
            self.service.observe(self.baseline)

    def test_22_tick_dry_run(self):
        result = self.service.monitored_tick(self.baseline)
        self.assertEqual(result["status"], "DRY_RUN_PASS")

    def test_23_tick_selects_one_low_task(self):
        result = self.service.monitored_tick(self.baseline)
        self.assertEqual((result["task_count"], result["selected_task_risk"]), (1, "LOW"))

    def test_24_tick_no_repo_mutation(self):
        before = git(self.repo, "status", "--porcelain=v1")
        result = self.service.monitored_tick(self.baseline)
        self.assertFalse(result["repository_mutation"]); self.assertEqual(before, git(self.repo, "status", "--porcelain=v1"))

    def test_25_tick_no_push(self): self.assertFalse(self.service.monitored_tick(self.baseline)["push_performed"])
    def test_26_tick_no_auto_promotion(self): self.assertFalse(self.service.monitored_tick(self.baseline)["pilot_automatic_promotion"])

    def test_27_kill_switch_pauses(self):
        self.runtime.mkdir(parents=True); (self.runtime / "PHOENIX_LEVEL5_STOP").write_text("STOP")
        self.assertEqual(self.service.monitored_tick(self.baseline)["status"], "PAUSED_KILL_SWITCH")

    def test_28_resume_after_kill_switch(self):
        self.runtime.mkdir(parents=True); stop = self.runtime / "PHOENIX_LEVEL5_STOP"; stop.write_text("STOP")
        self.service.monitored_tick(self.baseline); stop.unlink()
        self.assertEqual(self.service.monitored_tick(self.baseline)["status"], "DRY_RUN_PASS")

    def test_29_state_is_signed(self):
        result = self.service.monitored_tick(self.baseline)
        self.assertRegex(result["state_sha256"], r"^[0-9a-f]{64}$")

    def test_30_state_tamper_denied(self):
        self.service.monitored_tick(self.baseline)
        path = self.runtime / "continuous_state_v1.json"
        value = json.loads(path.read_text()); value["cycle_count"] = 99; path.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, "HMAC_DENY"):
            self.service.status()

    def test_31_signal_digest_deterministic(self):
        one = self.service.monitored_tick(self.baseline, persist=False)
        two = self.service.monitored_tick(self.baseline, persist=False)
        self.assertEqual(one["signal_sha256"], two["signal_sha256"])

    def test_32_policy_bundle_binds_phase15_policy(self):
        manifest = json.loads((CFG / "policy_bundle_manifest_v1.json").read_text())
        entry = manifest["files"]["continuous_development_policy_v1.json"]
        self.assertEqual(entry["sha256"], hashlib.sha256((CFG / "continuous_development_policy_v1.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
