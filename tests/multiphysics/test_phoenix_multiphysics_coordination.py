from pathlib import Path
import tempfile, unittest
from phoenix.multiphysics import *
from phoenix.multiphysics.bridges import publish_to_digital_twin,publish_to_knowledge_graph
from phoenix.database import ProjectDatabase
from phoenix.knowledge_graph import KnowledgeGraphEngine

def make_workflow():
    gis=AnalysisTask("QGIS","prepare_geometry",{"metrics":{"span":3.0}})
    os=AnalysisTask("OpenSees","structural_analysis",
        {"metrics":{"tip_displacement":-0.0535,"reaction":10000.0}},[gis.task_id])
    cx=AnalysisTask("CalculiX","finite_element_analysis",
        {"metrics":{"tip_displacement":-0.0536,"reaction":10000.0}},[gis.task_id])
    return MultiPhysicsWorkflow("BB15 Verification","BB15-DEMO",[gis,os,cx])

class Tests(unittest.TestCase):
    def registry(self):
        r=EngineRegistry(); register_default_adapters(r); return r
    def test_registry(self):
        r=self.registry()
        self.assertTrue(r.contains("QGIS") and r.contains("OpenSees") and r.contains("CalculiX"))
    def test_execution_and_fusion(self):
        result=MultiPhysicsOrchestrator(self.registry()).execute(make_workflow())
        self.assertTrue(result["success"])
        self.assertEqual(result["fusion"]["engine_count"],3)
        self.assertIn("reaction",result["fusion"]["metrics"])
    def test_comparison(self):
        self.assertTrue(ResultComparator(0.01).compare("u",-0.0535,-0.0536)["passed"])
    def test_cycle(self):
        a=AnalysisTask("QGIS","prepare_geometry"); b=AnalysisTask("OpenSees","verification")
        a.depends_on=[b.task_id]; b.depends_on=[a.task_id]
        with self.assertRaises(ValueError):
            MultiPhysicsOrchestrator(self.registry()).execute(MultiPhysicsWorkflow("x","x",[a,b]))
    def test_required_failure(self):
        result=MultiPhysicsOrchestrator(self.registry()).execute(
            MultiPhysicsWorkflow("x","x",[AnalysisTask("Missing","run")]))
        self.assertFalse(result["success"])
    def test_evidence_and_bridges(self):
        result=MultiPhysicsOrchestrator(self.registry()).execute(make_workflow())
        with tempfile.TemporaryDirectory() as d:
            checksum=MultiPhysicsOrchestrator.save_evidence(Path(d)/"evidence.json",result)
            self.assertEqual(len(checksum),64)
            self.assertEqual(len(publish_to_digital_twin(ProjectDatabase("BB15",Path(d)/"db"),result)),2)
            self.assertEqual(len(publish_to_knowledge_graph(KnowledgeGraphEngine(),result)),2)
    def test_duplicate_registration(self):
        r=self.registry()
        with self.assertRaises(KeyError): register_default_adapters(r)

if __name__=="__main__": unittest.main()
