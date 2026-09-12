import unittest
from phoenix.structural_final_package.engine import closure_plan

class TestFinalStructuralPackage(unittest.TestCase):
    def test_open_holds_never_auto_release(self):
        qa={"release_holds":[
            {"id":f"H{i:02d}","hold":"x","closure_class":"X","status":"OPEN"}
            for i in range(1,9)
        ]}
        result=closure_plan(qa)
        self.assertEqual(result["open_release_holds"],8)
        self.assertEqual(result["autonomous_holds_closed"],0)
        self.assertEqual(result["release_decision"],"HOLD")

    def test_professional_hold_owner(self):
        qa={"release_holds":[{"id":"H08","hold":"approval","closure_class":"PROFESSIONAL_APPROVAL_REQUIRED","status":"OPEN"}]}
        result=closure_plan(qa)
        self.assertEqual(result["holds"][0]["responsible_party"],"Qualified structural professional")

if __name__=="__main__":
    unittest.main()
