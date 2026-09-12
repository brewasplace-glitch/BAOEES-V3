import unittest
from phoenix.structural_qa_bim.engine import classify_holds, write_ifctester_json_report

class TestStructuralQABIM(unittest.TestCase):
    def test_hold_classification(self):
        holds=[
            {"id":f"H{i:02d}","hold":"x","required_for_release":"MANDATORY"}
            for i in range(1,9)
        ]
        r=classify_holds(holds)
        self.assertEqual(len(r),8)
        self.assertEqual(r[1]["closure_class"],"EXTERNAL_SITE_EVIDENCE")
        self.assertEqual(r[-1]["closure_class"],"PROFESSIONAL_APPROVAL_REQUIRED")
        self.assertTrue(all(x["status"]=="OPEN" for x in r))

    def test_ifctester_json_writer_uses_reporter_encoder(self):
        import json
        import tempfile
        from pathlib import Path

        class FakeEntity:
            pass

        class FakeReporter:
            def __init__(self):
                self.report_called=False
                self.to_file_called=False

            def report(self):
                self.report_called=True
                # Simulate the real IfcTester in-memory result containing
                # a non-JSON-serializable IFC entity instance.
                return {"status": True, "element": FakeEntity()}

            def to_file(self, filepath):
                self.to_file_called=True
                Path(filepath).write_text(
                    json.dumps({"status": True, "specifications": []}),
                    encoding="utf-8"
                )

        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"report.json"
            reporter=FakeReporter()
            result=write_ifctester_json_report(reporter,path)
            self.assertTrue(reporter.report_called)
            self.assertTrue(reporter.to_file_called)
            self.assertTrue(result["status"])
            self.assertTrue(path.exists())


if __name__=="__main__":
    unittest.main()
