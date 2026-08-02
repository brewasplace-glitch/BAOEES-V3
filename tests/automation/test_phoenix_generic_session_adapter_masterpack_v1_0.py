import json
import pathlib
import tempfile
import unittest
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from phoenix.autonomy.session_adapters import run_adapter
from phoenix.autonomy.session_orchestrator import AutonomousProjectOrchestrator


class SessionAdapterMasterpackTests(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory()
        repo=pathlib.Path(td.name)
        (repo/"configs"/"phoenix").mkdir(parents=True)
        (repo/"projects"/"runtime"/"PHOENIX-PAT-001"/"inputs").mkdir(parents=True)
        (repo/"projects"/"runtime"/"PHOENIX-PAT-001"/"digital_twin").mkdir(parents=True)
        (repo/"projects"/"runtime"/"PHOENIX-PAT-001"/"orchestration").mkdir(parents=True)
        (repo/"projects"/"runtime"/"PHOENIX-PAT-001"/"results").mkdir(parents=True)
        (repo/"projects"/"runtime"/"PHOENIX-PAT-001"/"logs").mkdir(parents=True)
        (repo/"outputs"/"runtime"/"phoenix_start_v3_sessions").mkdir(parents=True)
        (repo/"inputs"/"runtime"/"official_start_v3_uploads").mkdir(parents=True)
        # Copy master config
        src=ROOT/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json"
        (repo/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json").write_text(
            src.read_text(encoding="utf-8"),encoding="utf-8"
        )
        # Copy adapter runners for availability checks
        (repo/"runners").mkdir()
        for path in (ROOT/"runners").glob("PROJECT_PHOENIX_session_adapter_*_v1_0_0.py"):
            (repo/"runners"/path.name).write_text(path.read_text(encoding="utf-8"),encoding="utf-8")

        session={
            "session_id":"PHX-TEST",
            "project_type":"BOUW",
            "project_mode":"autonomous",
            "brief":"PHOENIX-PAT-001\nOntwerp testwoning",
            "selected_project":None,
            "upload_batch":None,
            "desired_outputs":["floor_plans","digital_twin_output","structural_analysis","permit_dossier","cost_estimate","reports","qaqc_output"],
            "bootstrap":{
                "project_id":"PHOENIX-PAT-001",
                "workspace":"projects/runtime/PHOENIX-PAT-001",
                "project_manifest":"projects/runtime/PHOENIX-PAT-001/project_manifest.json",
                "digital_twin_state":"projects/runtime/PHOENIX-PAT-001/digital_twin/project_state.json",
                "orchestration_plan":"projects/runtime/PHOENIX-PAT-001/orchestration/dependency_plan.json",
            }
        }
        sf=repo/"outputs"/"runtime"/"phoenix_start_v3_sessions"/"PHX-TEST.json"
        sf.write_text(json.dumps(session),encoding="utf-8")
        (repo/"projects"/"runtime"/"PHOENIX-PAT-001"/"project_manifest.json").write_text(
            json.dumps({"project_id":"PHOENIX-PAT-001"}),encoding="utf-8"
        )
        return td,repo,session,sf

    def test_01_all_seven_adapters_registered(self):
        cfg=json.loads((ROOT/"configs"/"phoenix"/"autonomous_project_orchestrator_v1_0.json").read_text())
        expected={"architecture","digital_twin","structural_engineering","permit","cost_planning","reporting","closure"}
        for cap in expected:
            self.assertTrue(cfg["capabilities"][cap]["session_adapter_ready"])
            self.assertTrue(cfg["capabilities"][cap]["runner_candidates"])

    def test_02_architecture_autonomous_text_bootstrap_generates_candidate_with_explicit_assumptions(self):
        td,repo,session,sf=self.make_repo()
        try:
            session["brief"]="PHOENIX-PAT-001\\nOntwerp een vrijstaande woning van twee bouwlagen."
            sf.write_text(json.dumps(session),encoding="utf-8")
            ws=repo/session["bootstrap"]["workspace"]
            out=ws/"results"/"session_adapters"/"architecture"
            rc=run_adapter("architecture",repo,sf,ws,out)
            self.assertEqual(rc,0)
            result=json.loads((out/"adapter_result.json").read_text())
            self.assertEqual(result["status"],"PASSED")
            self.assertEqual(result["metadata"]["generation_mode"],"AUTONOMOUS_TEXT_CONCEPT")
            self.assertTrue((out/"architectural_model.json").is_file())
            self.assertTrue((out/"architectural_assumptions_register.json").is_file())
            model=json.loads((out/"architectural_model.json").read_text())
            self.assertEqual(model["production_release"],"LOCKED")
            self.assertFalse(model["professional_approval"])
        finally: td.cleanup()

    def test_02b_architecture_non_autonomous_text_only_still_blocks_without_fabricating_geometry(self):
        td,repo,session,sf=self.make_repo()
        try:
            session["project_mode"]="manual"
            session["brief"]="PHOENIX-PAT-001\\nOntwerp een vrijstaande woning van twee bouwlagen."
            sf.write_text(json.dumps(session),encoding="utf-8")
            ws=repo/session["bootstrap"]["workspace"]
            out=ws/"results"/"session_adapters"/"architecture"
            rc=run_adapter("architecture",repo,sf,ws,out)
            self.assertEqual(rc,10)
            result=json.loads((out/"adapter_result.json").read_text())
            self.assertEqual(result["status"],"BLOCKED_INPUT")
            self.assertEqual(result["blockers"][0]["reason"],"DIMENSIONED_ARCHITECTURAL_MODEL_REQUIRED")
        finally: td.cleanup()

    def test_03_architecture_accepts_structured_json_upload(self):
        td,repo,session,sf=self.make_repo()
        try:
            batch="B1"
            root=repo/"inputs"/"runtime"/"official_start_v3_uploads"/batch
            root.mkdir()
            model={"storeys":[{"storey_id":"L0","spaces":[{"space_id":"R1","x_m":0,"y_m":0,"width_m":5,"depth_m":4}],"walls":[]}]}
            (root/"model.json").write_text(json.dumps(model),encoding="utf-8")
            session["upload_batch"]=batch
            sf.write_text(json.dumps(session),encoding="utf-8")
            ws=repo/session["bootstrap"]["workspace"]
            out=ws/"results"/"session_adapters"/"architecture"
            rc=run_adapter("architecture",repo,sf,ws,out)
            self.assertEqual(rc,0)
            self.assertTrue((out/"architectural_model.json").is_file())
        finally: td.cleanup()

    def test_04_digital_twin_uses_architecture_state(self):
        td,repo,session,sf=self.make_repo()
        try:
            ws=repo/session["bootstrap"]["workspace"]
            model=ws/"results"/"session_adapters"/"architecture"/"architectural_model.json"
            model.parent.mkdir(parents=True,exist_ok=True)
            model.write_text(json.dumps({"storeys":[]}),encoding="utf-8")
            state={"capabilities":{"architecture":{"status":"PASSED","outputs":[model.relative_to(repo).as_posix()]}}}
            (ws/"orchestration"/"adapter_state.json").write_text(json.dumps(state),encoding="utf-8")
            out=ws/"results"/"session_adapters"/"digital_twin"
            rc=run_adapter("digital_twin",repo,sf,ws,out)
            self.assertEqual(rc,0)
            self.assertTrue((out/"central_project_digital_twin.json").is_file())
        finally: td.cleanup()

    def test_05_permit_blocks_without_location(self):
        td,repo,session,sf=self.make_repo()
        try:
            ws=repo/session["bootstrap"]["workspace"]
            out=ws/"results"/"session_adapters"/"permit"
            rc=run_adapter("permit",repo,sf,ws,out)
            self.assertEqual(rc,10)
            result=json.loads((out/"adapter_result.json").read_text())
            self.assertEqual(result["blockers"][0]["reason"],"PROJECT_LOCATION_JURISDICTION_REQUIRED")
        finally: td.cleanup()

    def test_06_reporting_always_generates_status_report(self):
        td,repo,session,sf=self.make_repo()
        try:
            ws=repo/session["bootstrap"]["workspace"]
            out=ws/"results"/"session_adapters"/"reporting"
            rc=run_adapter("reporting",repo,sf,ws,out)
            self.assertEqual(rc,0)
            self.assertTrue((out/"autonomous_status_report.json").is_file())
            self.assertTrue((out/"autonomous_status_report.md").is_file())
        finally: td.cleanup()

    def test_07_closure_enforces_release_lock(self):
        td,repo,session,sf=self.make_repo()
        try:
            ws=repo/session["bootstrap"]["workspace"]
            (ws/"orchestration"/"adapter_state.json").write_text(json.dumps({
                "capabilities":{"architecture":{"status":"BLOCKED"}}
            }),encoding="utf-8")
            out=ws/"results"/"session_adapters"/"closure"
            rc=run_adapter("closure",repo,sf,ws,out)
            self.assertEqual(rc,0)
            gate=json.loads((out/"qaqc_release_gate.json").read_text())
            self.assertEqual(gate["production_release"],"LOCKED")
            self.assertGreater(gate["upstream_blocker_count"],0)
        finally: td.cleanup()

    def test_08_all_adapter_runners_are_generic_not_pilot(self):
        for path in (ROOT/"runners").glob("PROJECT_PHOENIX_session_adapter_*_v1_0_0.py"):
            text=path.read_text(encoding="utf-8").lower()
            self.assertNotIn("bb35_pilot",text)
            self.assertNotIn("moskee_bunschoten",text)

    def test_09_orchestrator_discovers_all_adapters_available(self):
        td,repo,session,sf=self.make_repo()
        try:
            orch=AutonomousProjectOrchestrator(repo)
            for cap in ("architecture","digital_twin","structural_engineering","permit","cost_planning","reporting","closure"):
                value=orch.capability_availability(cap)
                self.assertEqual(value["status"],"AVAILABLE",cap)
        finally: td.cleanup()

    def test_10_structural_adapter_exposes_v8_chain_without_pilot_dependency(self):
        text=(ROOT/"phoenix"/"autonomy"/"session_adapters.py").read_text(encoding="utf-8")
        for version in range(0,13):
            self.assertIn(f"_v8_{version}_0.py",text)
        self.assertIn('"legacy_pilot_dependency": False',text)

if __name__=="__main__":
    unittest.main()
