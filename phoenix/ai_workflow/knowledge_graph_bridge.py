"""Knowledge Graph bridge for AI workflow decisions."""

from __future__ import annotations

from phoenix.knowledge_graph import KnowledgeGraphEngine

from .models import DecisionRecord


def write_decisions_to_graph(
    graph: KnowledgeGraphEngine,
    decisions: list[DecisionRecord],
) -> dict[str, str]:
    mapping: dict[str, str] = {}

    for decision in decisions:
        node = graph.create_node(
            node_type="workflow_decision",
            label=decision.step_name,
            properties={
                "status": decision.status,
                "attempts": decision.attempts,
                "rationale": decision.rationale,
                "error": decision.error,
            },
            source_refs=decision.evidence_refs,
        )
        mapping[decision.step_id] = node.node_id

    return mapping
