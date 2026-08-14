from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.local_app.server import PhoenixLocalApplication


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")


ROOT = project_root()
HTML_PATH = ROOT / "phoenix" / "local_app" / "static" / "official_start_v3_0" / "index.html"
SERVER_PATH = ROOT / "phoenix" / "local_app" / "server.py"
POLICY_PATH = ROOT / "configs" / "phoenix" / "official_start_de_tv_policy_v1_0.json"


class OfficialStartDeTvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.server_source = SERVER_PATH.read_text(encoding="utf-8")
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8-sig"))

    def bare_app(self, repo: Path) -> PhoenixLocalApplication:
        app = PhoenixLocalApplication.__new__(PhoenixLocalApplication)
        app.repository = repo.resolve()
        return app

    def test_01_start_screen_version(self) -> None:
        self.assertIn("PROJECT PHOENIX 3.0.2", self.html)
        self.assertIn('START_SCREEN_VERSION = "3.0.2"', self.server_source)

    def test_02_de_tv_replaces_old_identity_panel(self) -> None:
        self.assertIn('id="phoenixTvPanel"', self.html)
        self.assertIn(">DE TV<", self.html)
        self.assertNotIn("Visuele Phoenix-identiteit hersteld — stabiele UI zonder flikkeren", self.html)

    def test_03_de_tv_has_fullscreen_control(self) -> None:
        self.assertIn('id="phoenixTvFullscreen"', self.html)
        self.assertIn("requestFullscreen", self.html)

    def test_04_de_tv_has_text_command(self) -> None:
        self.assertIn('id="phoenixTvCommand"', self.html)
        self.assertIn("executeCommand", self.html)

    def test_05_de_tv_has_speech_command(self) -> None:
        self.assertIn('id="phoenixTvMic"', self.html)
        self.assertIn("SpeechRecognition", self.html)
        self.assertIn("nl-NL", self.html)

    def test_06_presentation_selection_drives_playlist(self) -> None:
        self.assertIn("presentationIds", self.html)
        self.assertIn("startPresentation", self.html)
        self.assertIn("PRESENTATIE", self.html)

    def test_07_all_checked_outputs_can_be_requested(self) -> None:
        self.assertIn("selectedOutputIds", self.html)
        self.assertIn("showAllSelected", self.html)
        self.assertIn("NIET AANGEVINKT", self.html)

    def test_08_certified_and_powershell_toolbar_moves_left(self) -> None:
        self.assertIn("left:238px;right:auto", self.html)
        self.assertIn("phoenix-certified-materials", self.html)
        self.assertIn("phoenix-return-powershell", self.html)

    def test_09_pdf_desired_output_exists(self) -> None:
        app = self.bare_app(ROOT)
        groups = {g["group"]: g["items"] for g in app.desired_output_catalog()}
        ids = [item["id"] for item in groups["TEKENINGEN / MODELLEN"]]
        self.assertIn("drawing_pdf", ids)
        pdf = next(item for item in groups["TEKENINGEN / MODELLEN"] if item["id"] == "drawing_pdf")
        self.assertEqual("PDF", pdf["label"])

    def test_10_drawing_pdf_is_format_preference_not_capability(self) -> None:
        self.assertIn("drawing_pdf_requested", self.server_source)
        self.assertIn('"desired_output_ui_selection"', self.server_source)
        self.assertIn('"output_format_preferences"', self.server_source)
        self.assertIn('item != "drawing_pdf"', self.server_source)

    def test_11_tv_registry_is_existing_artifacts_only(self) -> None:
        self.assertEqual("EXISTING_ARTIFACTS_ONLY_NO_FABRICATION", self.policy["artifact_policy"])
        self.assertIn("EXISTING_ARTIFACTS_ONLY_NO_FABRICATION", self.server_source)

    def test_12_tv_registry_maps_drawing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            drawing = repo / "outputs" / "projects" / "demo" / "02_drawings" / "plattegrond.pdf"
            drawing.parent.mkdir(parents=True)
            drawing.write_bytes(b"%PDF-1.4\n")
            app = self.bare_app(repo)
            ids = app._tv_output_ids(drawing)
            self.assertIn("floor_plans", ids)
            self.assertIn("drawing_pdf", ids)

    def test_13_tv_registry_maps_presentation_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            viewer = repo / "outputs" / "projects" / "demo" / "digital_twin_3d_viewer.html"
            viewer.parent.mkdir(parents=True)
            viewer.write_text("<html></html>", encoding="utf-8")
            app = self.bare_app(repo)
            self.assertIn("viewer_3d", app._tv_output_ids(viewer))
            self.assertEqual("html", app._tv_preview_kind(viewer))

    def test_14_tv_registry_scans_controlled_output_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            pdf = repo / "outputs" / "projects" / "demo" / "situatie.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF-1.4\n")
            app = self.bare_app(repo)
            registry = app.tv_output_registry()
            self.assertEqual("DE TV", registry["tv_name"])
            self.assertEqual(1, registry["artifact_count"])
            self.assertTrue(registry["items"][0]["file_url"].startswith("/api/tv/file/"))

    def test_15_tv_file_access_is_output_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            allowed = repo / "outputs" / "projects" / "demo" / "x.pdf"
            allowed.parent.mkdir(parents=True)
            allowed.write_bytes(b"x")
            blocked = repo / "docs" / "secret.txt"
            blocked.parent.mkdir(parents=True)
            blocked.write_text("x", encoding="utf-8")
            app = self.bare_app(repo)
            self.assertEqual(allowed.resolve(), app.resolve_tv_file("outputs/projects/demo/x.pdf"))
            with self.assertRaises(FileNotFoundError):
                app.resolve_tv_file("docs/secret.txt")

    def test_16_server_routes_present(self) -> None:
        self.assertIn('parsed.path == "/api/tv/catalog"', self.server_source)
        self.assertIn('parsed.path.startswith("/api/tv/file/")', self.server_source)
        self.assertIn('parsed.path == "/api/tv/open"', self.server_source)

    def test_17_release_and_certification_safety_preserved(self) -> None:
        self.assertFalse(self.policy["changes_professional_approval"])
        self.assertFalse(self.policy["changes_code_compliance_claim"])
        self.assertEqual("LOCKED", self.policy["production_release"])
        self.assertEqual("LOCKED", self.policy["for_construction_release"])

    def test_18_no_live_solver_execution_added(self) -> None:
        self.assertFalse(self.policy["live_solver_execution_during_install"])
        self.assertNotIn("OpenSeesExecutable", self.html)
        self.assertNotIn("ccx.exe", self.html)

    def test_19_tv_relative_paths_use_os_realpath(self) -> None:
        self.assertIn("def _tv_repo_relative", self.server_source)
        self.assertIn("os.path.realpath(self.repository)", self.server_source)
        self.assertIn("os.path.realpath(path)", self.server_source)

    def test_20_tv_registry_avoids_lexical_relative_to_for_artifacts(self) -> None:
        start = self.server_source.index("def _tv_repo_relative")
        end = self.server_source.index("def render_dashboard", start)
        tv_source = self.server_source[start:end]
        self.assertNotIn("path.relative_to(self.repository)", tv_source)


    def test_21_runtime_compatibility_identity_is_preserved(self) -> None:
        self.assertIn('VERSION = "1.8.7"', self.server_source)
        self.assertIn('START_SCREEN_VERSION = "3.0.2"', self.server_source)
        self.assertEqual("1.8.7", self.policy["runtime_compatibility"]["phoenix_local_app_version"])
        self.assertEqual("3.0.2", self.policy["runtime_compatibility"]["official_start_version"])
        self.assertFalse(self.policy["runtime_compatibility"]["legacy_version_gates_modified"])

if __name__ == "__main__":
    unittest.main()
