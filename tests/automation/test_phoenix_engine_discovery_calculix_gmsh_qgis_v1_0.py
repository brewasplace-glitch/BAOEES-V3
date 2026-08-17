import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from phoenix.engines.engine_discovery_v1_0 import discover_engine,discover_core
from phoenix.engines.adapters.calculix_adapter_v1_0 import capability_state as ccx_state
from phoenix.engines.adapters.gmsh_adapter_v1_0 import capability_state as gmsh_state
from phoenix.engines.adapters.qgis_adapter_v1_0 import capability_state as qgis_state
from phoenix.engines.open_source_engine_registry import evaluate_registry

class TestPhoenixEngineDiscoveryFoundationV10(unittest.TestCase):
 def test_calculix_environment_discovery(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);tool=r/"ccx.exe";tool.write_text("fake")
   with patch.dict(os.environ,{"CCX_HOME":str(r)},clear=False):
    d=discover_engine("calculix",r)
   self.assertTrue(d["available"])
   self.assertEqual(Path(d["executable"]).name.lower(),"ccx.exe")
   self.assertEqual(d["discovery_source"],"ENV:CCX_HOME")

 def test_repository_discovery(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);p=r/"tools/calculix/bin";p.mkdir(parents=True);(p/"ccx.exe").write_text("fake")
   with patch.dict(os.environ,{"PATH":"","CCX_HOME":"","CALCULIX_HOME":""},clear=False):
    d=discover_engine("calculix",r)
   self.assertTrue(d["available"])
   self.assertEqual(d["discovery_source"],"REPOSITORY_SCAN")

 def test_optional_adapters_fail_closed_or_report_capability(self):
  repo=Path(__file__).resolve().parents[2]
  for fn in (ccx_state,gmsh_state,qgis_state):
   s=fn(repo)
   self.assertIn("available",s)
   self.assertIn("adapter_version",s)
   self.assertIsInstance(s["capabilities"],list)

 def test_central_registry_uses_deep_discovery(self):
  repo=Path(__file__).resolve().parents[2]
  state=evaluate_registry(repo/"configs/phoenix/open_source_engine_registry_v1_0.json")
  ids={s["id"]:s for s in state["states"]}
  for eid in ("calculix","gmsh","qgis"):
   self.assertIn(eid,ids)
   self.assertIn("discovery_source",ids[eid])
   self.assertIn("discovery_evidence",ids[eid])

 def test_version_probe_isolated_from_repository(self):
  import phoenix.engines.engine_discovery_v1_0 as dmod
  with tempfile.TemporaryDirectory() as td:
   repo=Path(td)
   fake=repo/"ccx.exe"
   fake.write_text("fake")
   before={p.name for p in repo.iterdir()}
   with patch("subprocess.run") as run:
    run.return_value.stdout=""
    run.return_value.stderr=""
    run.return_value.returncode=0
    dmod._run_version(fake)
    self.assertTrue(run.called)
    for call in run.call_args_list:
     self.assertIn("cwd",call.kwargs)
     self.assertNotEqual(Path(call.kwargs["cwd"]).resolve(),repo.resolve())
   after={p.name for p in repo.iterdir()}
   self.assertEqual(before,after)

 def test_discovery_state_has_three_foundation_engines(self):
  repo=Path(__file__).resolve().parents[2]
  s=discover_core(repo)
  self.assertEqual(set(s["engines"]),{"calculix","gmsh","qgis"})
  self.assertIn("calculix_ready",s)
  self.assertIn("gmsh_ready",s)
  self.assertIn("qgis_ready",s)

if __name__=="__main__":unittest.main()
