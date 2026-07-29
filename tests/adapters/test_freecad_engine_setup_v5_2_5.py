from pathlib import Path
import json
import tempfile
import unittest

from phoenix.adapters.open_source.freecad_acceptance import (
    PLACEHOLDER,
    build_runtime_macro,
)

ROOT = Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_configuration(self):
        cfg = json.loads(
            (
                ROOT / "configs/phoenix/freecad_engine_setup_v5_2_1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(cfg["winget_package_id"], "FreeCAD.FreeCAD")
        self.assertFalse(cfg["acceptance"]["simulated_results_allowed"])

    def test_macro_contains_output_placeholder(self):
        text = (
            ROOT / "tools/freecad/phoenix_freecad_acceptance_macro.py"
        ).read_text(encoding="utf-8")
        self.assertIn(PLACEHOLDER, text)
        self.assertIn("doc.saveAs", text)
        self.assertIn("box.Shape.exportStep", text)

    def test_runtime_macro_embeds_absolute_output(self):
        template = (
            ROOT / "tools/freecad/phoenix_freecad_acceptance_macro.py"
        )
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "acceptance"
            output.mkdir()
            runtime = build_runtime_macro(template, output)
            text = runtime.read_text(encoding="utf-8")
            self.assertNotIn(PLACEHOLDER, text)
            self.assertIn(str(output.resolve()).replace("\\", "\\\\"), text)

if __name__ == "__main__":
    unittest.main()
