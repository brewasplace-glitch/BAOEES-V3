from pathlib import Path
import tempfile
import unittest

from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine
from phoenix.qgis import QGISIntegrationEngine, SpatialExtent
from phoenix.qgis.datasources import validate_geojson, write_geojson
from phoenix.qgis.digital_twin_bridge import publish_project_to_digital_twin
from phoenix.qgis.knowledge_graph_bridge import (
    publish_project_to_knowledge_graph,
)
from phoenix.qgis.spatial_analysis import (
    extent_intersection,
    extent_intersects,
    point_distance,
)


class QGISIntegrationTests(unittest.TestCase):
    def test_extent_validation(self) -> None:
        with self.assertRaises(ValueError):
            SpatialExtent(1, 0, 0, 1).validate()

    def test_extent_intersection(self) -> None:
        left = SpatialExtent(0, 0, 10, 10)
        right = SpatialExtent(5, 5, 15, 15)
        self.assertTrue(extent_intersects(left, right))
        overlap = extent_intersection(left, right)
        self.assertEqual(overlap.xmin, 5)
        self.assertEqual(overlap.ymax, 10)

    def test_distance(self) -> None:
        self.assertEqual(point_distance((0, 0), (3, 4)), 5)

    def test_geojson_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "points.geojson"
            write_geojson(
                path,
                [{
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [5, 52]},
                    "properties": {"name": "A"},
                }],
            )
            payload = validate_geojson(path)
            self.assertEqual(payload["type"], "FeatureCollection")

    def test_project_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            geojson = root / "site.geojson"
            write_geojson(geojson, [])
            engine = QGISIntegrationEngine()
            project = engine.create_project(
                name="Phoenix GIS",
                project_id="GIS-001",
            )
            engine.add_file_layer(
                project,
                name="Site",
                path=geojson,
                geometry_type="point",
            )
            result = engine.save_project(
                project,
                manifest_path=root / "project.json",
                qgs_path=root / "project.qgs",
            )
            self.assertEqual(len(result["manifest_checksum_sha256"]), 64)
            self.assertTrue((root / "project.qgs").exists())

    def test_digital_twin_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = QGISIntegrationEngine()
            project = engine.create_project(
                name="Twin GIS",
                project_id="GIS-002",
            )
            project.layers.append(
                engine.layers.add(
                    __import__("phoenix.qgis", fromlist=["GISLayer"]).GISLayer(
                        name="Buildings",
                        source="memory:buildings",
                        provider="memory",
                        geometry_type="polygon",
                    )
                )
            )
            db = ProjectDatabase("GIS-002", Path(tmp))
            mapping = publish_project_to_digital_twin(project, db)
            self.assertEqual(len(mapping), 2)
            self.assertEqual(len(list(db.relationships.all())), 1)

    def test_knowledge_graph_bridge(self) -> None:
        engine = QGISIntegrationEngine()
        project = engine.create_project(
            name="Graph GIS",
            project_id="GIS-003",
        )
        graph = KnowledgeGraphEngine()
        mapping = publish_project_to_knowledge_graph(project, graph)
        self.assertIn("project", mapping)
        self.assertEqual(len(graph.search(node_type="gis_project").nodes), 1)

    def test_runtime_probe(self) -> None:
        info = QGISIntegrationEngine().runtime.probe()
        self.assertIn(info.mode, {"native", "offline"})


if __name__ == "__main__":
    unittest.main()
