import importlib.util, json, pathlib, tempfile, unittest
from unittest import mock
ENGINE = pathlib.Path(__file__).resolve().parents[2] / "tools" / "start_screen" / "PROJECT_PHOENIX_official_start_v3_autosync.py"
spec = importlib.util.spec_from_file_location("m", ENGINE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class T(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory();r=pathlib.Path(td.name)
        (r/".git").mkdir();(r/"configs"/"phoenix"/"structural").mkdir(parents=True)
        (r/"configs"/"projects").mkdir(parents=True);(r/"runners").mkdir()
        (r/"phoenix"/"local_app"/"static"/"official_start_v3_0").mkdir(parents=True)
        return td,r
    def rs(self):
        return {"branch":"project-phoenix","clean":True,"head":"abc","head_subject":"x","local_remote_synchronized":True}
    def test_01_plain_semver(self): self.assertEqual(m._version_tuple("8.12.0"),(8,12,0))
    def test_02_filename_semver(self): self.assertEqual(m._version_tuple("x_v8_12_0"),(8,12,0))
    def test_03_category(self): self.assertEqual(m._category("structural foundation"),"STRUCTURAL")
    def test_04_discovery(self):
        td,r=self.make_repo()
        try:
            p=r/"configs"/"phoenix"/"structural"/"e.json";p.write_text(json.dumps({"engine_id":"X","name":"Structural Test","version":"8.12.0"}))
            self.assertTrue(any(x["engine_id"]=="X" for x in m.discover_engines(r)))
        finally: td.cleanup()
    def test_05_major8_only(self):
        e=[{"category":"STRUCTURAL","version_tuple":[8,12,0],"name":"A","engine_id":"A"},{"category":"STRUCTURAL","version_tuple":[9,0,0],"name":"B","engine_id":"B"}]
        self.assertEqual([x["version"] for x in m.structural_chain(e)],["v8.12.0"])
    def test_06_chain_sort(self):
        e=[{"category":"STRUCTURAL","version_tuple":[8,12,0],"name":"B","engine_id":"B"},{"category":"STRUCTURAL","version_tuple":[8,1,0],"name":"A","engine_id":"A"}]
        self.assertEqual([x["version"] for x in m.structural_chain(e)],["v8.1.0","v8.12.0"])
    def test_07_registry_line(self):
        td,r=self.make_repo()
        try:
            with mock.patch.object(m,"repo_status",return_value=self.rs()):
                self.assertEqual(m.build_registry(r)["phoenix"]["major_line"],"Phoenix 3.0")
        finally: td.cleanup()
    def test_08_pat_pending(self):
        td,r=self.make_repo()
        try:
            with mock.patch.object(m,"repo_status",return_value=self.rs()):
                self.assertIn("PENDING",m.build_registry(r)["product_status"]["production_acceptance_test"])
        finally: td.cleanup()
    def test_09_release_locked(self):
        td,r=self.make_repo()
        try:
            with mock.patch.object(m,"repo_status",return_value=self.rs()):
                self.assertIn("LOCKED",m.build_registry(r)["product_status"]["production_release"])
        finally: td.cleanup()
    def test_10_manual_false(self):
        td,r=self.make_repo()
        try:
            with mock.patch.object(m,"repo_status",return_value=self.rs()):
                self.assertFalse(m.build_registry(r)["automation"]["manual_dashboard_registration_required"])
        finally: td.cleanup()
    def test_11_write_registry(self):
        td,r=self.make_repo()
        try:
            with mock.patch.object(m,"repo_status",return_value=self.rs()):
                self.assertTrue(m.write_registry(r).is_file())
        finally: td.cleanup()
    def test_12_policy_override(self):
        td,r=self.make_repo()
        try:
            (r/"configs"/"phoenix"/"official_start_screen_v3_policy.json").write_text(json.dumps({"production_acceptance_test_status":"PASSED","production_release":"READY"}))
            with mock.patch.object(m,"repo_status",return_value=self.rs()):
                self.assertEqual(m.build_registry(r)["product_status"]["production_acceptance_test"],"PASSED")
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
