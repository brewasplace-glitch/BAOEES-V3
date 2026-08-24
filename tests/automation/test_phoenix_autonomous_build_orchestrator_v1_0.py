import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.autonomous_build_orchestrator_v1_0 import (
    AutonomousBuildOrchestrator,
    BuildManifest,
    BuildOrchestratorError,
    BuildStep,
    CommandResult,
    CommandSafetyError,
    CommandSpec,
    ManifestValidationError,
    _is_safe_command,
)


def manifest_dict(**overrides):
    data = {
        "schema_version": "phoenix.autonomous-build-manifest/1.0",
        "build_id": "TEST-BUILD",
        "title": "Test build",
        "branch": "project-phoenix",
        "baseline": "a" * 40,
        "classification": "EXTEND",
        "commit_message": "test: build",
        "expected_scope": ["phoenix/test.py"],
        "existing_markers": ["phoenix/existing"],
        "required_contracts": ["phoenix/required.py"],
        "health_checks": [],
        "steps": [
            {
                "id": "build",
                "kind": "build",
                "command": {"argv": ["python", "-c", "print('ok')"]},
            }
        ],
        "impact_tests": [],
        "smoke_tests": [],
    }
    data.update(overrides)
    return data


class FakeExecutor:
    def __init__(self, returncodes):
        self.returncodes = list(returncodes)
        self.calls = []

    def __call__(self, command, repository):
        self.calls.append(list(command.argv))
        rc = self.returncodes.pop(0) if self.returncodes else 0
        return CommandResult(
            argv=list(command.argv),
            cwd=str(repository),
            returncode=rc,
            stdout="ok" if rc == 0 else "",
            stderr="" if rc == 0 else "failed",
            elapsed_seconds=0.01,
        )


class AutonomousBuildOrchestratorTests(unittest.TestCase):
    def test_manifest_accepts_valid_extend(self):
        manifest = BuildManifest.from_dict(manifest_dict())
        self.assertEqual(manifest.classification, "EXTEND")
        self.assertEqual(manifest.steps[0].step_id, "build")

    def test_manifest_rejects_invalid_classification(self):
        with self.assertRaises(ManifestValidationError):
            BuildManifest.from_dict(manifest_dict(classification="MAGIC"))

    def test_non_reuse_requires_scope(self):
        with self.assertRaises(ManifestValidationError):
            BuildManifest.from_dict(manifest_dict(expected_scope=[]))

    def test_reuse_can_have_no_steps(self):
        manifest = BuildManifest.from_dict(
            manifest_dict(
                classification="REUSE",
                expected_scope=[],
                steps=[],
            )
        )
        self.assertEqual(manifest.classification, "REUSE")

    def test_force_push_is_blocked(self):
        with self.assertRaises(CommandSafetyError):
            _is_safe_command(CommandSpec(("git", "push", "--force", "origin")))

    def test_inline_powershell_is_blocked(self):
        with self.assertRaises(CommandSafetyError):
            _is_safe_command(
                CommandSpec(("powershell.exe", "-Command", "Write-Host hi"))
            )

    def test_self_healing_repairs_then_retries(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            fake = FakeExecutor([1, 0, 0])
            orchestrator = AutonomousBuildOrchestrator(repo, executor=fake)
            step = BuildStep(
                step_id="repairable",
                kind="build",
                command=CommandSpec(("python", "build.py")),
                max_attempts=2,
                repair_actions=(CommandSpec(("python", "repair.py")),),
            )
            from phoenix.autonomy.autonomous_build_orchestrator_v1_0 import RunEvidence
            evidence = RunEvidence(
                build_id="X",
                started_at="now",
                manifest_classification="EXTEND",
            )
            result = orchestrator._run_step_with_healing(step, evidence)
            self.assertTrue(result.ok)
            self.assertEqual(
                fake.calls,
                [
                    ["python", "build.py"],
                    ["python", "repair.py"],
                    ["python", "build.py"],
                ],
            )
            self.assertEqual(len(evidence.repairs), 1)

    def test_self_healing_fails_after_attempt_limit(self):
        with tempfile.TemporaryDirectory() as td:
            fake = FakeExecutor([1, 1])
            orchestrator = AutonomousBuildOrchestrator(td, executor=fake)
            step = BuildStep(
                step_id="bad",
                kind="build",
                command=CommandSpec(("python", "bad.py")),
                max_attempts=2,
            )
            from phoenix.autonomy.autonomous_build_orchestrator_v1_0 import RunEvidence
            evidence = RunEvidence(
                build_id="X",
                started_at="now",
                manifest_classification="EXTEND",
            )
            with self.assertRaises(BuildOrchestratorError):
                orchestrator._run_step_with_healing(step, evidence)

    def test_capability_reuse_when_all_contracts_exist(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "phoenix").mkdir()
            (repo / "phoenix" / "required.py").write_text("x=1", encoding="utf-8")
            (repo / "phoenix" / "existing").mkdir()
            manifest = BuildManifest.from_dict(manifest_dict(health_checks=[]))
            result = AutonomousBuildOrchestrator(repo, executor=FakeExecutor([])).inspect_capability(manifest)
            self.assertEqual(result["classification"], "REUSE")

    def test_capability_extend_when_partial_presence_exists(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "phoenix" / "existing").mkdir(parents=True)
            manifest = BuildManifest.from_dict(manifest_dict(health_checks=[]))
            result = AutonomousBuildOrchestrator(repo, executor=FakeExecutor([])).inspect_capability(manifest)
            self.assertEqual(result["classification"], "EXTEND")

    def test_capability_build_when_nothing_exists(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = BuildManifest.from_dict(manifest_dict(health_checks=[]))
            result = AutonomousBuildOrchestrator(td, executor=FakeExecutor([])).inspect_capability(manifest)
            self.assertEqual(result["classification"], "BUILD")

    def test_capability_repair_when_present_but_health_fails(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "phoenix").mkdir()
            (repo / "phoenix" / "required.py").write_text("x=1", encoding="utf-8")
            (repo / "phoenix" / "existing").mkdir()
            manifest = BuildManifest.from_dict(
                manifest_dict(
                    health_checks=[{"argv": ["python", "health.py"]}]
                )
            )
            result = AutonomousBuildOrchestrator(repo, executor=FakeExecutor([1])).inspect_capability(manifest)
            self.assertEqual(result["classification"], "REPAIR")


if __name__ == "__main__":
    unittest.main()
