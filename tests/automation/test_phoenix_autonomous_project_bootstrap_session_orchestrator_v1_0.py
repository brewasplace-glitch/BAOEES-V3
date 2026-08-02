import json
import pathlib
import tempfile
import unittest
from unittest import mock
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from phoenix.autonomy.session_orchestrator import AutonomousProjectOrchestrator
from phoenix.local_app.server import PhoenixLocalApplication


class DummyWorkflows:
    def __init__(self):
        self.calls = []
        self._latest = None
    def describe(self):
        return [
            {"id":"visible","label":"Visible","available":True,"ui_hidden":False},
            {"id":"autonomous_session_orchestrator_v1_0","label":"Auto","available":True,"ui_hidden":True},
        ]
    def latest(self): return self._latest
    def get(self, job_id): return self._latest
    def start(self, workflow_id, **kwargs):
        from phoenix.local_app.models import RuntimeJob
        self.calls.append((workflow_id, kwargs))
        job = RuntimeJob(
            job_id="auto123",
            workflow_id=workflow_id,
            label="Auto",
            status="QUEUED",
            started_at="2026-08-02T00:00:00+00:00",
            output_dir="outputs/runtime/auto123",
            log_path="outputs/runtime/auto123/workflow.log",
            command=["python","runner.py"],
        )
        self._latest = job
        return job


def make_config():
    return {
        "application_name":"Test",
        "dashboard":{},
        "open_targets":[],
        "workflows":[],
        "runtime_root":"outputs/runtime/test",
    }


class AutonomousBootstrapTests(unittest.TestCase):
    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        repo = pathlib.Path(td.name)
        (repo/"configs"/"phoenix").mkdir(parents=True)
        source = ROOT/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json"
        (repo/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (repo/"outputs"/"runtime"/"phoenix_start_v3_sessions").mkdir(parents=True)
        (repo/"phoenix"/"local_app"/"static"/"official_start_v3_0").mkdir(parents=True)
        (repo/"phoenix"/"local_app"/"static"/"official_start_v3_0"/"index.html").write_text(
            "__PHOENIX_SESSION_TOKEN__ __PHOENIX_RUNTIME_VERSION__ __PHOENIX_START_SCREEN_VERSION__ __PHOENIX_DESIRED_OUTPUTS__",
            encoding="utf-8"
        )
        return td, repo

    def test_01_explicit_project_id_from_brief(self):
        td, repo = self.make_repo()
        try:
            orch = AutonomousProjectOrchestrator(repo)
            session={"project_type":"BOUW","brief":"PHOENIX-PAT-001\nOntwerp woning"}
            self.assertEqual(orch.derive_project_id(session),"PHOENIX-PAT-001")
        finally: td.cleanup()

    def test_02_bootstrap_creates_workspace(self):
        td, repo = self.make_repo()
        try:
            orch = AutonomousProjectOrchestrator(repo)
            sf=repo/"outputs"/"runtime"/"phoenix_start_v3_sessions"/"PHX-X.json"
            session={
                "session_id":"PHX-X","project_type":"BOUW","project_mode":"autonomous",
                "brief":"PHOENIX-PAT-001","desired_outputs":["reports","structural_analysis"],
                "upload_batch":None,"selected_project":None
            }
            sf.write_text(json.dumps(session),encoding="utf-8")
            result=orch.bootstrap_session(session,sf)
            self.assertTrue((repo/result.project_manifest).is_file())
            self.assertTrue((repo/result.digital_twin_state).is_file())
            self.assertTrue((repo/result.orchestration_plan).is_file())
        finally: td.cleanup()

    def test_03_plan_maps_outputs_to_capabilities(self):
        td, repo = self.make_repo()
        try:
            orch=AutonomousProjectOrchestrator(repo)
            plan=orch.build_plan(
                {"session_id":"S","project_type":"BOUW","desired_outputs":["floor_plans","structural_analysis","cost_estimate"]},
                "P"
            )
            ids={x["capability_id"] for x in plan["steps"]}
            self.assertIn("architecture",ids)
            self.assertIn("structural_engineering",ids)
            self.assertIn("cost_planning",ids)
        finally: td.cleanup()

    def test_04_pilot_runner_is_never_available(self):
        td, repo = self.make_repo()
        try:
            cfg=json.loads((repo/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json").read_text())
            cfg["capabilities"]["architecture"]["runner_candidates"]=["runners/PROJECT_PHOENIX_BB35_pilot_1_arch.py"]
            cfg["capabilities"]["architecture"]["session_adapter_ready"]=True
            (repo/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json").write_text(json.dumps(cfg))
            (repo/"runners").mkdir()
            (repo/"runners"/"PROJECT_PHOENIX_BB35_pilot_1_arch.py").write_text("pass")
            orch=AutonomousProjectOrchestrator(repo)
            value=orch.capability_availability("architecture")
            self.assertNotEqual(value["status"],"AVAILABLE")
        finally: td.cleanup()

    def test_05_run_returns_controlled_blocked(self):
        td, repo = self.make_repo()
        try:
            orch=AutonomousProjectOrchestrator(repo)
            sf=repo/"outputs"/"runtime"/"phoenix_start_v3_sessions"/"PHX-X.json"
            session={
                "session_id":"PHX-X","project_type":"BOUW","project_mode":"autonomous",
                "brief":"PHOENIX-PAT-001","desired_outputs":["floor_plans"],
                "upload_batch":None,"selected_project":None
            }
            sf.write_text(json.dumps(session),encoding="utf-8")
            b=orch.bootstrap_session(session,sf)
            session["bootstrap"]=b.to_dict()
            sf.write_text(json.dumps(session),encoding="utf-8")
            out=repo/"outputs"/"run"
            rc=orch.run_session(sf,out)
            self.assertEqual(rc,10)
            progress=json.loads((out/"progress.json").read_text())
            self.assertEqual(progress["status"],"BLOCKED")
        finally: td.cleanup()

    def test_06_session_context_propagates(self):
        td, repo = self.make_repo()
        try:
            orch=AutonomousProjectOrchestrator(repo)
            sf=repo/"outputs"/"runtime"/"phoenix_start_v3_sessions"/"PHX-X.json"
            session={
                "session_id":"PHX-X","project_type":"BOUW","project_mode":"autonomous",
                "brief":"PHOENIX-PAT-001","desired_outputs":["reports","planning"],
                "upload_batch":"BATCH-1","selected_project":None
            }
            sf.write_text(json.dumps(session),encoding="utf-8")
            b=orch.bootstrap_session(session,sf)
            manifest=json.loads((repo/b.project_manifest).read_text())
            self.assertEqual(manifest["desired_outputs"],["reports","planning"])
            self.assertEqual(manifest["session_id"],"PHX-X")
            self.assertEqual(manifest["upload"]["batch_id"],"BATCH-1")
        finally: td.cleanup()

    def test_07_server_session_persists_project_mode_and_bootstrap(self):
        td, repo = self.make_repo()
        try:
            app=PhoenixLocalApplication(repo,make_config())
            app.workflows=DummyWorkflows()
            app.autonomy=AutonomousProjectOrchestrator(repo)
            value=app.create_analysis_session({
                "project_type":"BOUW","project_mode":"autonomous",
                "brief":"PHOENIX-PAT-001","desired_outputs":["reports"]
            })
            self.assertEqual(value["status"],"READY_FOR_AUTONOMOUS_ORCHESTRATION")
            self.assertEqual(value["project_mode"],"autonomous")
            self.assertEqual(value["bootstrap"]["project_id"],"PHOENIX-PAT-001")
            self.assertTrue(all(not w.get("ui_hidden") for w in value["available_workflows"]))
        finally: td.cleanup()

    def test_08_server_starts_hidden_generic_orchestrator_with_session_file(self):
        td, repo = self.make_repo()
        try:
            app=PhoenixLocalApplication(repo,make_config())
            dummy=DummyWorkflows()
            app.workflows=dummy
            app.autonomy=AutonomousProjectOrchestrator(repo)
            value=app.create_analysis_session({
                "project_type":"BOUW","project_mode":"autonomous",
                "brief":"PHOENIX-PAT-001","desired_outputs":["reports"]
            })
            job=app.start_autonomous_session(value["session_id"])
            self.assertEqual(job["workflow_id"],"autonomous_session_orchestrator_v1_0")
            self.assertEqual(dummy.calls[0][0],"autonomous_session_orchestrator_v1_0")
            extra=dummy.calls[0][1]["extra_args"]
            self.assertEqual(extra[0],"--session-file")
            self.assertIn(value["session_id"],extra[1])
        finally: td.cleanup()

    def test_09_non_autonomous_session_rejected(self):
        td, repo = self.make_repo()
        try:
            app=PhoenixLocalApplication(repo,make_config())
            app.workflows=DummyWorkflows()
            app.autonomy=AutonomousProjectOrchestrator(repo)
            value=app.create_analysis_session({
                "project_type":"BOUW","project_mode":"manual",
                "brief":"PHOENIX-PAT-001","desired_outputs":["reports"]
            })
            with self.assertRaises(ValueError):
                app.start_autonomous_session(value["session_id"])
        finally: td.cleanup()

    def test_10_job_view_merges_real_progress(self):
        td, repo = self.make_repo()
        try:
            from phoenix.local_app.models import RuntimeJob
            app=PhoenixLocalApplication(repo,make_config())
            out=repo/"outputs"/"runtime"/"job"/"result"
            out.mkdir(parents=True)
            (out/"progress.json").write_text(json.dumps({
                "percent":42,"step":"Architecture","project_id":"P","session_id":"S","blocker_count":0
            }))
            job=RuntimeJob(
                job_id="x",workflow_id="a",label="A",status="RUNNING",
                started_at="x",output_dir="outputs/runtime/job",log_path="x",command=[]
            )
            view=app.job_view(job)
            self.assertEqual(view["progress_percent"],42)
            self.assertEqual(view["project_id"],"P")
        finally: td.cleanup()


    def test_11_bootstrap_accepts_external_or_alias_session_path_reference(self):
        td, repo = self.make_repo()
        external = tempfile.TemporaryDirectory()
        try:
            orch = AutonomousProjectOrchestrator(repo)
            sf = pathlib.Path(external.name) / "PHX-ALIAS.json"
            session = {
                "session_id":"PHX-ALIAS",
                "project_type":"BOUW",
                "project_mode":"autonomous",
                "brief":"PHOENIX-PAT-ALIAS",
                "desired_outputs":["reports"],
                "upload_batch":None,
                "selected_project":None,
            }
            sf.write_text(json.dumps(session), encoding="utf-8")
            result = orch.bootstrap_session(session, sf)
            manifest = json.loads((repo/result.project_manifest).read_text(encoding="utf-8"))
            self.assertTrue(manifest["source_session_file"])
            self.assertEqual(manifest["session_id"], "PHX-ALIAS")
        finally:
            external.cleanup()
            td.cleanup()

if __name__=="__main__":
    unittest.main()
