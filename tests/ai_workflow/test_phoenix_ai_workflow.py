from pathlib import Path
import tempfile
import unittest

from phoenix.ai_workflow import (
    AIWorkflowEngine,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowPlanner,
    WorkflowStep,
)
from phoenix.ai_workflow.assumptions import add_assumption
from phoenix.ai_workflow.evidence import save_workflow_evidence
from phoenix.ai_workflow.knowledge_graph_bridge import write_decisions_to_graph
from phoenix.knowledge_graph import KnowledgeGraphEngine


class AIWorkflowTests(unittest.TestCase):
    def test_dependency_order(self) -> None:
        workflow = WorkflowDefinition(
            name="order",
            version="1.0",
            steps=[
                WorkflowStep("b", "test", lambda ctx: None, depends_on=["a"]),
                WorkflowStep("a", "test", lambda ctx: None),
            ],
        )
        ordered = WorkflowPlanner().plan(workflow)
        self.assertEqual([step.name for step in ordered], ["a", "b"])

    def test_cycle_detection(self) -> None:
        workflow = WorkflowDefinition(
            name="cycle",
            version="1.0",
            steps=[
                WorkflowStep("a", "test", lambda ctx: None, depends_on=["b"]),
                WorkflowStep("b", "test", lambda ctx: None, depends_on=["a"]),
            ],
        )
        with self.assertRaises(ValueError):
            WorkflowPlanner().plan(workflow)

    def test_successful_execution(self) -> None:
        context = WorkflowContext(project_id="P1")
        workflow = WorkflowDefinition(
            name="simple",
            version="1.0",
            steps=[
                WorkflowStep(
                    "set-value",
                    "state.write",
                    lambda ctx: ctx.state.update({"value": 42}) or 42,
                )
            ],
        )
        decisions = AIWorkflowEngine().execute(workflow, context)
        self.assertEqual(decisions[0].status, "succeeded")
        self.assertEqual(context.state["value"], 42)

    def test_retry(self) -> None:
        context = WorkflowContext(project_id="P1")
        attempts = {"count": 0}

        def flaky(ctx):
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise RuntimeError("temporary")
            return "ok"

        workflow = WorkflowDefinition(
            name="retry",
            version="1.0",
            steps=[WorkflowStep("flaky", "test", flaky, retry_limit=1)],
        )
        decisions = AIWorkflowEngine().execute(workflow, context)
        self.assertEqual(decisions[0].status, "succeeded")
        self.assertEqual(decisions[0].attempts, 2)

    def test_fail_fast(self) -> None:
        context = WorkflowContext(project_id="P1")
        workflow = WorkflowDefinition(
            name="fail-fast",
            version="1.0",
            steps=[
                WorkflowStep("fail", "test", lambda ctx: 1 / 0),
                WorkflowStep("later", "test", lambda ctx: "never"),
            ],
        )
        decisions = AIWorkflowEngine().execute(workflow, context)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].status, "failed")

    def test_conditional_skip(self) -> None:
        context = WorkflowContext(project_id="P1")
        workflow = WorkflowDefinition(
            name="condition",
            version="1.0",
            steps=[
                WorkflowStep(
                    "optional",
                    "test",
                    lambda ctx: "done",
                    condition=lambda ctx: False,
                )
            ],
        )
        decisions = AIWorkflowEngine().execute(workflow, context)
        self.assertEqual(decisions[0].status, "skipped")

    def test_assumption_record(self) -> None:
        context = WorkflowContext(project_id="P1")
        record = add_assumption(
            context,
            key="groundwater_level",
            value=-0.5,
            source="Phoenix default",
            confidence=0.6,
        )
        self.assertEqual(record["value"], -0.5)
        self.assertEqual(context.state["groundwater_level"], -0.5)

    def test_evidence_persistence(self) -> None:
        context = WorkflowContext(project_id="P1")
        workflow = WorkflowDefinition(
            name="evidence",
            version="1.0",
            steps=[WorkflowStep("ok", "test", lambda ctx: "ok")],
        )
        decisions = AIWorkflowEngine().execute(workflow, context)
        with tempfile.TemporaryDirectory() as tmp:
            checksum = save_workflow_evidence(
                Path(tmp) / "evidence.json",
                workflow=workflow,
                context=context,
                decisions=decisions,
            )
            self.assertEqual(len(checksum), 64)

    def test_knowledge_graph_bridge(self) -> None:
        context = WorkflowContext(project_id="P1")
        workflow = WorkflowDefinition(
            name="graph",
            version="1.0",
            steps=[WorkflowStep("ok", "test", lambda ctx: "ok")],
        )
        decisions = AIWorkflowEngine().execute(workflow, context)
        graph = KnowledgeGraphEngine()
        mapping = write_decisions_to_graph(graph, decisions)
        self.assertEqual(len(mapping), 1)
        result = graph.search(node_type="workflow_decision")
        self.assertEqual(len(result.nodes), 1)


if __name__ == "__main__":
    unittest.main()
