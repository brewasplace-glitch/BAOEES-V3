from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from uuid import uuid4

@dataclass
class Node:
    x: float
    y: float
    z: float
    node_id: str = field(default_factory=lambda: str(uuid4()))
    def to_dict(self): return asdict(self)

@dataclass
class Material:
    name: str
    elastic_modulus: float
    poisson_ratio: float
    density: float = 0.0
    material_id: str = field(default_factory=lambda: str(uuid4()))
    def validate(self):
        if not self.name.strip(): raise ValueError("material name required")
        if self.elastic_modulus <= 0: raise ValueError("elastic modulus must be positive")
        if not (-1.0 < self.poisson_ratio < 0.5): raise ValueError("invalid poisson ratio")
        if self.density < 0: raise ValueError("density must not be negative")
    def to_dict(self): self.validate(); return asdict(self)

@dataclass
class BeamElement:
    start_node_id: str
    end_node_id: str
    material_id: str
    area: float
    second_moment_y: float
    second_moment_z: float
    torsional_constant: float
    element_id: str = field(default_factory=lambda: str(uuid4()))
    def validate(self):
        if self.start_node_id == self.end_node_id: raise ValueError("beam nodes must differ")
        for value in (self.area, self.second_moment_y, self.second_moment_z, self.torsional_constant):
            if value <= 0: raise ValueError("section values must be positive")
    def to_dict(self): self.validate(); return asdict(self)

@dataclass
class BoundaryCondition:
    node_id: str
    dof_start: int
    dof_end: int
    value: float = 0.0
    def validate(self):
        if not (1 <= self.dof_start <= self.dof_end <= 6): raise ValueError("invalid dof range")
    def to_dict(self): self.validate(); return asdict(self)

@dataclass
class ConcentratedLoad:
    node_id: str
    dof: int
    magnitude: float
    case: str = "LC1"
    def validate(self):
        if not (1 <= self.dof <= 6): raise ValueError("invalid load dof")
    def to_dict(self): self.validate(); return asdict(self)

@dataclass
class FEModel:
    name: str
    model_id: str
    nodes: list[Node] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    beam_elements: list[BeamElement] = field(default_factory=list)
    boundary_conditions: list[BoundaryCondition] = field(default_factory=list)
    concentrated_loads: list[ConcentratedLoad] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    def validate(self):
        if not self.name.strip() or not self.model_id.strip(): raise ValueError("model identity required")
        node_ids = {n.node_id for n in self.nodes}
        mat_ids = {m.material_id for m in self.materials}
        if len(node_ids) != len(self.nodes): raise ValueError("duplicate nodes")
        if len(mat_ids) != len(self.materials): raise ValueError("duplicate materials")
        for m in self.materials: m.validate()
        for e in self.beam_elements:
            e.validate()
            if e.start_node_id not in node_ids or e.end_node_id not in node_ids: raise KeyError("unknown beam node")
            if e.material_id not in mat_ids: raise KeyError("unknown material")
        for item in [*self.boundary_conditions, *self.concentrated_loads]:
            item.validate()
            if item.node_id not in node_ids: raise KeyError("unknown referenced node")
    def to_dict(self):
        self.validate()
        return {
            "name": self.name, "model_id": self.model_id,
            "nodes": [x.to_dict() for x in self.nodes],
            "materials": [x.to_dict() for x in self.materials],
            "beam_elements": [x.to_dict() for x in self.beam_elements],
            "boundary_conditions": [x.to_dict() for x in self.boundary_conditions],
            "concentrated_loads": [x.to_dict() for x in self.concentrated_loads],
            "metadata": self.metadata,
        }

@dataclass
class FEAnalysisResult:
    model_id: str
    analysis_type: str
    success: bool
    runtime_mode: str
    displacements: dict[str, list[float]] = field(default_factory=dict)
    reactions: dict[str, list[float]] = field(default_factory=dict)
    element_results: dict[str, dict[str, float]] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    checksum_sha256: Optional[str] = None
    def to_dict(self): return asdict(self)
