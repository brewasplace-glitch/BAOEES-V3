"""Bridge from BB9 Digital Twin objects to BB10 Knowledge Graph nodes."""

from __future__ import annotations

from phoenix.database import ProjectDatabase

from .engine import KnowledgeGraphEngine


def import_project_database(
    database: ProjectDatabase,
    graph: KnowledgeGraphEngine,
) -> dict[str, str]:
    """Import Digital Twin objects and relationships into the graph."""
    mapping: dict[str, str] = {}

    for twin_object in database.objects.all():
        node = graph.create_node(
            node_type=twin_object.object_type,
            label=twin_object.name,
            properties={
                **twin_object.properties,
                "digital_twin_object_id": twin_object.object_id,
                "version": twin_object.version,
            },
            source_refs=[twin_object.object_id],
        )
        mapping[twin_object.object_id] = node.node_id

    for relation in database.relationships.all():
        graph.connect(
            mapping[relation.source_id],
            relation.relationship_type,
            mapping[relation.target_id],
            properties={
                **relation.properties,
                "digital_twin_relationship_id": relation.relationship_id,
            },
        )

    return mapping
