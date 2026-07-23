from pathlib import Path
import tempfile
import unittest

from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine, KnowledgeGraphRepository
from phoenix.knowledge_graph.digital_twin_bridge import import_project_database


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = KnowledgeGraphEngine()

    def test_create_and_search_node(self) -> None:
        self.graph.create_node("document", "Foundation Report")
        result = self.graph.search(text="foundation")
        self.assertEqual(len(result.nodes), 1)

    def test_edge_requires_existing_nodes(self) -> None:
        node = self.graph.create_node("building", "A")
        with self.assertRaises(KeyError):
            self.graph.connect(node.node_id, "contains", "missing")

    def test_trace_follows_relations(self) -> None:
        a = self.graph.create_node("building", "A")
        b = self.graph.create_node("storey", "B")
        c = self.graph.create_node("space", "C")
        self.graph.connect(a.node_id, "contains", b.node_id)
        self.graph.connect(b.node_id, "contains", c.node_id)
        result = self.graph.trace(a.node_id, relation_type="contains", max_depth=2)
        self.assertEqual(len(result.nodes), 3)
        self.assertEqual(len(result.edges), 2)

    def test_property_filter(self) -> None:
        self.graph.create_node(
            "requirement",
            "Fire resistance",
            properties={"status": "accepted"},
        )
        result = self.graph.search(property_equals={"status": "accepted"})
        self.assertEqual(len(result.nodes), 1)

    def test_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            self.graph.create_node("standard", "NEN")
            checksum = self.graph.repository.save(path)
            self.assertEqual(len(checksum), 64)
            other = KnowledgeGraphRepository()
            other.load(path)
            self.assertEqual(len(list(other.all_nodes())), 1)

    def test_digital_twin_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = ProjectDatabase("KG-TEST", Path(tmp))
            building = db.create_object("building", "Main")
            floor = db.create_object("storey", "Ground")
            db.relate(building.object_id, "contains", floor.object_id)
            mapping = import_project_database(db, self.graph)
            self.assertEqual(len(mapping), 2)
            validation = self.graph.validate_traceability()
            self.assertEqual(validation["edge_count"], 1)
            self.assertTrue(validation["valid"])

    def test_orphan_detection(self) -> None:
        node = self.graph.create_node("document", "Unlinked")
        validation = self.graph.validate_traceability()
        self.assertIn(node.node_id, validation["orphan_nodes"])


if __name__ == "__main__":
    unittest.main()
