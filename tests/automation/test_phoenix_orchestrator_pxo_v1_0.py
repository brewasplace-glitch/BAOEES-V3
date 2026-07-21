import unittest

from phoenix.orchestration import (
    OrchestrationError,
    OrchestrationState,
    PhoenixOrchestrator,
    ProjectContext,
)


class PhoenixOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = PhoenixOrchestrator()
        self.context = ProjectContext(
            project_id="PHX-APT-001",
            instruction="Ontwerp een appartementencomplex op deze locatie.",
            location_reference="kaart://testlocatie",
            selected_variant_id="V04",
            selected_variant_fingerprint="abc123",
        )

    def test_plan_contains_complete_engine_graph(self):
        plan = self.orchestrator.create_plan(self.context)
        self.assertEqual(len(plan.engines), 20)
        self.assertEqual(plan.state, OrchestrationState.READY)
        self.assertEqual(
            [e.engine_id for e in self.orchestrator.next_executable_engines(plan)],
            ["gis"],
        )

    def test_dependencies_unlock_in_order(self):
        plan = self.orchestrator.create_plan(self.context)
        plan = self.orchestrator.start_engine(plan, "gis")
        self.assertEqual(plan.state, OrchestrationState.RUNNING)
        plan = self.orchestrator.complete_engine(
            plan,
            "gis",
            outputs=("site_context.json",),
            evidence=("gis-test-evidence",),
        )
        ready = {e.engine_id for e in self.orchestrator.next_executable_engines(plan)}
        self.assertIn("geotechnical", ready)
        self.assertIn("traffic", ready)
        self.assertIn("fire_safety", ready)

    def test_engine_cannot_complete_without_running(self):
        plan = self.orchestrator.create_plan(self.context)
        with self.assertRaises(OrchestrationError):
            self.orchestrator.complete_engine(
                plan,
                "gis",
                outputs=("x",),
                evidence=("y",),
            )

    def test_completed_engine_requires_output_and_evidence(self):
        plan = self.orchestrator.start_engine(
            self.orchestrator.create_plan(self.context),
            "gis",
        )
        with self.assertRaises(OrchestrationError):
            self.orchestrator.complete_engine(
                plan,
                "gis",
                outputs=(),
                evidence=("evidence",),
            )

    def test_failure_is_traceable(self):
        plan = self.orchestrator.create_plan(self.context)
        failed = self.orchestrator.fail_engine(plan, "gis", "GIS unavailable")
        self.assertEqual(failed.state, OrchestrationState.FAILED)
        self.assertIn("engine-failed:gis", failed.audit_log)

    def test_missing_available_engine_blocks_plan(self):
        context = ProjectContext(
            project_id="PHX-APT-002",
            instruction="Ontwerp een appartementencomplex.",
            location_reference="kaart://testlocatie",
            selected_variant_id="V01",
            selected_variant_fingerprint="fp",
            available_engines=("gis",),
        )
        plan = self.orchestrator.create_plan(context)
        self.assertEqual(plan.state, OrchestrationState.READY)
        self.assertEqual(plan.engine_map()["geotechnical"].status, "blocked")

    def test_status_summary_is_stable(self):
        plan = self.orchestrator.create_plan(self.context)
        summary = self.orchestrator.status_summary(plan)
        self.assertEqual(summary["project_id"], "PHX-APT-001")
        self.assertEqual(summary["next_engines"], ["gis"])
        self.assertEqual(len(summary["plan_fingerprint"]), 64)


if __name__ == "__main__":
    unittest.main()
