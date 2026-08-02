import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
HTML = ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"index.html"
JS = ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_visual_v3_0_2.js"

class StartScreen302StaticTests(unittest.TestCase):
    def test_primary_controls(self):
        html=HTML.read_text(encoding="utf-8")
        for id_ in ["resultsBtn","startBtn","speechBtn","projectSelect","brief","desiredOutputGroups"]:
            self.assertIn(f'id="{id_}"',html)

    def test_navigation_controls(self):
        html=HTML.read_text(encoding="utf-8")
        for label in ["Nieuw Project","Projecten","Digital Twin","AI Agents","Simulaties","Documenten","Rapporten","Asset Management","Dashboard","Instellingen"]:
            self.assertIn(label,html)

    def test_results_and_progress_visible(self):
        html=HTML.read_text(encoding="utf-8")
        self.assertIn('progressFill',html)
        self.assertIn('RESULTATEN',html)

    def test_js_uses_stable_polling_endpoints(self):
        js=JS.read_text(encoding="utf-8")
        for marker in ["/api/summary","/api/progress","/api/status","/api/results","/api/desired-outputs","/api/modules/"]:
            self.assertIn(marker,js)

    def test_js_binds_output_toolbar(self):
        js=JS.read_text(encoding="utf-8")
        for marker in ["allOnBtn","allOffBtn","recommendedBtn","myStandardBtn"]:
            self.assertIn(marker,js)

    def test_js_binds_results(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn('openResults',js)

    def test_visual_reference_elements_present(self):
        html=HTML.read_text(encoding="utf-8")
        for marker in ["SELECTEER PROJECTTYPE","INVOER / UPLOAD PROJECTOMSCHRIJVING","GEWENSTE OUTPUT","Autonomous Engineering & Infrastructure Intelligence Platform"]:
            self.assertIn(marker,html)

if __name__=="__main__":
    unittest.main()
