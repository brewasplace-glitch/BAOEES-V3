"""QGIS-compatible project manifest generation."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from phoenix.database.persistence import save_json

from .models import GISProject


class QGISProjectManager:
    """Writes a Phoenix GIS manifest and a minimal QGIS .qgs project."""

    def save_manifest(self, project: GISProject, path: str | Path) -> str:
        project.validate()
        return save_json(Path(path), project.to_dict())

    def write_qgs(self, project: GISProject, path: str | Path) -> Path:
        project.validate()
        root = ET.Element("qgis", {
            "projectname": project.name,
            "version": "3.0.0",
        })
        title = ET.SubElement(root, "title")
        title.text = project.name

        crs = ET.SubElement(root, "projectCrs")
        authid = ET.SubElement(crs, "authid")
        authid.text = project.crs

        tree_root = ET.SubElement(root, "layer-tree-group", {
            "name": "",
            "checked": "Qt::Checked",
            "expanded": "1",
        })

        project_layers = ET.SubElement(root, "projectlayers")
        for layer in project.layers:
            ET.SubElement(tree_root, "layer-tree-layer", {
                "id": layer.layer_id,
                "name": layer.name,
                "checked": "Qt::Checked" if layer.visible else "Qt::Unchecked",
            })
            maplayer = ET.SubElement(project_layers, "maplayer", {
                "type": "vector" if layer.provider != "gdal" else "raster",
                "geometry": layer.geometry_type,
            })
            ET.SubElement(maplayer, "id").text = layer.layer_id
            ET.SubElement(maplayer, "layername").text = layer.name
            ET.SubElement(maplayer, "datasource").text = layer.source
            ET.SubElement(maplayer, "provider").text = layer.provider

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(root).write(
            output,
            encoding="utf-8",
            xml_declaration=True,
        )
        return output
