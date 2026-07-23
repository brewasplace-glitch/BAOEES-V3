"""Semantic query and traceability engine."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from .models import GraphEdge, GraphNode, QueryResult
from .repository import KnowledgeGraphRepository


class KnowledgeGraphEngine:
    """Creates, links and queries semantic project knowledge."""

    def __init__(self, repository: Optional[KnowledgeGraphRepository] = None) -> None:
        self.repository = repository or KnowledgeGraphRepository()
        self.audit_log: list[dict[str, Any]] = []

    def create_node(
        self,
        node_type: str,
        label: str,
        properties: Optional[dict] = None,
        source_refs: Optional[list[str]] = None,
    ) -> GraphNode:
        if not node_type.strip() or not label.strip():
            raise ValueError("node_type and label must not be empty")
        node = self.repository.add_node(
            GraphNode(
                node_type=node_type,
                label=label,
                properties=properties or {},
                source_refs=source_refs or [],
            )
        )
        self._audit("node.created", node.node_id)
        return node

    def connect(
        self,
        source_id: str,
        relation_type: str,
        target_id: str,
        properties: Optional[dict] = None,
    ) -> GraphEdge:
        if not relation_type.strip():
            raise ValueError("relation_type must not be empty")
        edge = self.repository.add_edge(
            GraphEdge(
                source_id=source_id,
                relation_type=relation_type,
                target_id=target_id,
                properties=properties or {},
            )
        )
        self._audit("edge.created", edge.edge_id)
        return edge

    def search(
        self,
        *,
        text: Optional[str] = None,
        node_type: Optional[str] = None,
        property_equals: Optional[dict] = None,
    ) -> QueryResult:
        text_norm = text.lower().strip() if text else None
        matches = []
        for node in self.repository.all_nodes():
            if node_type and node.node_type != node_type:
                continue
            if text_norm:
                haystack = " ".join(
                    [
                        node.label,
                        node.node_type,
                        " ".join(node.source_refs),
                        repr(node.properties),
                    ]
                ).lower()
                if text_norm not in haystack:
                    continue
            if property_equals:
                if any(node.properties.get(k) != v for k, v in property_equals.items()):
                    continue
            matches.append(node)

        match_ids = {node.node_id for node in matches}
        edges = [
            edge
            for edge in self.repository.all_edges()
            if edge.source_id in match_ids or edge.target_id in match_ids
        ]
        return QueryResult(nodes=matches, edges=edges)

    def trace(
        self,
        start_id: str,
        *,
        relation_type: Optional[str] = None,
        max_depth: int = 3,
    ) -> QueryResult:
        if self.repository.get_node(start_id) is None:
            raise KeyError(f"Unknown start node: {start_id}")
        if max_depth < 0:
            raise ValueError("max_depth must be zero or greater")

        visited = {start_id}
        queue = deque([(start_id, 0)])
        result_edges = []

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.repository.incident_edges(current):
                if relation_type and edge.relation_type != relation_type:
                    continue
                result_edges.append(edge)
                neighbor = (
                    edge.target_id if edge.source_id == current else edge.source_id
                )
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        nodes = [
            node
            for node_id in visited
            if (node := self.repository.get_node(node_id)) is not None
        ]
        unique_edges = {edge.edge_id: edge for edge in result_edges}
        return QueryResult(nodes=nodes, edges=list(unique_edges.values()))

    def validate_traceability(self) -> dict:
        orphan_nodes = [
            node.node_id
            for node in self.repository.all_nodes()
            if not self.repository.incident_edges(node.node_id)
        ]
        broken_edges = []
        for edge in self.repository.all_edges():
            if self.repository.get_node(edge.source_id) is None:
                broken_edges.append(edge.edge_id)
            elif self.repository.get_node(edge.target_id) is None:
                broken_edges.append(edge.edge_id)
        return {
            "node_count": len(list(self.repository.all_nodes())),
            "edge_count": len(list(self.repository.all_edges())),
            "orphan_nodes": sorted(orphan_nodes),
            "broken_edges": sorted(broken_edges),
            "valid": not broken_edges,
        }

    def _audit(self, event: str, subject: str) -> None:
        self.audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "subject": subject,
            }
        )
