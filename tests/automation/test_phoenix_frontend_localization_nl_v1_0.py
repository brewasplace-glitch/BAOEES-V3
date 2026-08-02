import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
LOCALIZER=ROOT/'phoenix'/'local_app'/'static'/'official_start_v3_0'/'PROJECT_PHOENIX_frontend_nl_v1_0_0.js'
HTML=ROOT/'phoenix'/'local_app'/'static'/'official_start_v3_0'/'index.html'
SERVER=ROOT/'phoenix'/'local_app'/'server.py'
POLICY=ROOT/'configs'/'phoenix'/'frontend_localization_nl_v1_0.json'

class DutchFrontendTests(unittest.TestCase):
    def test_01_dutch_status_map(self):
        js=LOCALIZER.read_text(encoding='utf-8')
        for marker in ['["RUNNING", "BEZIG"]','["BLOCKED", "GEBLOKKEERD"]','["PASSED", "GESLAAGD"]','["FAILED", "MISLUKT"]']:
            self.assertIn(marker,js)
    def test_02_dutch_terms(self):
        js=LOCALIZER.read_text(encoding='utf-8')
        for marker in ['AUTONOME PROJECTMODUS','Digitale Tweeling','Sessieadapter','Resultatenindex','TAAL · NEDERLANDS']:
            self.assertIn(marker,js)
    def test_03_technical_pre_code_excluded(self):
        js=LOCALIZER.read_text(encoding='utf-8')
        self.assertIn('pre,code,kbd,samp',js)
    def test_04_no_frontend_polling(self):
        js=LOCALIZER.read_text(encoding='utf-8')
        self.assertNotIn('setInterval(',js)
        self.assertNotIn('setTimeout(',js)
    def test_05_html_loads_localizer(self):
        html=HTML.read_text(encoding='utf-8')
        self.assertIn('PROJECT_PHOENIX_frontend_nl_v1_0_0.js',html)
    def test_06_backend_contract_codes_still_english(self):
        server=SERVER.read_text(encoding='utf-8')
        for marker in ['"RUNNING"','"BLOCKED"','"PASSED"','"FAILED"','session_id','project_id']:
            self.assertIn(marker,server)
    def test_07_policy_language_split(self):
        p=json.loads(POLICY.read_text(encoding='utf-8'))
        self.assertEqual(p['frontend_locale'],'nl-NL')
        self.assertEqual(p['backend_contract_locale'],'en-US')
        self.assertTrue(p['rules']['technical_json_keys_unchanged'])

if __name__=='__main__': unittest.main()
