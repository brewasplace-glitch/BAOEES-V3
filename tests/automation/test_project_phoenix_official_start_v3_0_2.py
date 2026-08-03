import base64
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from phoenix.local_app.server import PhoenixLocalApplication


class DummyJob:
    def __init__(self, status="RUNNING"):
        self.job_id = "job123"
        self.label = "Demo workflow"
        self.workflow_id = "wf"
        self.status = status
        self.output_dir = "outputs/runtime/demo"
        self.log_path = "outputs/runtime/demo/log.txt"
    def to_dict(self):
        return {
            "job_id": self.job_id,
            "label": self.label,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "output_dir": self.output_dir,
            "log_path": self.log_path,
        }


class DummyWorkflows:
    def __init__(self, status="RUNNING"):
        self._job = DummyJob(status)
    def latest(self): return self._job
    def describe(self): return [{"id":"wf","label":"Test workflow","available":True}]
    def get(self, job_id): return self._job
    def start(self, workflow_id): return self._job


class StartScreen302Tests(unittest.TestCase):
    def make_repo(self, job_status="RUNNING"):
        td = tempfile.TemporaryDirectory()
        repo = pathlib.Path(td.name)
        (repo/"configs"/"projects").mkdir(parents=True)
        (repo/"configs"/"phoenix"/"structural").mkdir(parents=True)
        (repo/"configs"/"phoenix"/"cost_ratebooks").mkdir(parents=True)
        (repo/"phoenix"/"local_app"/"static"/"official_start_v3_0").mkdir(parents=True)
        (repo/"digital_twin").mkdir()
        (repo/"infrastructure").mkdir()
        (repo/"permit").mkdir()
        (repo/"reports").mkdir()
        (repo/"releases").mkdir()
        (repo/"knowledge").mkdir()
        (repo/"docs").mkdir()
        (repo/"outputs"/"runtime"/"demo").mkdir(parents=True)
        (repo/"outputs"/"runtime"/"demo"/"result.json").write_text("{}")
        (repo/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"index.html").write_text(
            "__PHOENIX_SESSION_TOKEN__ __PHOENIX_RUNTIME_VERSION__ __PHOENIX_START_SCREEN_VERSION__ __PHOENIX_DESIRED_OUTPUTS__",
            encoding="utf-8"
        )
        config={"application_name":"Test","dashboard":{},"open_targets":[],"workflows":[],"runtime_root":"outputs/runtime/test"}
        app=PhoenixLocalApplication(repo,config)
        app.workflows=DummyWorkflows(job_status)
        return td,repo,app

    def test_01_versions(self):
        self.assertEqual(PhoenixLocalApplication.VERSION,"1.8.4")
        self.assertEqual(PhoenixLocalApplication.START_SCREEN_VERSION,"3.0.2")

    def test_02_render_injects_desired_output_catalog(self):
        td,repo,app=self.make_repo()
        try:
            out=app.render_start_v3()
            self.assertIn(app.token,out)
            self.assertIn("DOCUMENTEN",out)
            self.assertNotIn("__PHOENIX_DESIRED_OUTPUTS__",out)
        finally: td.cleanup()

    def test_03_progress_snapshot_running(self):
        td,repo,app=self.make_repo("RUNNING")
        try:
            value=app.progress_snapshot()
            self.assertTrue(value["active"])
            self.assertEqual(value["percent"],55)
        finally: td.cleanup()

    def test_04_progress_snapshot_passed(self):
        td,repo,app=self.make_repo("PASSED")
        try:
            value=app.progress_snapshot()
            self.assertEqual(value["percent"],100)
            self.assertEqual(value["status"],"PASSED")
        finally: td.cleanup()

    def test_05_results_snapshot_has_items(self):
        td,repo,app=self.make_repo()
        try:
            value=app.results_snapshot()
            self.assertGreaterEqual(value["count"],1)
            self.assertTrue(value["items"])
        finally: td.cleanup()

    def test_06_module_catalog_has_results_and_projects(self):
        td,repo,app=self.make_repo()
        try:
            ids={x["id"] for x in app.module_catalog()}
            self.assertIn("results",ids)
            self.assertIn("projects",ids)
        finally: td.cleanup()

    def test_07_module_view_screen(self):
        td,repo,app=self.make_repo()
        try:
            value=app.module_view("results")
            self.assertEqual(value["route_kind"],"screen")
        finally: td.cleanup()

    def test_08_module_open_screen(self):
        td,repo,app=self.make_repo()
        try:
            value=app.open_module("results")
            self.assertEqual(value["mode"],"screen")
        finally: td.cleanup()

    def test_09_module_open_modal_info(self):
        td,repo,app=self.make_repo()
        try:
            value=app.open_module("ai_agents")
            self.assertEqual(value["mode"],"modal_info")
        finally: td.cleanup()

    def test_10_module_open_real_path(self):
        td,repo,app=self.make_repo()
        try:
            with mock.patch.object(app,"_open_path") as op:
                value=app.open_module("projects")
                self.assertEqual(value["mode"],"opened_path")
                op.assert_called_once()
        finally: td.cleanup()

    def test_11_summary_contains_progress(self):
        td,repo,app=self.make_repo()
        try:
            with mock.patch.object(app,"_git_status",return_value={"branch":"project-phoenix","clean":True,"status_lines":[]}):
                value=app.summary()
                self.assertIn("progress",value)
        finally: td.cleanup()

    def test_12_create_analysis_persists_desired_outputs(self):
        td,repo,app=self.make_repo()
        try:
            value=app.create_analysis_session({"project_type":"BOUW","desired_outputs":["reports","planning"]})
            self.assertEqual(value["desired_outputs"],["reports","planning"])
        finally: td.cleanup()

    def test_13_save_uploads(self):
        td,repo,app=self.make_repo()
        try:
            data=base64.b64encode(b"hello").decode()
            value=app.save_uploads([{"name":"hello.txt","base64":data}])
            self.assertEqual(value["file_count"],1)
        finally: td.cleanup()

    def test_14_default_outputs_exist(self):
        td,repo,app=self.make_repo()
        try:
            self.assertTrue(app.default_desired_outputs())
        finally: td.cleanup()

    def test_15_status_has_official_start_flags(self):
        td,repo,app=self.make_repo()
        try:
            with mock.patch.object(app,"_git_status",return_value={"branch":"project-phoenix","clean":True,"status_lines":[]}):
                s=app.status()
                self.assertTrue(s["official_start"]["results_panel"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
