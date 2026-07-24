"""Structural data models for the Phoenix OpenSees integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass
class Node:
    x: float
    y: float
    z: float = 0.0
    node_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrussElement:
    start_node_id: str
    end_node_id: str
    area: float
    elastic_modulus: float
    density: float = 0.0
    element_id: str = field(default_factory=lambda: str(uuid4()))

    def validate(self) -> None:
        if self.area <= 0:
            raise ValueError("element area must be positive")
        if self.elastic_modulus <= 0:
            raise ValueError("elastic modulus must be positive")
        if self.start_node_id == self.end_node_id:
            raise ValueError("element nodes must be different")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class BoundaryCondition:
    node_id: str
    ux: bool
    uy: bool
    uz: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Load:
    node_id: str
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    case: str = "LC1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StructuralModel:
    name: str
    model_id: str
    dimension: int = 2
    nodes: list[Node] = field(default_factory=list)
    truss_elements: list[TrussElement] = field(default_factory=list)
    boundary_conditions: list[BoundaryCondition] = field(default_factory=list)
    loads: list[Load] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.name.strip() or not self.model_id.strip():
            raise ValueError("model name and model_id must not be empty")
        if self.dimension not in {2, 3}:
            raise ValueError("dimension must be 2 or 3")
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("duplicate node identifiers")
        for element in self.truss_elements:
            element.validate()
            if element.start_node_id not in node_ids:
                raise KeyError("unknown element start node")
            if element.end_node_id not in node_ids:
                raise KeyError("unknown element end node")
        for item in [*self.boundary_conditions, *self.loads]:
            if item.node_id not in node_ids:
                raise KeyError("boundary condition or load references unknown node")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            **asdict(self),
            "nodes": [node.to_dict() for node in self.nodes],
            "truss_elements": [
                element.to_dict() for element in self.truss_elements
            ],
            "boundary_conditions": [
                condition.to_dict() for condition in self.boundary_conditions
            ],
            "loads": [load.to_dict() for load in self.loads],
        }


@dataclass
class AnalysisResult:
    model_id: str
    analysis_type: str
    success: bool
    runtime_mode: str
    node_displacements: Dict[str, list[float]] = field(default_factory=dict)
    element_forces: Dict[str, float] = field(default_factory=dict)
    reactions: Dict[str, list[float]] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    checksum_sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
