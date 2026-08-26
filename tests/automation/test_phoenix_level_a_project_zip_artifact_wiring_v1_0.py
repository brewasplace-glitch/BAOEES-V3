import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "phoenix" / "autonomy" / "session_adapters.py"


class LevelAProjectZipWiringTests(unittest.TestCase):
    def test_closure_wires_project_zip_after_qaqc_gate_write(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        start = text.index("def run_closure(")
        end = text.index("\n\nRUNNERS:", start)
        block = text[start:end]

        gate_write = "write_json(gate_path,gate)"
        zip_call = "emit_level_a_project_zip_artifact("
        finish_call = "return finish("

        self.assertIn(gate_write, block)
        self.assertIn(zip_call, block)
        self.assertIn("project_zip_path", block)
        self.assertIn("project_zip_manifest_path", block)
        self.assertIn("repo_ref(project_zip_path", block)
        self.assertIn("repo_ref(project_zip_manifest_path", block)
        self.assertLess(block.index(gate_write), block.index(zip_call))
        self.assertLess(block.index(zip_call), block.index(finish_call))

    def test_module_import_is_present(self):
        text = ADAPTER.read_text(encoding="utf-8-sig")
        self.assertIn(
            "from .level_a_project_zip_artifact_bridge_v1_0 import emit_level_a_project_zip_artifact",
            text,
        )


if __name__ == "__main__":
    unittest.main()
