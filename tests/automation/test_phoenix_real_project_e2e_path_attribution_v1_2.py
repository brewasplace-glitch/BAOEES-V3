
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "phoenix/validation/real_project_e2e_environment_discovery.py"

spec = importlib.util.spec_from_file_location("e2e_discovery", DISCOVERY)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class StrictToolPathAttributionTests(unittest.TestCase):
    def test_freecad_basename_filter_rejects_foreign_tools(self):
        self.assertTrue(module.is_tool_binary("freecad", pathlib.Path("FreeCADCmd.exe")))
        self.assertTrue(module.is_tool_binary("freecad", pathlib.Path("FreeCAD.exe")))
        self.assertFalse(module.is_tool_binary("freecad", pathlib.Path("ccx.exe")))
        self.assertFalse(module.is_tool_binary("freecad", pathlib.Path("python.exe")))

    def test_blender_basename_filter_rejects_foreign_tools(self):
        self.assertTrue(module.is_tool_binary("blender", pathlib.Path("blender.exe")))
        self.assertFalse(module.is_tool_binary("blender", pathlib.Path("python.exe")))
        self.assertFalse(module.is_tool_binary("blender", pathlib.Path("git.exe")))
        self.assertFalse(module.is_tool_binary("blender", pathlib.Path("FreeCAD.exe")))

    def test_calculix_basename_filter_rejects_foreign_tools(self):
        self.assertTrue(module.is_tool_binary("calculix", pathlib.Path("ccx.exe")))
        self.assertTrue(module.is_tool_binary("calculix", pathlib.Path("ccx_2.22.exe")))
        self.assertFalse(module.is_tool_binary("calculix", pathlib.Path("python.exe")))
        self.assertFalse(module.is_tool_binary("calculix", pathlib.Path("Esa.exe")))

    def test_detector_marks_strict_attribution(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn('"strict_basename_attribution": True', source)

    def test_browser_discovery_remains_no_fetch(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn('["npx"', source)
        self.assertIn('"network_fetch_attempted": False', source)

    def test_project_selection_remains_required(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn('"selection_required": True', source)

    def test_release_remains_locked(self):
        source = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn('"production": "LOCKED"', source)
        self.assertIn('"for_construction": "LOCKED"', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
