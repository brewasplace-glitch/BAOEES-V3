import json, tempfile, unittest
from hashlib import sha256
from pathlib import Path
from phoenix.adapters.automatic_drawing_generation import (
    AutomaticDrawingGenerationConfig,
    AutomaticDrawingGenerationError,
    create_automatic_drawing_generation_adapter,
)

def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

class Wave14Tests(unittest.TestCase):
    def make_bim(self, directory, node_ids=("N1","N2")):
        artifact = {
            "schema":"phoenix-bim-ifc-synchronization-v1.0",
            "project_id":"PHX-W14-001",
            "nodes":[
                {"phoenix_id":"N1","coordinates_m":[0,0,0]},
                {"phoenix_id":"N2","coordinates_m":[5,0,3]},
            ],
            "elements":[
                {"phoenix_id":"E1","ifc_entity":"IfcMember","node_ids":list(node_ids)},
            ],
            "synchronization_summary":{"synchronization_status":"ready_for_ifc_serialization"},
        }
        artifact["artifact_sha256"] = sha256(canonical(artifact).encode("utf-8")).hexdigest()
        path = Path(directory)/"bim.json"
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return path

    def config(self, directory, path):
        return AutomaticDrawingGenerationConfig(
            "PHX-W14-001", path, Path(directory)/"out", "PHX14", "P01"
        )

    def run_engine(self, directory):
        return create_automatic_drawing_generation_adapter(
            self.config(directory, self.make_bim(directory))
        )(project_id="PHX-W14-001",
          engine_id="automatic_drawing_generation",
          plan_fingerprint="wave14-fp")

    def test_generates_five_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_engine(directory)
            self.assertEqual(len(result.outputs), 5)
            self.assertTrue(all(Path(p).is_file() for p in result.outputs))

    def test_svg_contains_titleblock_and_element(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_engine(directory)
            svg = Path(result.outputs[0]).read_text(encoding="utf-8")
            self.assertIn("STRUCTURAL PLAN", svg)
            self.assertIn("REVISION: P01", svg)
            self.assertIn(">E1<", svg)

    def test_dxf_is_ascii_r12(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_engine(directory)
            dxf = Path(result.outputs[2]).read_text(encoding="utf-8")
            self.assertIn("AC1009", dxf)
            self.assertIn("PHX_STRUCTURE", dxf)
            self.assertTrue(dxf.endswith("0\nEOF\n"))

    def test_register_has_hashes_and_limitations(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_engine(directory)
            register = json.loads(Path(result.outputs[3]).read_text(encoding="utf-8"))
            self.assertEqual(register["summary"]["drawing_count"], 3)
            self.assertTrue(register["claims_policy"]["dwg_not_generated"])
            self.assertTrue(register["claims_policy"]["pdf_not_generated"])
            self.assertEqual(len(register["artifact_sha256"]), 64)

    def test_tampered_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_bim(directory)
            artifact = json.loads(path.read_text())
            artifact["nodes"][1]["coordinates_m"][0] = 9
            path.write_text(json.dumps(artifact))
            with self.assertRaises(AutomaticDrawingGenerationError):
                create_automatic_drawing_generation_adapter(
                    self.config(directory, path)
                )(project_id="PHX-W14-001",
                  engine_id="automatic_drawing_generation",
                  plan_fingerprint="wave14-fp")

    def test_three_node_element_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_bim(directory, ("N1","N2","N1"))
            with self.assertRaises(AutomaticDrawingGenerationError):
                create_automatic_drawing_generation_adapter(
                    self.config(directory, path)
                )(project_id="PHX-W14-001",
                  engine_id="automatic_drawing_generation",
                  plan_fingerprint="wave14-fp")

    def test_wrong_engine_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_bim(directory)
            with self.assertRaises(AutomaticDrawingGenerationError):
                create_automatic_drawing_generation_adapter(
                    self.config(directory, path)
                )(project_id="PHX-W14-001",
                  engine_id="wrong",
                  plan_fingerprint="wave14-fp")

if __name__ == "__main__":
    unittest.main()
