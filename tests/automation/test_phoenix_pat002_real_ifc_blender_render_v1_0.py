import json
import tempfile
import unittest
from pathlib import Path

from phoenix.architecture.real_multivariant_design_engine_v1_0 import run_multivariant_design
from phoenix.engines.pat002_blender_presentation_v1_0 import verify_cycles_cpu_bootstrap
from phoenix.engines.visual_engine_discovery_v1_0 import discover_executable

class TestPhoenixPat002RealIfcBlenderRenderV10(unittest.TestCase):
    def test_blender_cycles_cpu_bootstrap(self):
        repo=Path(__file__).resolve().parents[2]
        blender=discover_executable("blender",repo)
        self.assertTrue(blender["available"])
        smoke=verify_cycles_cpu_bootstrap(Path(blender["executable"]),timeout=180)
        self.assertTrue(smoke["passed"],smoke)

    def _workspace(self, root: Path) -> Path:
        w = root / "projects" / "runtime" / "PHOENIX-PAT-002"
        a = w / "results" / "session_adapters" / "architecture"
        a.mkdir(parents=True)
        (a / "architectural_model.json").write_text(json.dumps({
            "project_id": "PHOENIX-PAT-002",
            "description": "Vrijstaande woning van twee bouwlagen in Paramaribo, Suriname"
        }), encoding="utf-8")
        (a / "architectural_session_intake.json").write_text(json.dumps({
            "project_id": "PHOENIX-PAT-002",
            "prompt": "Ontwerp een vrijstaande woning van twee bouwlagen en genereer presentatie-output."
        }), encoding="utf-8")
        (a / "project_context.json").write_text(json.dumps({
            "project_id": "PHOENIX-PAT-002",
            "parcel_width": 28,
            "parcel_depth": 42,
            "location": "Paramaribo, Suriname"
        }), encoding="utf-8")
        (a / "site_context.json").write_text(json.dumps({
            "location": "Paramaribo, Suriname",
            "source": "project-specific site drawing"
        }), encoding="utf-8")

        for p in (
            w / "results" / "session_adapters" / "digital_twin" / "central_project_digital_twin.json",
            w / "digital_twin" / "central_project_digital_twin.json",
        ):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"project_id": "PHOENIX-PAT-002"}), encoding="utf-8")
        return w

    def test_pat002_generates_real_blender_png_set_from_authoritative_ifc(self):
        with tempfile.TemporaryDirectory() as td:
            repository = Path(td)
            workspace = self._workspace(repository)
            result = run_multivariant_design(repository, workspace)
            self.assertEqual(result["status"], "PASSED")

            arch = workspace / "results" / "session_adapters" / "architecture"
            model = json.loads((arch / "architectural_model.json").read_text(encoding="utf-8"))
            self.assertEqual(model["authoritative_geometry_source"], "IFC_AUTHORITATIVE")
            self.assertEqual(model["authoritative_geometry_format"], "IFC")
            self.assertEqual(model["blender_presentation"]["status"], "PASSED")
            self.assertEqual(model["blender_presentation"]["source_geometry"], "IFC_AUTHORITATIVE")

            out = workspace / "results" / "generated_visual_media" / "blender_presentation"
            expected = (
                "phoenix_exterior_front.png",
                "phoenix_exterior_rear.png",
                "phoenix_bird_view.png",
                "phoenix_interior_cutaway.png",
            )
            for name in expected:
                p = out / name
                self.assertTrue(p.exists(), name)
                self.assertGreaterEqual(p.stat().st_size, 1500, name)
                self.assertEqual(p.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

            manifest = json.loads((out / "blender_presentation_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PASSED")
            self.assertEqual(manifest["authoritative_geometry"], "IFC")
            self.assertEqual(manifest["renderer"], "Blender")
            self.assertEqual(manifest["project_id"], "PHOENIX-PAT-002")
            self.assertEqual(manifest["production_release"], "LOCKED")
            self.assertIn("png_quality",manifest)
            for name,check in manifest["png_quality"].items():
                self.assertTrue(check["valid"], (name,check))
                self.assertGreaterEqual(check["width"],1280)
                self.assertGreaterEqual(check["height"],720)
            self.assertTrue((out / "phoenix_blender_scene_evidence.txt").exists())

    def test_non_pat002_project_does_not_trigger_blender_render(self):
        with tempfile.TemporaryDirectory() as td:
            repository = Path(td)
            w = repository / "projects" / "runtime" / "PHOENIX-PAT-TEST"
            a = w / "results" / "session_adapters" / "architecture"
            a.mkdir(parents=True)
            (a / "architectural_model.json").write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST"}))
            (a / "architectural_session_intake.json").write_text(json.dumps({
                "project_id":"PHOENIX-PAT-TEST",
                "prompt":"Ontwerp een vrijstaande woning van twee bouwlagen"
            }))
            (a / "project_context.json").write_text(json.dumps({
                "project_id":"PHOENIX-PAT-TEST","parcel_width":28,"parcel_depth":42
            }))
            (a / "site_context.json").write_text("{}")
            for p in (
                w / "results" / "session_adapters" / "digital_twin" / "central_project_digital_twin.json",
                w / "digital_twin" / "central_project_digital_twin.json",
            ):
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps({"project_id":"PHOENIX-PAT-TEST"}))
            result=run_multivariant_design(repository,w)
            self.assertEqual(result["status"],"PASSED")
            self.assertFalse((w/"results/generated_visual_media/blender_presentation").exists())

if __name__ == "__main__":
    unittest.main()
