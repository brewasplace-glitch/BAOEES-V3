"""Bridge between GIS projects and the BB9 Digital Twin."""

from __future__ import annotations

from phoenix.database import ProjectDatabase

from .models import GISProject


def publish_project_to_digital_twin(
    project: GISProject,
    database: ProjectDatabase,
) -> dict[str, str]:
    project.validate()
    project_object = database.create_object(
        "gis_project",
        project.name,
        properties={
            "crs": project.crs,
            "layer_count": len(project.layers),
        },
        metadata={
            "phoenix_project_id": project.project_id,
        },
    )

    mapping = {"project": project_object.object_id}

    for layer in project.layers:
        layer_object = database.create_object(
            "gis_layer",
            layer.name,
            properties={
                "source": layer.source,
                "provider": layer.provider,
                "geometry_type": layer.geometry_type,
                "crs": layer.crs,
            },
            metadata=layer.metadata,
        )
        database.relate(
            project_object.object_id,
            "contains",
            layer_object.object_id,
        )
        mapping[layer.layer_id] = layer_object.object_id

    return mapping
