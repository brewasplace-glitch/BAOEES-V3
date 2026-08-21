from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "phoenix/engines/adapters/blender_phoenix_render_script_v1_0.py"
ADAPTER = ROOT / "phoenix/engines/adapters/blender_visual_adapter_v1_0.py"

class Blender52CyclesCpuR2Tests(unittest.TestCase):
    def test_cycles_is_primary_engine(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("_phoenix_engine_candidates = ('CYCLES',", src)

    def test_cycles_cpu_is_explicit(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("scene.cycles.device = 'CPU'", src)
        self.assertIn("PHOENIX_RENDER_DEVICE=", src)

    def test_world_is_created_when_missing(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("if scene.world is None:", src)
        self.assertIn("bpy.data.worlds.new('PHOENIX_WORLD')", src)

    def test_runtime_evidence_tokens_exist(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PHOENIX_RENDER_ENGINE=", src)
        self.assertIn("PHOENIX_WORLD_READY=PASS", src)

    def test_legacy_hardcoded_eevee_next_assignment_removed(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("scene.render.engine='BLENDER_EEVEE_NEXT'", src)
        self.assertNotIn('scene.render.engine="BLENDER_EEVEE_NEXT"', src)

    def test_adapter_still_requires_real_png(self):
        src = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("p.returncode==0 and output_png.exists()", src)

    def test_no_release_or_detv_core_logic_in_render_patch(self):
        src = SCRIPT.read_text(encoding="utf-8").lower()
        self.assertNotIn("production_release", src)
        self.assertNotIn("for_construction", src)
        self.assertNotIn("detv", src)

    def test_cycles_sample_cap_present(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("scene.cycles.samples = 16", src)

if __name__ == "__main__":
    unittest.main(verbosity=2)
