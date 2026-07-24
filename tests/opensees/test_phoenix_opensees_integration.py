from pathlib import Path
import tempfile
import unittest

from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine
from phoenix.opensees import (
    BoundaryCondition,
    Load,
    Node,
    OpenSeesIntegrationEngine,
    StructuralModel,
    TrussElement,
)
from phoenix.opensees.digital_twin_bridge import publish_model_and_result
from phoenix.opensees.knowledge_graph_bridge import (
    publish_model_and_result_to_graph,
)


def triangle_model() -> StructuralModel:
    n1 = Node(0.0, 0.0)
    n2 = Node(4.0, 0.0)
    n3 = Node(2.0, 3.0)
    return StructuralModel(
        name="Triangle Truss",
        model_id="TRUSS-001",
        nodes=[n1, n2, n3],
        truss_elements=[
            TrussElement(n1.node_id, n2.node_id, 0.01, 210e9),
            TrussElement(n1.node_id, n3.node_id, 0.01, 210e9),
            TrussElement(n2.node_id, n3.node_id, 0.01, 210e9),
        ],
        boundary_conditions=[
            BoundaryCondition(n1.node_id, True, True),
            BoundaryCondition(n2.node_id, False, True),
        ],
        loads=[Load(n3.node_id, fy=-100000.0)],
    )


class OpenSeesIntegrationTests(unittest.TestCase):
    def test_model_validation(self) -> None:
        triangle_model().validate()

    def test_offline_analysis(self) -> None:
        model = triangle_model()
        result = OpenSeesIntegrationEngine().analyze(model, prefer_native=False)
        self.assertTrue(result.success)
        self.assertEqual(result.runtime_mode, "offline")
        self.assertLess(result.node_displacements[model.nodes[2].node_id][1], 0)

    def test_reaction_equilibrium(self) -> None:
        model = triangle_model()
        result = OpenSeesIntegrationEngine().analyze(model, prefer_native=False)
        vertical_reaction = sum(r[1] for r in result.reactions.values())
        self.assertAlmostEqual(vertical_reaction, 100000.0, places=4)

    def test_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = OpenSeesIntegrationEngine().analyze_and_save(
                triangle_model(),
                evidence_path=Path(tmp) / "analysis.json",
                prefer_native=False,
            )
            self.assertEqual(len(result.checksum_sha256), 64)

    def test_runtime_probe(self) -> None:
        info = OpenSeesIntegrationEngine().runtime.probe()
        self.assertIn(info.mode, {"native", "offline"})

    def test_digital_twin_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model = triangle_model()
            result = OpenSeesIntegrationEngine().analyze(model, prefer_native=False)
            db = ProjectDatabase("TRUSS-001", Path(tmp))
            mapping = publish_model_and_result(db, model, result)
            self.assertEqual(len(mapping), 2)

    def test_knowledge_graph_bridge(self) -> None:
        model = triangle_model()
        result = OpenSeesIntegrationEngine().analyze(model, prefer_native=False)
        graph = KnowledgeGraphEngine()
        mapping = publish_model_and_result_to_graph(graph, model, result)
        self.assertEqual(len(mapping), 2)
        self.assertEqual(
            len(graph.search(node_type="structural_analysis_result").nodes),
            1,
        )

    def test_invalid_element_area(self) -> None:
        model = triangle_model()
        model.truss_elements[0].area = 0
        with self.assertRaises(ValueError):
            model.validate()


if __name__ == "__main__":
    unittest.main()
