from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MOUNT = ROOT / "phoenix/local_app/static/official_start_v3_0/phoenix_detv_player_mount.js"
PLAYER = ROOT / "phoenix/media_player/web/player.js"
R4TEST = ROOT / "tests/automation/test_phoenix_de_tv_single_visual_authority_nonrecursive_bridge_v1_0.py"

class TestPresentationUiConsolidationLiveMetaSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mount = MOUNT.read_text(encoding="utf-8")
        cls.player = PLAYER.read_text(encoding="utf-8")

    def test_working_single_visual_authority_baseline_is_preserved(self):
        self.assertIn(
            "PHOENIX DE TV SINGLE VISUAL AUTHORITY NON-RECURSIVE PARENT BRIDGE v1.0",
            self.mount,
        )
        self.assertTrue(R4TEST.is_file())

    def test_sidecar_is_mounted_in_embedded_mode(self):
        self.assertIn(
            '${SIDECAR}/player/?project=${encodeURIComponent(activeProject())}&embedded=1',
            self.mount,
        )

    def test_embedded_mode_hides_duplicate_sidecar_controls(self):
        self.assertIn("phoenixApplyEmbeddedUiConsolidation", self.player)
        self.assertIn('get("embedded")==="1"', self.player)
        self.assertIn('document.querySelectorAll("button")', self.player)
        self.assertIn('document.getElementById("command")', self.player)
        self.assertIn('document.getElementById("show")', self.player)
        self.assertIn('dataset.phoenixEmbeddedHidden="1"', self.player)

    def test_internal_meta_is_hidden_but_kept_as_state_source(self):
        self.assertIn('meta.dataset.phoenixEmbeddedMetaSource="1"', self.player)
        self.assertIn('meta.style.display="none"', self.player)

    def test_every_successful_image_load_pushes_current_live_label(self):
        self.assertIn("PHOENIX DE TV LIVE META SYNC v1.0", self.player)
        self.assertRegex(
            self.player,
            r'img\.onload=\(\)=>\{[\s\S]*?const liveLabel=`\$\{i\+1\}/\$\{items\.length\} Â· \$\{x\.label\}`;'
        )
        self.assertIn('phoenixParentState("GEREED",liveLabel)', self.player)

    def test_presentation_bridge_is_still_present(self):
        for token in (
            'action==="prev"',
            'action==="next"',
            'action==="play"',
            'action==="command"',
            'type:"phoenix-detv-player-state"',
        ):
            self.assertIn(token, self.player)

    def test_new_ui_block_does_not_add_mutation_observer(self):
        marker="PHOENIX DE TV LIVE META SYNC v1.0"
        block=self.player.split(marker,1)[1]
        self.assertIsNone(
            re.search(r"(?:new\s+)?(?:window\.)?MutationObserver\s*\(", block)
        )
        self.assertNotRegex(block, r"attributes\s*:\s*true")
        self.assertNotIn("attributeFilter", block)

    def test_real_pat002_pngs_remain_nonempty(self):
        base=ROOT/"projects/runtime/PHOENIX-PAT-002/results/generated_visual_media/blender_presentation"
        for name in (
            "phoenix_exterior_front.png",
            "phoenix_exterior_rear.png",
            "phoenix_bird_view.png",
            "phoenix_interior_cutaway.png",
        ):
            path=base/name
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size,1000,path)

if __name__ == "__main__":
    unittest.main(verbosity=2)