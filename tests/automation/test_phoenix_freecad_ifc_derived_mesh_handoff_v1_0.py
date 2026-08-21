from __future__ import annotations

import inspect
import unittest

class FreeCADIfcDerivedMeshHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import phoenix.architecture.nonresidential_real_project_orchestration_v1_0 as mod
        cls.src = inspect.getsource(mod._freecad_handoff)

    def test_legacy_generic_ifc_import_removed(self):
        self.assertNotIn("Import.insert", self.src)
        self.assertNotIn("import Import", self.src)

    def test_existing_ifc_mesh_adapter_reused(self):
        self.assertIn("from phoenix.engines.ifc_visual_mesh_adapter_v1_0 import ifc_to_obj", self.src)
        self.assertIn("ifc_to_obj(", self.src)

    def test_freecad_mesh_module_used(self):
        self.assertIn('"import Mesh\\n"', self.src)
        self.assertIn("Mesh.Mesh(", self.src)
        self.assertIn("Mesh::Feature", self.src)

    def test_authoritative_ifc_role_preserved(self):
        self.assertIn("authoritative source remains IFC", self.src)
        self.assertIn("IFC_DERIVED_PRESENTATION_MESH", self.src)

    def test_output_gate_strict(self):
        self.assertIn("output.stat().st_size < 1000", self.src)
        self.assertIn("FREECAD_NONRESIDENTIAL_HANDOFF=PASS", self.src)

    def test_strict_freecad_runtime_bound(self):
        self.assertIn(r"C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe", self.src)

if __name__ == "__main__":
    unittest.main(verbosity=2)
