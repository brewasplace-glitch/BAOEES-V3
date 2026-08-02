import base64
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVER = ROOT / "phoenix" / "local_app" / "server.py"

# Load using package import so relative imports work.
import sys
sys.path.insert(0, str(ROOT))
from phoenix.local_app.server import PhoenixLocalApplication


class DummyWorkflows:
    def latest(self): return None
    def describe(self):
        return [{"id":"wf","label":"Test workflow","available":True}]
    def get(self, job_id): return None


class StartScreenFunctionalTests(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory()
        repo=pathlib.Path(td.name)
        (repo/"configs"/"projects").mkdir(parents=True)
        (repo/"phoenix"/"local_app"/"static"/"official_start_v3_0").mkdir(parents=True)
        (repo/"projects").mkdir()
        (repo/"digital_twin").mkdir()
        (repo/"architecture").mkdir()
        (repo/"structural").mkdir()
        (repo/"infrastructure").mkdir()
        (repo/"permit").mkdir()
        (repo/"configs"/"phoenix"/"cost_ratebooks").mkdir(parents=True)
        (repo/"reports").mkdir()
        (repo/"releases").mkdir()
        (repo/"bib").mkdir()
        (repo/"outputs"/"runtime").mkdir(parents=True)
        html='<html><body>__PHOENIX_SESSION_TOKEN__ __PHOENIX_RUNTIME_VERSION__ __PHOENIX_START_SCREEN_VERSION__</body></html>'
        (repo/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"index.html").write_text(html)
        config={"application_name":"Test","dashboard":{},"open_targets":[],"workflows":[],"runtime_root":"outputs/runtime/test"}
        app=PhoenixLocalApplication(repo,config)
        app.workflows=DummyWorkflows()
        return td,repo,app

    def test_01_version(self):
        self.assertEqual(PhoenixLocalApplication.VERSION,"1.5.0")

    def test_02_start_version(self):
        self.assertEqual(PhoenixLocalApplication.START_SCREEN_VERSION,"3.0.1")

    def test_03_render_injects_token(self):
        td,repo,app=self.make_repo()
        try:
            out=app.render_start_v3()
            self.assertIn(app.token,out)
            self.assertNotIn("__PHOENIX_SESSION_TOKEN__",out)
        finally: td.cleanup()

    def test_04_module_catalog_has_core_tiles(self):
        td,repo,app=self.make_repo()
        try:
            ids={x["id"] for x in app.module_catalog()}
            self.assertTrue({"projects","digital_twin","architectural","structural","permits","knowledge"}.issubset(ids))
        finally: td.cleanup()

    def test_05_module_availability(self):
        td,repo,app=self.make_repo()
        try:
            mods={x["id"]:x for x in app.module_catalog()}
            self.assertTrue(mods["projects"]["available"])
            self.assertTrue(mods["digital_twin"]["available"])
        finally: td.cleanup()

    def test_06_open_module_calls_open_path(self):
        td,repo,app=self.make_repo()
        try:
            with mock.patch.object(app,"_open_path") as op:
                r=app.open_module("projects")
                self.assertEqual(r["module_id"],"projects")
                op.assert_called_once()
        finally: td.cleanup()

    def test_07_upload_persists(self):
        td,repo,app=self.make_repo()
        try:
            data=base64.b64encode(b"hello").decode()
            r=app.save_uploads([{"name":"hello.txt","base64":data}])
            self.assertEqual(r["file_count"],1)
            saved=repo/r["files"][0]["relative_path"]
            self.assertEqual(saved.read_bytes(),b"hello")
        finally: td.cleanup()

    def test_08_upload_sanitizes_name(self):
        td,repo,app=self.make_repo()
        try:
            data=base64.b64encode(b"x").decode()
            r=app.save_uploads([{"name":"../../evil.txt","base64":data}])
            self.assertEqual(r["files"][0]["name"],"evil.txt")
        finally: td.cleanup()

    def test_09_analysis_session_persists(self):
        td,repo,app=self.make_repo()
        try:
            r=app.create_analysis_session({"project_type":"BOUW","brief":"test"})
            self.assertEqual(r["status"],"READY_FOR_WORKFLOW_SELECTION")
            self.assertTrue((repo/r["session_file"]).is_file())
        finally: td.cleanup()

    def test_10_invalid_project_type_rejected(self):
        td,repo,app=self.make_repo()
        try:
            with self.assertRaises(ValueError):
                app.create_analysis_session({"project_type":"OTHER"})
        finally: td.cleanup()

    def test_11_asset_traversal_rejected(self):
        td,repo,app=self.make_repo()
        try:
            with self.assertRaises(FileNotFoundError):
                app.resolve_start_asset("../../secret.txt")
        finally: td.cleanup()

    def test_12_status_exposes_modules(self):
        td,repo,app=self.make_repo()
        try:
            with mock.patch.object(app,"_git_status",return_value={"branch":"project-phoenix","clean":True,"status_lines":[]}):
                s=app.status()
                self.assertIn("modules",s)
                self.assertTrue(s["official_start"]["functional_controls"])
        finally: td.cleanup()

    def test_13_start_asset_resolves(self):
        td,repo,app=self.make_repo()
        try:
            p=repo/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"x.js"
            p.write_text("x")
            self.assertEqual(app.resolve_start_asset("x.js"),p.resolve())
        finally: td.cleanup()

    def test_14_project_registry(self):
        td,repo,app=self.make_repo()
        try:
            (repo/"configs"/"projects"/"p.json").write_text(json.dumps({"project_id":"P1","project_name":"Project One"}))
            self.assertEqual(app._projects()[0]["project_id"],"P1")
        finally: td.cleanup()

    def test_15_upload_rejects_bad_base64(self):
        td,repo,app=self.make_repo()
        try:
            with self.assertRaises(ValueError):
                app.save_uploads([{"name":"x.txt","base64":"%%%"}])
        finally: td.cleanup()


if __name__=="__main__":
    unittest.main()
