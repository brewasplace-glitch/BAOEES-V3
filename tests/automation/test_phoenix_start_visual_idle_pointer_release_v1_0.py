import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = ROOT / "phoenix/local_app/static/official_start_v3_0/index.html"
GUARD = ROOT / "phoenix/local_app/static/official_start_v3_0/phoenix_pointer_release_guard.js"
START_DIR = INDEX.parent

class StartVisualIdlePointerReleaseTests(unittest.TestCase):
    def test_pointer_release_guard_is_loaded_once(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertEqual(text.count("phoenix_pointer_release_guard.js"), 1)

    def test_pointer_guard_releases_unexpected_lock(self):
        text = GUARD.read_text(encoding="utf-8")
        self.assertIn("document.pointerLockElement", text)
        self.assertIn("document.exitPointerLock", text)
        self.assertIn('data-phoenix-allow-pointer-lock="true"', text)
        self.assertIn("pointerlockchange", text)

    def test_guard_has_no_continuous_pointer_loop(self):
        text = GUARD.read_text(encoding="utf-8")
        self.assertNotIn("mousemove", text)
        self.assertNotIn("pointermove", text)
        self.assertNotIn("setInterval", text)
        self.assertNotIn("MutationObserver", text)

    def test_periodic_status_poll_is_visual_idle(self):
        hits = []
        for p in START_DIR.glob("*.js"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            if "STATUS_POLL_MS" in text:
                hits.append((p.name, text))
        self.assertEqual(len(hits), 1, hits)
        name, text = hits[0]
        m = re.search(r"STATUS_POLL_MS\s*=\s*(\d+)", text)
        self.assertIsNotNone(m, name)
        self.assertGreaterEqual(int(m.group(1)), 600000)

    def test_existing_output_layout_stability_remains(self):
        css = START_DIR / "phoenix_output_layout_stability.css"
        js = START_DIR / "phoenix_output_layout_stability.js"
        self.assertTrue(css.exists())
        self.assertTrue(js.exists())
        self.assertIn("phoenix-output-mode-row", css.read_text(encoding="utf-8"))
        self.assertIn("AUTONOME PHOENIX-FLOW", js.read_text(encoding="utf-8"))

    def test_legacy_integration_contracts_remain(self):
        combined = INDEX.read_text(encoding="utf-8") + "\n"
        combined += "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in START_DIR.glob("*.js")
        )
        self.assertIn("X-Phoenix-Token", combined)
        self.assertIn("architectural_orchestration", combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)
