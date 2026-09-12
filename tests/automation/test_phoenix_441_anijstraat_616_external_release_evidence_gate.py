import unittest
import tempfile
from pathlib import Path
from phoenix.structural_release_evidence.engine import approval_gate, bootstrap_inbox

class TestReleaseEvidenceGate(unittest.TestCase):
    def test_no_evidence_never_releases(self):
        records=[
            {"id":f"H{i:02d}","hold":"x","closure_status":"OPEN","submission_status":"OPEN_NO_EXTERNAL_EVIDENCE"}
            for i in range(1,9)
        ]
        gate=approval_gate(records)
        self.assertEqual(gate["open_release_holds"],8)
        self.assertFalse(gate["release_allowed"])
        self.assertEqual(gate["construction_release"],"LOCKED")

    def test_inbox_bootstrap(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            schema=root/"schema.json"
            schema.write_text('{"type":"object"}',encoding="utf-8")
            inbox=root/"inbox"
            bootstrap_inbox(inbox,schema)
            self.assertTrue((inbox/"H01/submission.template.json").exists())
            self.assertTrue((inbox/"H08/REQUIRED_EVIDENCE.md").exists())

if __name__=="__main__":
    unittest.main()
