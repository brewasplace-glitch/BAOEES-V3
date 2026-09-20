import base64
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy import (
    BoundedRepositoryImprovementCycleService,
    ChangeRecord,
    GuardedWorktreeManager,
    RepositoryChangeClassifier,
    RuntimeProviderProbe,
    UniversalCapabilityExecutorRegistry,
    build_patch_probe_source,
    initialize_fixture_repository,
    normalize_repository_path,
)


ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "configs" / "phoenix"


def load(name):
    return json.loads((CFG / name).read_text(encoding="utf-8-sig"))


def record(path, content=b"x", status="A", *, symlink=False):
    return ChangeRecord(
        status,
        path,
        len(content),
        hashlib.sha256(content).hexdigest(),
        symlink,
    )


class FakePhase10Boundary:
    provider_id = "test.only.phase10.boundary"
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
        expected = re.search(r"^EXPECTED = '([a-f0-9]{64})'$", source, re.MULTILINE).group(1)
        lane = re.search(r"^LANE = '([^']+)'$", source, re.MULTILINE).group(1)
        encoded = re.search(
            r"^PATCH = base64\.b64decode\('([^']+)'\)$", source, re.MULTILINE
        ).group(1)
        patch = base64.b64decode(encoded)
        result = {
            "patch_sha256": expected,
            "patch_bytes": len(patch),
            "lane": lane,
            "mode": "PHASE10_READ_ONLY_PATCH_PROBE_V1",
        }
        second = dict(result)
        if self.mismatch:
            second["mode"] = "MISMATCH"
        boundary = {
            "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
            "nonce": request["nonce"],
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
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
            "stdout_sha256": "0" * 64,
            "stderr_sha256": "0" * 64,
            "command_policy": {"network": "none", "test_only": True},
        }


class Phase10RepositoryCycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load("repository_improvement_cycle_policy_v1.json")
        cls.protected = load("protected_repository_paths_v1.json")
        cls.classifier = RepositoryChangeClassifier(cls.policy, cls.protected)

    def service(self, runtime, provider=None):
        return BoundedRepositoryImprovementCycleService(
            ROOT,
            Path(runtime),
            provider=provider or FakePhase10Boundary(),
            enable_gateway=False,
        )

    def test_01_policy_contract(self):
        self.assertEqual(
            self.policy["schema"],
            "PHOENIX_REPOSITORY_IMPROVEMENT_CYCLE_POLICY_V1",
        )
        self.assertTrue(self.policy["fail_closed"])
        self.assertEqual(self.policy["allowed_risk"], ["LOW"])
        self.assertEqual(self.policy["max_repair_attempts"], 3)

    def test_02_protected_path_contract(self):
        self.assertEqual(
            self.protected["schema"], "PHOENIX_PROTECTED_REPOSITORY_PATHS_V1"
        )
        self.assertTrue(self.protected["deny_symlinks_and_junctions"])

    def test_03_phase10_versions_advance(self):
        self.assertEqual(load("autonomy_policy_v2.json")["version"], "2.7.0")
        self.assertEqual(load("engine_registry_v1.json")["version"], "1.8.0")
        self.assertEqual(
            load("capability_executor_registry_v1.json")["version"], "1.5.0"
        )
        self.assertEqual(
            load("future_engine_admission_contract_v1.json")["version"], "1.6.0"
        )

    def test_04_registry_coverage_complete(self):
        report = UniversalCapabilityExecutorRegistry.from_repo(ROOT).coverage_report()
        self.assertTrue(report["complete"])
        self.assertEqual(report["active_engine_actions"], report["covered_engine_actions"])

    def test_05_repository_cycle_engine_is_gateway_bound(self):
        engines = load("engine_registry_v1.json")["engines"]
        engine = [x for x in engines if x["engine_id"] == "autonomy.repository_cycle"][0]
        self.assertTrue(engine["mutation_capable"])
        self.assertTrue(engine["gateway_required"])
        self.assertIn("runtime://repository_cycle/", engine["allowed_path_roots"])

    def test_06_policy_bundle_binds_phase10_files(self):
        manifest = load("policy_bundle_manifest_v1.json")
        for name in (
            "repository_improvement_cycle_policy_v1.json",
            "protected_repository_paths_v1.json",
        ):
            self.assertTrue(manifest["files"][name]["required"])
            self.assertRegex(manifest["files"][name]["sha256"], r"^[a-f0-9]{64}$")

    def test_07_path_normalizes_backslashes(self):
        self.assertEqual(
            normalize_repository_path(
                r"docs\automation\autonomous_generated\x.md",
                windows_reserved_names=self.protected["windows_reserved_names"],
            ),
            "docs/automation/autonomous_generated/x.md",
        )

    def test_08_absolute_path_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "ABSOLUTE"):
            self.classifier.normalize("C:/PROJECT-PHOENIX/x.md")

    def test_09_traversal_path_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "TRAVERSAL"):
            self.classifier.normalize("docs/../configs/x.json")

    def test_10_windows_reserved_name_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "RESERVED"):
            self.classifier.normalize("docs/automation/autonomous_generated/CON.txt")

    def test_11_windows_trailing_dot_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "TRAILING"):
            self.classifier.normalize("docs/automation/autonomous_generated/x.md.")

    def test_12_lane_a_classification(self):
        result = self.classifier.classify(
            [record("docs/automation/autonomous_generated/x.md", b"ok")]
        )
        self.assertEqual(result.lane, "LOW_NON_EXECUTABLE")
        self.assertFalse(result.approval_required)
        self.assertTrue(result.automatic_fast_forward_promotion)

    def test_13_lane_a_extension_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "EXTENSION"):
            self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.py", b"x=1")]
            )

    def test_14_lane_a_file_count_is_bounded(self):
        items = [
            record(f"docs/automation/autonomous_generated/{i}.md", str(i).encode())
            for i in range(6)
        ]
        with self.assertRaisesRegex(PermissionError, "FILE_COUNT"):
            self.classifier.classify(items)

    def test_15_lane_a_file_size_is_bounded(self):
        content = b"x" * 65537
        with self.assertRaisesRegex(PermissionError, "FILE_SIZE"):
            self.classifier.classify(
                [record("docs/automation/autonomous_generated/large.md", content)]
            )

    def test_16_lane_b_classification_requires_approval(self):
        result = self.classifier.classify(
            [record("phoenix/autonomy/generated_adapters/x.py", b"VALUE=1\n")]
        )
        self.assertEqual(result.lane, "LOW_EXECUTABLE_APPROVAL_BOUND")
        self.assertTrue(result.approval_required)
        self.assertFalse(result.automatic_fast_forward_promotion)

    def test_17_lane_b_requires_executable_source(self):
        with self.assertRaisesRegex(PermissionError, "EXECUTABLE_SOURCE_REQUIRED"):
            self.classifier.classify(
                [record("tests/automation/generated_adapters/test_x.py", b"pass\n")]
            )

    def test_18_protected_config_root_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "PROTECTED_ROOT"):
            self.classifier.classify([record("configs/phoenix/x.json")])

    def test_19_protected_governor_file_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "PROTECTED_EXACT"):
            self.classifier.classify([record("phoenix/autonomy/repository_cycle.py")])

    def test_20_secret_suffix_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "SECRET_SUFFIX"):
            self.classifier.classify(
                [record("docs/automation/autonomous_generated/private.key")]
            )

    def test_21_case_collision_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "CASE_COLLISION"):
            self.classifier.classify(
                [
                    record("docs/automation/autonomous_generated/X.md", b"1"),
                    record("docs/automation/autonomous_generated/x.md", b"2"),
                ]
            )

    def test_22_symlink_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "SYMLINK"):
            self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.md", symlink=True)]
            )

    def test_23_delete_status_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "STATUS_DENY"):
            self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.md", status="D")]
            )

    def test_24_rename_status_is_denied(self):
        with self.assertRaisesRegex(PermissionError, "STATUS_DENY"):
            self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.md", status="R")]
            )

    def test_25_patch_probe_embeds_exact_hash(self):
        patch = b"deterministic patch"
        source = build_patch_probe_source(patch, "LOW_NON_EXECUTABLE")
        self.assertIn(hashlib.sha256(patch).hexdigest(), source)
        self.assertIn(base64.b64encode(patch).decode("ascii"), source)

    def test_26_unavailable_boundary_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            service = self.service(td, FakePhase10Boundary(available=False))
            classification = self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.md")]
            )
            with self.assertRaisesRegex(PermissionError, "SECURITY_BOUNDARY_REQUIRED"):
                service._execute_patch_probe(b"patch", classification)

    def test_27_boundary_mismatch_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            service = self.service(td, FakePhase10Boundary(mismatch=True))
            classification = self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.md")]
            )
            with self.assertRaisesRegex(PermissionError, "DETERMINISTIC_REPLAY_FAILED"):
                service._execute_patch_probe(b"patch", classification)

    def test_28_synthetic_cycle_proof_passes(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.service(td).run_synthetic_proof("1" * 40)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["lane_a_fast_forward_proof"], "PASS")
            self.assertEqual(result["lane_b_approval_pause_proof"], "PASS")
            self.assertFalse(result["automatic_engine_activation"])

    def test_29_attestation_hmac_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            service = self.service(td)
            classification = self.classifier.classify(
                [record("docs/automation/autonomous_generated/x.md")]
            )
            att = service._attestation(
                baseline_sha="2" * 40,
                classification=classification,
                patch_sha256="3" * 64,
                provider=service.probe(),
                candidate_commit=None,
                promoted=False,
                persist=False,
            )
            path = Path(td) / "repository_cycle" / "attestations" / "test.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(att), encoding="utf-8")
            self.assertEqual(service.load_attestation(path)["status"], "LANE_A_PROMOTION_ELIGIBLE")
            att["automatic_engine_activation"] = True
            path.write_text(json.dumps(att), encoding="utf-8")
            with self.assertRaisesRegex(PermissionError, "HMAC"):
                service.load_attestation(path)

    def test_30_candidate_worktree_is_outside_main(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            baseline = initialize_fixture_repository(repo)
            manager = GuardedWorktreeManager(repo)
            candidate = manager.create_candidate(
                "outside-proof", baseline, parent=Path(td) / "candidates"
            )
            with self.assertRaises(ValueError):
                candidate.path.relative_to(repo)
            manager.cleanup(candidate)

    def test_31_candidate_starts_at_exact_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            baseline = initialize_fixture_repository(repo)
            manager = GuardedWorktreeManager(repo)
            candidate = manager.create_candidate(
                "baseline-proof", baseline, parent=Path(td) / "candidates"
            )
            self.assertEqual(manager.git("rev-parse", "HEAD", root=candidate.path), baseline)
            self.assertEqual(manager.snapshot(fetch=False).head, baseline)
            manager.cleanup(candidate)

    def test_32_binary_patch_replay_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            baseline = initialize_fixture_repository(repo)
            manager = GuardedWorktreeManager(repo)
            candidate = manager.create_candidate(
                "replay-proof", baseline, parent=Path(td) / "candidates"
            )
            target = candidate.path / "docs/automation/autonomous_generated/x.md"
            target.parent.mkdir(parents=True)
            target.write_text("replay\n", encoding="utf-8")
            classification = self.classifier.classify(manager.status_records(candidate))
            patch, _ = manager.stage_and_patch(candidate, classification.paths)
            first, second = manager.deterministic_replay(
                candidate, patch, parent=Path(td) / "replays"
            )
            self.assertEqual(first, second)
            self.assertEqual(manager.snapshot(fetch=False).head, baseline)
            manager.cleanup(candidate)


if __name__ == "__main__":
    unittest.main()
