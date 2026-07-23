param(
    [string]$RepoRoot = "C:\PROJECT-PHOENIX",
    [string]$OutputPath = "outputs/runtime/bb11/workflow_evidence.json"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot
$env:PYTHONPATH = $RepoRoot

$Code = @'
from pathlib import Path

from phoenix.ai_workflow import (
    AIWorkflowEngine,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowStep,
)
from phoenix.ai_workflow.assumptions import add_assumption
from phoenix.ai_workflow.evidence import save_workflow_evidence
from phoenix.ai_workflow.knowledge_graph_bridge import write_decisions_to_graph
from phoenix.knowledge_graph import KnowledgeGraphEngine

context = WorkflowContext(
    project_id="BB11-DEMO",
    inputs={"location": "Bunschoten"},
)

def initialize(ctx):
    ctx.state["initialized"] = True
    return {"initialized": True}

def apply_defaults(ctx):
    return add_assumption(
        ctx,
        key="groundwater_level",
        value=-0.5,
        source="Phoenix default engineering assumptions",
        confidence=0.6,
    )

def produce_result(ctx):
    result = {
        "location": ctx.inputs["location"],
        "groundwater_level": ctx.state["groundwater_level"],
    }
    ctx.evidence.append({"id": "BB11-DEMO-RESULT", "result": result})
    return result

workflow = WorkflowDefinition(
    name="Phoenix Demonstration Workflow",
    version="1.0",
    steps=[
        WorkflowStep("initialize", "project.initialize", initialize),
        WorkflowStep(
            "apply-defaults",
            "assumption.apply",
            apply_defaults,
            depends_on=["initialize"],
        ),
        WorkflowStep(
            "produce-result",
            "result.generate",
            produce_result,
            depends_on=["apply-defaults"],
        ),
    ],
)

decisions = AIWorkflowEngine().execute(workflow, context)
graph = KnowledgeGraphEngine()
write_decisions_to_graph(graph, decisions)

checksum = save_workflow_evidence(
    Path(r"__OUTPUT__"),
    workflow=workflow,
    context=context,
    decisions=decisions,
)

print("Phoenix AI Workflow self-test: PASSED")
print(f"Decisions: {len(decisions)}")
print(f"Successful: {sum(d.status == 'succeeded' for d in decisions)}")
print(f"Assumptions: {len(context.assumptions)}")
print(f"Graph nodes: {len(list(graph.repository.all_nodes()))}")
print(f"Checksum: {checksum}")
'@

$Code = $Code.Replace("__OUTPUT__", $OutputPath.Replace("\", "\\"))
$Code | python -
if ($LASTEXITCODE -ne 0) {
    throw "Phoenix AI Workflow self-test failed."
}
