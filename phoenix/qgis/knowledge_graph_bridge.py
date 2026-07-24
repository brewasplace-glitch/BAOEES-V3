"""Bridge from GIS project metadata to the BB10 Knowledge Graph."""

from __future__ import annotations

from phoenix.knowledge_graph import KnowledgeGraphEngine

from .models import GISProject


def publish_project_to_knowledge_graph(
    project: GISProject,
    graph: KnowledgeGraphEngine,
) -> dict[str, str]:
    project.validate()
    project_node = graph.create_node(
        node_type="gis_project",
        label=project.name,
        properties={
            "project_id": project.project_id,
            "crs": project.crs,
        },
    )
    mapping = {"project": project_node.node_id}

    for layer in project.layers:
        layer_node = graph.create_node(
            node_type="gis_layer",
            label=layer.name,
            properties={
                "provider": layer.provider,
                "source": layer.source,
                "geometry_type": layer.geometry_type,
                "crs": layer.crs,
            },
        )
        graph.connect(project_node.node_id, "contains", layer_node.node_id)
        mapping[layer.layer_id] = layer_node.node_id

    return mapping
