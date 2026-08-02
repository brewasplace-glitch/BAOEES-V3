import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
HTML=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"index.html"
JS=ROOT/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"PROJECT_PHOENIX_official_start_v3_functional_v3_0_1.js"

class StaticFunctionalContractTests(unittest.TestCase):
    def test_all_expected_module_buttons_exist(self):
        html=HTML.read_text(encoding="utf-8")
        for module in ["projects","digital_twin","architectural","structural","civil","infra","permits","cost_planning","qaqc","release_control","knowledge"]:
            self.assertIn(f'data-module="{module}"',html)

    def test_primary_controls_exist(self):
        html=HTML.read_text(encoding="utf-8")
        for id_ in ["uploadBtn","speechBtn","startBtn","systemBtn","filePicker","projectSelect","brief"]:
            self.assertIn(f'id="{id_}"',html)

    def test_client_binds_primary_controls(self):
        js=JS.read_text(encoding="utf-8")
        for id_ in ["uploadBtn","speechBtn","startBtn","systemBtn"]:
            self.assertIn(f'$("{id_}").onclick',js)

    def test_client_binds_modules(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn('querySelectorAll("[data-module]")',js)
        self.assertIn('/api/modules/',js)

    def test_real_upload_endpoint_used(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn('post("/api/uploads"',js)

    def test_project_analysis_endpoint_used(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn('post("/api/project-analysis/start"',js)

    def test_workflow_endpoint_used(self):
        js=JS.read_text(encoding="utf-8")
        self.assertIn('/api/workflows/',js)

if __name__=="__main__":
    unittest.main()
