from __future__ import annotations
import importlib.util, json, sys, unittest
from pathlib import Path

def project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists(): return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

def load_module():
    path = project_root() / "phoenix/graph/phoenix_project_graph_v34_0.py"
    name = "phoenix_project_graph_v34_0_test"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError("Graphmodule kon niet worden geladen.")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    try: spec.loader.exec_module(module)
    finally: sys.modules.pop(name, None)
    return module

class PhoenixProjectGraphTests(unittest.TestCase):
    def test_policy_and_schema(self):
        root = project_root()
        policy = json.loads((root / "configs/phoenix/project_graph_policy_v34_0.json").read_text(encoding="utf-8-sig"))
        schema = json.loads((root / "configs/phoenix/project_graph_schema_v34_0.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(policy["policy_version"], "v34.0"); self.assertIn("depends_on", schema["relation_types"])
    def test_id_registry(self):
        module = load_module(); registry = module.PhoenixIdRegistry()
        self.assertEqual(registry.create_id("project"), "PROJECT-000001"); self.assertEqual(registry.create_id("building"), "BLD-000001")
    def test_nodes_and_relations(self):
        module = load_module(); graph = module.PhoenixProjectGraph(); p = graph.add_node("project", "P"); b = graph.add_node("building", "B")
        graph.add_relation(p.object_id, b.object_id, "contains"); self.assertEqual(graph.find_children(p.object_id)[0]["object_id"], b.object_id)
    def test_update_revision(self):
        module = load_module(); graph = module.PhoenixProjectGraph(); n = graph.add_node("column", "K12", {"size": "200x200"}); u = graph.update_node(n.object_id, {"size": "250x250"})
        self.assertEqual(u.revision, 2); self.assertEqual(u.attributes["size"], "250x250")
    def test_dependency_query(self):
        module = load_module(); graph = module.PhoenixProjectGraph(); c = graph.add_node("column", "K12"); f = graph.add_node("foundation", "F1")
        graph.add_relation(c.object_id, f.object_id, "depends_on"); self.assertEqual(graph.find_dependencies(c.object_id)[0]["object_id"], f.object_id)
    def test_impact_analysis(self):
        module = load_module(); graph = module.PhoenixProjectGraph(); c = graph.add_node("column", "K12"); f = graph.add_node("foundation", "F1"); k = graph.add_node("cost_item", "Kosten")
        graph.add_relation(c.object_id, f.object_id, "depends_on"); graph.add_relation(k.object_id, f.object_id, "depends_on")
        impacted = {x["object_id"] for x in graph.impact_analysis(f.object_id)["impacts"]}; self.assertIn(c.object_id, impacted); self.assertIn(k.object_id, impacted)
    def test_invalid_relation_rejected(self):
        module = load_module(); graph = module.PhoenixProjectGraph(); a = graph.add_node("project", "A"); b = graph.add_node("building", "B")
        with self.assertRaises(ValueError): graph.add_relation(a.object_id, b.object_id, "invalid")
    def test_integration(self):
        module = load_module(); self.assertEqual(module.PhoenixProjectGraph().integration_test()["status"], "PASS")

if __name__ == "__main__": unittest.main()
