"""In-memory graph repository with deterministic JSON persistence."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Iterable, Optional

from phoenix.database.persistence import load_json, save_json

from .models import GraphEdge, GraphNode


class KnowledgeGraphRepository:
    schema_version = "1.0"

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

    def add_node(self, node: GraphNode) -> GraphNode:
        if node.node_id in self._nodes:
            raise ValueError(f"Node already exists: {node.node_id}")
        self._nodes[node.node_id] = deepcopy(node)
        return deepcopy(node)

    def add_edge(self, edge: GraphEdge) -> GraphEdge:
        if edge.edge_id in self._edges:
            raise ValueError(f"Edge already exists: {edge.edge_id}")
        if edge.source_id not in self._nodes:
            raise KeyError(f"Unknown source node: {edge.source_id}")
        if edge.target_id not in self._nodes:
            raise KeyError(f"Unknown target node: {edge.target_id}")
        self._edges[edge.edge_id] = deepcopy(edge)
        return deepcopy(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        node = self._nodes.get(node_id)
        return deepcopy(node) if node is not None else None

    def all_nodes(self) -> Iterable[GraphNode]:
        return [deepcopy(node) for node in self._nodes.values()]

    def all_edges(self) -> Iterable[GraphEdge]:
        return [deepcopy(edge) for edge in self._edges.values()]

    def incident_edges(self, node_id: str) -> list[GraphEdge]:
        return [
            deepcopy(edge)
            for edge in self._edges.values()
            if edge.source_id == node_id or edge.target_id == node_id
        ]

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "nodes": [node.to_dict() for node in self.all_nodes()],
            "edges": [edge.to_dict() for edge in self.all_edges()],
        }

    def save(self, path: Path | str) -> str:
        return save_json(Path(path), self.to_dict())

    def load(self, path: Path | str) -> None:
        payload = load_json(Path(path))
        if payload.get("schema_version") != self.schema_version:
            raise ValueError("Knowledge Graph schema version mismatch")
        self._nodes.clear()
        self._edges.clear()
        for record in payload.get("nodes", []):
            node = GraphNode(**record)
            self._nodes[node.node_id] = node
        for record in payload.get("edges", []):
            edge = GraphEdge(**record)
            self._edges[edge.edge_id] = edge
