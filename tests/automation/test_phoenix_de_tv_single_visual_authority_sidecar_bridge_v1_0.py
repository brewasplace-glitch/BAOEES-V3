from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "phoenix/local_app/static/official_start_v3_0/index.html"
MOUNT = ROOT / "phoenix/local_app/static/official_start_v3_0/phoenix_detv_player_mount.js"
PLAYER = ROOT / "phoenix/media_player/web/player.js"

DISABLED = (
    "PROJECT_PHOENIX_pat002_blender_tv_activation_v1_0.js",
    "PROJECT_PHOENIX_de_tv_visual_only_presentation_v1_0.js",
    "PROJECT_PHOENIX_de_tv_authoritative_visual_media_router_v1_0.js",
    "PROJECT_PHOENIX_de_tv_direct_authoritative_png_render_bridge_responsive_control_bar_v1_0.js",
    "PROJECT_PHOENIX_de_tv_seek_exact_visual_ready_bridge_loading_failsafe_v1_0.js",
    "PROJECT_PHOENIX_de_tv_open_source_media_player_v1_0.js",
)

class TestSingleVisualAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.mount = MOUNT.read_text(encoding="utf-8")
        cls.player = PLAYER.read_text(encoding="utf-8")

    def test_canonical_mount_is_active(self):
        self.assertRegex(
            self.index,
            r'<script\b[^>]*src=["\']\./phoenix_detv_player_mount\.js["\'][^>]*>\s*</script>'
        )

    def test_conflicting_legacy_controllers_are_not_active_script_tags(self):
        for name in DISABLED:
            active = re.search(
                rf'<script\b[^>]*src=["\'][^"\']*{re.escape(name)}[^"\']*["\'][^>]*>\s*</script>',
                self.index,
                flags=re.I | re.S,
            )
            self.assertIsNone(active, name)
            self.assertIn(f"PHOENIX_SINGLE_VISUAL_AUTHORITY_DISABLED: {name}", self.index)

    def test_parent_bridge_removes_all_three_known_loading_overlays(self):
        self.assertIn("PHOENIX DE TV SINGLE VISUAL AUTHORITY PARENT BRIDGE v1.0", self.mount)
        for token in (
            "phoenixTvVisualOnlyOverlay",
            "phoenixTvVisualReadyOverlay",
            "phoenixTvAuthoritativeOverlay",
        ):
            self.assertIn(token, self.mount)

    def test_outer_controls_bridge_to_sidecar(self):
        for token in (
            'id==="phoenixTvPrev"',
            'id==="phoenixTvNext"',
            'id==="phoenixTvPlay"',
            'id==="phoenixTvCommandGo"',
            'type:"phoenix-detv-command"',
        ):
            self.assertIn(token, self.mount)

    def test_sidecar_accepts_parent_commands(self):
        self.assertIn("PHOENIX DE TV SIDECAR PARENT COMMAND BRIDGE v1.0", self.player)
        self.assertIn('d.type!=="phoenix-detv-command"', self.player)
        self.assertIn('action==="prev"', self.player)
        self.assertIn('action==="next"', self.player)
        self.assertIn('action==="play"', self.player)
        self.assertIn('action==="command"', self.player)

    def test_real_pat002_pngs_exist(self):
        base = ROOT / "projects/runtime/PHOENIX-PAT-002/results/generated_visual_media/blender_presentation"
        for name in (
            "phoenix_exterior_front.png",
            "phoenix_exterior_rear.png",
            "phoenix_bird_view.png",
            "phoenix_interior_cutaway.png",
        ):
            p = base / name
            self.assertTrue(p.is_file(), p)
            self.assertGreater(p.stat().st_size, 1000, p)

if __name__ == "__main__":
    unittest.main(verbosity=2)