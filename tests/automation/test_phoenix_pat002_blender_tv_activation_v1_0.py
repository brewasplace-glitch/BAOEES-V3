import unittest
from pathlib import Path

class TestPhoenixPat002BlenderTvActivationV10(unittest.TestCase):
    def test_tv_contract(self):
        repo=Path(__file__).resolve().parents[2]
        js=(repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_pat002_blender_tv_activation_v1_0.js").read_text(encoding="utf-8")
        for required in (
            'pid!=="PHOENIX-PAT-002"',
            "phoenix_exterior_front.png",
            "phoenix_exterior_rear.png",
            "phoenix_bird_view.png",
            "phoenix_interior_cutaway.png",
            "seekExactArtifact",
            "toon\\s+",
            "interieur",
            "exterieur",
            "variant\\s*b",
        ):
            self.assertIn(required,js)

    def test_blender_script_and_launcher_fail_closed(self):
        repo=Path(__file__).resolve().parents[2]
        launcher=(repo/"phoenix/engines/pat002_blender_presentation_v1_0.py").read_text(encoding="utf-8")
        script=(repo/"phoenix/engines/adapters/blender_pat002_presentation_script_v1_0.py").read_text(encoding="utf-8")
        self.assertIn('"--python-exit-code"',launcher)
        self.assertIn('"23"',launcher)
        self.assertIn("if scene.world is None:",script)
        self.assertIn('bpy.data.worlds.new("Phoenix World")',script)
        self.assertIn('PHOENIX_CYCLES_LOST_BEFORE_OBJ_IMPORT',script)
        self.assertIn('scene.render.engine = "CYCLES"',script)
        self.assertNotIn("read_factory_settings",script)
        self.assertIn('scene.cycles.device = "CPU"',script)
        self.assertIn("scene.cycles.samples = 8",script)
        self.assertNotIn('addon_enable(module="cycles")',script)
        self.assertNotIn('bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items',script)

    def test_cycles_bootstrap_helper_is_present(self):
        repo=Path(__file__).resolve().parents[2]
        launcher=(repo/"phoenix/engines/pat002_blender_presentation_v1_0.py").read_text(encoding="utf-8")
        self.assertIn("def verify_cycles_cpu_bootstrap",launcher)
        self.assertIn('"CYCLES"',launcher)
        self.assertIn('"PHOENIX_CYCLES_CPU_BOOTSTRAP_OK"',launcher)
        self.assertIn('"bootstrap_method": "BLENDER_CLI_-E_CYCLES"',launcher)
        self.assertNotIn("addon_enable(module='cycles')",launcher)

    def test_render_script_does_not_reset_factory_after_cli_bootstrap(self):
        repo=Path(__file__).resolve().parents[2]
        script=(repo/"phoenix/engines/adapters/blender_pat002_presentation_script_v1_0.py").read_text(encoding="utf-8")
        self.assertNotIn("bpy.ops.wm.read_factory_settings",script)
        self.assertIn("PHOENIX_CYCLES_LOST_BEFORE_OBJ_IMPORT",script)

    def test_full_render_uses_cycles_cli_engine_bootstrap(self):
        repo=Path(__file__).resolve().parents[2]
        launcher=(repo/"phoenix/engines/pat002_blender_presentation_v1_0.py").read_text(encoding="utf-8")
        self.assertIn('"-E"',launcher)
        self.assertIn('"CYCLES"',launcher)
        self.assertIn('"--python"',launcher)

    def test_png_validator_uses_real_png_magic_bytes(self):
        repo=Path(__file__).resolve().parents[2]
        launcher=(repo/"phoenix/engines/pat002_blender_presentation_v1_0.py").read_text(encoding="utf-8")
        self.assertIn('bytes.fromhex("89504E470D0A1A0A")',launcher)
        self.assertNotIn('b"\\\\x89PNG',launcher)

    def test_tv_regex_contract_uses_single_javascript_backslash(self):
        repo=Path(__file__).resolve().parents[2]
        js=(repo/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_pat002_blender_tv_activation_v1_0.js").read_text(encoding="utf-8")
        self.assertIn(r"toon\s+",js)
        self.assertIn(r"variant\s*b",js)
        self.assertNotIn(r"toon\\s+",js)
        self.assertNotIn(r"variant\\s*b",js)

    def test_start_screen_loads_tv_activation_after_existing_contracts(self):
        repo=Path(__file__).resolve().parents[2]
        html=(repo/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
        visual="PROJECT_PHOENIX_pat002_blender_tv_activation_v1_0.js"
        strict="PROJECT_PHOENIX_strict_requested_output_presentation_contract_v1_0.js"
        self.assertIn(visual,html)
        self.assertIn(strict,html)
        self.assertGreater(html.index(visual),html.index(strict))

if __name__=="__main__":
    unittest.main()
