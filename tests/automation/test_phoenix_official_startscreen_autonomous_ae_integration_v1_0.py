from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from phoenix.local_app.architectural_orchestration_runtime import ArchitecturalOrchestrationRuntime, RELEASE_STATUS
from phoenix.local_app.capability_registry import StartCapabilityRegistry
ROOT = Path(__file__).resolve().parents[2]

class TestPhoenixOfficialStartscreenAutonomousAeIntegration(unittest.TestCase):
    def test_dynamic_capability_registry_auto_discovers_new_files(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td); root=repo/"configs/phoenix/startscreen_capabilities"; root.mkdir(parents=True)
            (repo/"engine.py").write_text("# ok\n",encoding="utf-8")
            for i in (1,2):
                (root/f"cap_{i}.json").write_text(json.dumps({"id":f"cap_{i}","label":f"Capability {i}","required_files":["engine.py"],"action":{"kind":"project_api_post","path":f"/api/cap/{i}"}}),encoding="utf-8")
            values=StartCapabilityRegistry(repo).describe()
            self.assertEqual([x["id"] for x in values],["cap_1","cap_2"])
            self.assertTrue(all(x["available"] for x in values))

    def test_architectural_catalog_filters_non_project_json(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            root=repo/"configs/projects"
            root.mkdir(parents=True)
            (root/"project_index.json").write_text('{"projects":[]}',encoding="utf-8")
            (root/"metadata_only.json").write_text('{"title":"metadata"}',encoding="utf-8")
            (root/"valid_top.json").write_text(
                json.dumps({"project_id":"TOP-001","project_name":"Top project"}),
                encoding="utf-8",
            )
            (root/"valid_nested.json").write_text(
                json.dumps({"project":{"id":"NEST-001","name":"Nested project"}}),
                encoding="utf-8",
            )
            catalog=ArchitecturalOrchestrationRuntime(repo).project_catalog()
            self.assertEqual(
                [item["project_id"] for item in catalog],
                ["NEST-001","TOP-001"],
            )
            self.assertTrue(all(item["file"].startswith("configs/projects/") for item in catalog))

    def test_architectural_project_path_is_repo_contained(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td); runtime=ArchitecturalOrchestrationRuntime(repo)
            outside=repo.parent/"outside_project.json"; outside.write_text('{"project_id":"OUT"}',encoding="utf-8")
            try:
                with self.assertRaises(ValueError): runtime._resolve_project(str(outside))
            finally: outside.unlink(missing_ok=True)

    def test_ui_project_selection_must_use_configs_projects(self):
        source=(ROOT/"phoenix/local_app/architectural_orchestration_runtime.py").read_text(encoding="utf-8")
        self.assertIn('self.repository / "configs" / "projects"',source)
        self.assertIn("projects_root not in path.parents",source)

    def test_release_and_process_governance(self):
        self.assertEqual(RELEASE_STATUS,"CONCEPT_ONLY_NOT_FOR_CONSTRUCTION")
        source=(ROOT/"phoenix/local_app/architectural_orchestration_runtime.py").read_text(encoding="utf-8")
        self.assertIn('"production_locked": True',source); self.assertIn('"for_construction_locked": True',source); self.assertIn("shell=False",source)

    def test_server_has_integrated_status_and_api_routes(self):
        source=(ROOT/"phoenix/local_app/server.py").read_text(encoding="utf-8")
        self.assertIn('"start_capabilities": self.start_capabilities.describe()',source)
        self.assertIn('"architectural_orchestration": self.architectural_orchestration.describe()',source)
        self.assertIn('"/api/architectural-orchestration/status"',source)
        self.assertIn('"/api/architectural-orchestration/start"',source)

    def test_official_start_bootstrap_is_injected_once(self):
        source=(ROOT/"phoenix/local_app/static/official_start_v3_0/index.html").read_text(encoding="utf-8")
        self.assertEqual(source.count("PHOENIX_START_CAPABILITY_BOOTSTRAP"),1)
        self.assertEqual(source.count("PROJECT_PHOENIX_start_capability_registry_v1_0.js"),1)
        self.assertIn("__PHOENIX_SESSION_TOKEN__",source)

    def test_client_keeps_nonrecursive_visual_architecture(self):
        source=(ROOT/"phoenix/local_app/static/official_start_v3_0/PROJECT_PHOENIX_start_capability_registry_v1_0.js").read_text(encoding="utf-8")
        self.assertNotIn("MutationObserver",source); self.assertNotIn("https://",source)
        self.assertIn('api("/api/status")',source); self.assertIn('"X-Phoenix-Token":TOKEN',source)
        self.assertIn("status.start_capabilities",source); self.assertIn("AUTONOME PHOENIX-FLOW",source)
        self.assertIn("status.architectural_orchestration?.projects",source)
        self.assertNotIn('projectOptions(root.querySelector(".phx-cap-project"),status.projects',source)

if __name__=="__main__": unittest.main(verbosity=2)
