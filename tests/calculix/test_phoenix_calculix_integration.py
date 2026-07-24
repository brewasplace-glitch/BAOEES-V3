from pathlib import Path
import tempfile, unittest
from phoenix.calculix import *
from phoenix.calculix.engine import render_inp
from phoenix.calculix.bridges import publish_to_digital_twin, publish_to_knowledge_graph
from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine

def model():
    n1,n2=Node(0,0,0),Node(3,0,0)
    m=Material("Steel",210e9,0.3,7850)
    e=BeamElement(n1.node_id,n2.node_id,m.material_id,0.01,8e-6,8e-6,1e-5)
    return FEModel("Cantilever","CCX-001",[n1,n2],[m],[e],
        [BoundaryCondition(n1.node_id,1,6)],[ConcentratedLoad(n2.node_id,2,-10000)])

class Tests(unittest.TestCase):
    def test_model(self): model().validate()
    def test_deck(self):
        deck=render_inp(model())
        self.assertIn("*ELEMENT, TYPE=B31",deck); self.assertIn("*CLOAD",deck)
    def test_offline_and_equilibrium(self):
        m=model()
        with tempfile.TemporaryDirectory() as d:
            r=CalculiXIntegrationEngine().analyze_and_save(m,Path(d)/"w",Path(d)/"e.json",False)
            self.assertTrue(r.success); self.assertEqual(r.runtime_mode,"offline")
            self.assertLess(r.displacements[m.nodes[1].node_id][1],0)
            self.assertAlmostEqual(r.reactions[m.nodes[0].node_id][1],10000)
            self.assertEqual(len(r.checksum_sha256),64)
    def test_runtime(self):
        self.assertIn(CalculiXRuntimeProbe().probe().mode,{"native","offline"})
    def test_bridges(self):
        m=model()
        with tempfile.TemporaryDirectory() as d:
            r=CalculiXIntegrationEngine().analyze_and_save(m,Path(d)/"w",Path(d)/"e.json",False)
            self.assertEqual(len(publish_to_digital_twin(ProjectDatabase("x",Path(d)/"db"),m,r)),2)
            g=KnowledgeGraphEngine()
            self.assertEqual(len(publish_to_knowledge_graph(g,m,r)),2)
    def test_invalid_material(self):
        m=model(); m.materials[0].elastic_modulus=0
        with self.assertRaises(ValueError): m.validate()

if __name__=="__main__": unittest.main()
