"""Native OpenSeesPy solver adapter."""

from __future__ import annotations

from .models import AnalysisResult, StructuralModel


def solve_with_openseespy(model: StructuralModel) -> AnalysisResult:
    model.validate()
    if model.dimension != 2:
        raise ValueError("BB13 native solver currently supports 2D trusses")

    try:
        import openseespy.opensees as ops
    except ImportError as exc:
        raise RuntimeError("OpenSeesPy is not available") from exc

    ops.wipe()
    ops.model("basic", "-ndm", 2, "-ndf", 2)

    tag_by_node = {}
    for tag, node in enumerate(model.nodes, start=1):
        tag_by_node[node.node_id] = tag
        ops.node(tag, node.x, node.y)

    for condition in model.boundary_conditions:
        ops.fix(
            tag_by_node[condition.node_id],
            int(condition.ux),
            int(condition.uy),
        )

    material_tags = {}
    for tag, element in enumerate(model.truss_elements, start=1):
        key = element.elastic_modulus
        if key not in material_tags:
            material_tags[key] = len(material_tags) + 1
            ops.uniaxialMaterial("Elastic", material_tags[key], key)
        ops.element(
            "truss",
            tag,
            tag_by_node[element.start_node_id],
            tag_by_node[element.end_node_id],
            element.area,
            material_tags[key],
        )

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for load in model.loads:
        ops.load(tag_by_node[load.node_id], load.fx, load.fy)

    ops.system("BandSPD")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    code = ops.analyze(1)
    if code != 0:
        raise RuntimeError(f"OpenSees analysis failed with code {code}")

    node_displacements = {}
    reactions = {}
    ops.reactions()
    for node in model.nodes:
        tag = tag_by_node[node.node_id]
        node_displacements[node.node_id] = [
            float(ops.nodeDisp(tag, 1)),
            float(ops.nodeDisp(tag, 2)),
            0.0,
        ]
        reactions[node.node_id] = [
            float(ops.nodeReaction(tag, 1)),
            float(ops.nodeReaction(tag, 2)),
            0.0,
        ]

    element_forces = {}
    for tag, element in enumerate(model.truss_elements, start=1):
        response = ops.eleResponse(tag, "axialForce")
        element_forces[element.element_id] = float(response[0])

    ops.wipe()
    return AnalysisResult(
        model_id=model.model_id,
        analysis_type="linear_static_2d_truss",
        success=True,
        runtime_mode="native",
        node_displacements=node_displacements,
        element_forces=element_forces,
        reactions=reactions,
        diagnostics={
            "node_count": len(model.nodes),
            "element_count": len(model.truss_elements),
        },
    )
