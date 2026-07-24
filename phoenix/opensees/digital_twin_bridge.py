"""Digital Twin bridge for structural models and results."""

from phoenix.database import ProjectDatabase
from .models import AnalysisResult, StructuralModel


def publish_model_and_result(
    database: ProjectDatabase,
    model: StructuralModel,
    result: AnalysisResult,
) -> dict[str, str]:
    model_object = database.create_object(
        "structural_model",
        model.name,
        properties={
            "model_id": model.model_id,
            "dimension": model.dimension,
            "node_count": len(model.nodes),
            "element_count": len(model.truss_elements),
        },
    )
    result_object = database.create_object(
        "structural_analysis_result",
        f"{model.name} result",
        properties={
            "analysis_type": result.analysis_type,
            "success": result.success,
            "runtime_mode": result.runtime_mode,
            "checksum_sha256": result.checksum_sha256,
        },
    )
    database.relate(result_object.object_id, "analyzes", model_object.object_id)
    return {"model": model_object.object_id, "result": result_object.object_id}
