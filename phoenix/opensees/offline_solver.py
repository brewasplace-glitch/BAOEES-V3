"""Deterministic 2D truss solver for offline verification."""

from __future__ import annotations

from math import hypot

import numpy as np

from .models import AnalysisResult, StructuralModel


def solve_linear_2d_truss(model: StructuralModel) -> AnalysisResult:
    model.validate()
    if model.dimension != 2:
        raise ValueError("offline solver supports only 2D truss models")
    if not model.truss_elements:
        raise ValueError("model contains no truss elements")

    index = {node.node_id: i for i, node in enumerate(model.nodes)}
    dof_count = 2 * len(model.nodes)
    stiffness = np.zeros((dof_count, dof_count), dtype=float)
    force = np.zeros(dof_count, dtype=float)

    for load in model.loads:
        base = 2 * index[load.node_id]
        force[base] += load.fx
        force[base + 1] += load.fy

    for element in model.truss_elements:
        start = model.nodes[index[element.start_node_id]]
        end = model.nodes[index[element.end_node_id]]
        dx = end.x - start.x
        dy = end.y - start.y
        length = hypot(dx, dy)
        if length <= 0:
            raise ValueError("zero-length element")
        c = dx / length
        s = dy / length
        factor = element.area * element.elastic_modulus / length
        local = factor * np.array([
            [c*c, c*s, -c*c, -c*s],
            [c*s, s*s, -c*s, -s*s],
            [-c*c, -c*s, c*c, c*s],
            [-c*s, -s*s, c*s, s*s],
        ])
        dofs = [
            2 * index[element.start_node_id],
            2 * index[element.start_node_id] + 1,
            2 * index[element.end_node_id],
            2 * index[element.end_node_id] + 1,
        ]
        for i, row in enumerate(dofs):
            for j, col in enumerate(dofs):
                stiffness[row, col] += local[i, j]

    restrained = set()
    for condition in model.boundary_conditions:
        base = 2 * index[condition.node_id]
        if condition.ux:
            restrained.add(base)
        if condition.uy:
            restrained.add(base + 1)

    free = [dof for dof in range(dof_count) if dof not in restrained]
    if not free:
        raise ValueError("model has no free degrees of freedom")

    kff = stiffness[np.ix_(free, free)]
    ff = force[free]
    try:
        uf = np.linalg.solve(kff, ff)
    except np.linalg.LinAlgError as exc:
        raise ValueError("singular structural model") from exc

    displacement = np.zeros(dof_count, dtype=float)
    displacement[free] = uf
    reactions_vector = stiffness @ displacement - force

    node_displacements = {}
    reactions = {}
    for node in model.nodes:
        base = 2 * index[node.node_id]
        node_displacements[node.node_id] = [
            float(displacement[base]),
            float(displacement[base + 1]),
            0.0,
        ]
        reactions[node.node_id] = [
            float(reactions_vector[base]),
            float(reactions_vector[base + 1]),
            0.0,
        ]

    element_forces = {}
    for element in model.truss_elements:
        start = model.nodes[index[element.start_node_id]]
        end = model.nodes[index[element.end_node_id]]
        dx = end.x - start.x
        dy = end.y - start.y
        length = hypot(dx, dy)
        c = dx / length
        s = dy / length
        dofs = [
            2 * index[element.start_node_id],
            2 * index[element.start_node_id] + 1,
            2 * index[element.end_node_id],
            2 * index[element.end_node_id] + 1,
        ]
        extension = np.dot(
            np.array([-c, -s, c, s]),
            displacement[dofs],
        )
        axial_force = (
            element.area * element.elastic_modulus / length * extension
        )
        element_forces[element.element_id] = float(axial_force)

    return AnalysisResult(
        model_id=model.model_id,
        analysis_type="linear_static_2d_truss",
        success=True,
        runtime_mode="offline",
        node_displacements=node_displacements,
        element_forces=element_forces,
        reactions=reactions,
        diagnostics={
            "node_count": len(model.nodes),
            "element_count": len(model.truss_elements),
            "free_dof_count": len(free),
        },
    )
