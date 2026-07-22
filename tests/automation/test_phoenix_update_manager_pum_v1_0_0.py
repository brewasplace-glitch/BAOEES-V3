import json, tempfile, unittest
from pathlib import Path
from phoenix.update_manager import PhoenixUpdateManager, UpdateError, UpdateManifest
class PUMTests(unittest.TestCase):
    def test_plan(self):
        m=PhoenixUpdateManager(); p=m.create_plan(UpdateManifest("PHX","1",("a.txt",), tests=("t",)))
        self.assertEqual(len(p.evidence_sha256),64)
    def test_unsafe(self):
        with self.assertRaises(UpdateError): UpdateManifest("PHX","1",("../bad",)).validate()
    def test_overlap(self):
        with self.assertRaises(UpdateError): UpdateManifest("PHX","1",("a",),("a",)).validate()
    def test_state_push_pending(self):
        m=PhoenixUpdateManager(); p=m.create_plan(UpdateManifest("PHX","1",("a",)))
        with tempfile.TemporaryDirectory() as d:
            f=m.write_state(Path(d)/"s.json",plan=p,phase="committed",commit_sha="abc",push_pending=True)
            x=json.loads(f.read_text()); self.assertTrue(x["push_pending"]); self.assertEqual(len(x["state_sha256"]),64)
    def test_bad_phase(self):
        m=PhoenixUpdateManager(); p=m.create_plan(UpdateManifest("PHX","1",("a",)))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(UpdateError): m.write_state(Path(d)/"s.json",plan=p,phase="bad")
if __name__ == "__main__": unittest.main()
