"""Knowledge Graph bridge for structural-analysis traceability."""

from phoenix.knowledge_graph import KnowledgeGraphEngine
from .models import AnalysisResult, StructuralModel


def publish_model_and_result_to_graph(
    graph: KnowledgeGraphEngine,
    model: StructuralModel,
    result: AnalysisResult,
) -> dict[str, str]:
    model_node = graph.create_node(
        node_type="structural_model",
        label=model.name,
        properties={"model_id": model.model_id, "dimension": model.dimension},
    )
    result_node = graph.create_node(
        node_type="structural_analysis_result",
        label=f"{model.name} result",
        properties={
            "analysis_type": result.analysis_type,
            "success": result.success,
            "runtime_mode": result.runtime_mode,
            "checksum_sha256": result.checksum_sha256,
        },
    )
    graph.connect(result_node.node_id, "analyzes", model_node.node_id)
    return {"model": model_node.node_id, "result": result_node.node_id}
