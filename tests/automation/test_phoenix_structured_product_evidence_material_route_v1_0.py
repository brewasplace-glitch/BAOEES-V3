import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.material_route_intelligence import decide_material_route
from phoenix.autonomy.landed_cost_gate_guard import enforce_landed_cost_gate
from phoenix.autonomy.structured_product_evidence_acquisition import _technical_eval


class StructuredProductEvidenceMaterialRouteTests(unittest.TestCase):
    def test_structural_concrete_is_local_ready_mix_route(self):
        decision = decide_material_route(
            "REQ-COLUMN-STRUCTURAL-CONCRETE",
            "structural_concrete",
            "LOCAL_AVAILABILITY_CONFIRMED",
            "TECHNICAL_PRODUCT_EVIDENCE_REQUIRED",
        )
        self.assertEqual(decision.primary_route, "LOCAL_READY_MIX_TECHNICAL_QUALIFICATION")
        self.assertFalse(decision.international_fallback_allowed)
        self.assertFalse(decision.automatic_ordering)

    def test_timber_requires_strength_standard_and_document_evidence(self):
        good = _technical_eval(
            "structural_timber",
            ["Structural timber C24 according to EN 338 and EN 14081. Declaration of Performance available. CE marking."],
        )
        self.assertTrue(good["engineering_qualified"])
        bad = _technical_eval("structural_timber", ["C24 structural timber available now"])
        self.assertFalse(bad["engineering_qualified"])

    def test_rebar_requires_grade_standard_and_certificate(self):
        good = _technical_eval(
            "reinforcement_steel",
            ["Reinforcing steel B500B EN 10080. Inspection certificate 3.1 available."],
        )
        self.assertTrue(good["engineering_qualified"])
        bad = _technical_eval("reinforcement_steel", ["B500B reinforcing bar for sale"])
        self.assertFalse(bad["engineering_qualified"])

    def test_masonry_requires_standard_strength_and_document(self):
        good = _technical_eval(
            "masonry_unit",
            ["EN 771-3 masonry block. Compressive strength 12.5 MPa. Declaration of Performance."],
        )
        self.assertTrue(good["engineering_qualified"])
        bad = _technical_eval("masonry_unit", ["Concrete masonry block 12.5 MPa"])
        self.assertFalse(bad["engineering_qualified"])

    def test_empty_import_false_pass_is_blocked_when_import_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            arch = ws / "results" / "session_adapters" / "architecture"
            acq = ws / "sources" / "import_acquisition"
            arch.mkdir(parents=True)
            acq.mkdir(parents=True)
            (arch / "global_material_sourcing_register.json").write_text(
                json.dumps({"status": "BLOCKED", "blockers": [{"reasons": ["GLOBAL_SUPPLIER_EVIDENCE_REQUIRED"]}]}),
                encoding="utf-8",
            )
            (arch / "landed_cost_register.json").write_text(
                json.dumps({"status": "PASSED", "selected_imports": []}),
                encoding="utf-8",
            )
            (acq / "global_supplier_import_acquisition_register.json").write_text(
                json.dumps({"status": "BLOCKED"}), encoding="utf-8"
            )
            result = enforce_landed_cost_gate(ws)
            self.assertEqual(result["status"], "BLOCKED")
            landed = json.loads((arch / "landed_cost_register.json").read_text(encoding="utf-8"))
            self.assertEqual(landed["gate_reason"], "IMPORT_REQUIRED_BUT_NO_COMPLETE_LANDED_COST_EVIDENCE")

    def test_empty_import_is_not_applicable_when_no_import_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            arch = ws / "results" / "session_adapters" / "architecture"
            arch.mkdir(parents=True)
            (arch / "global_material_sourcing_register.json").write_text(
                json.dumps({"status": "PASSED", "selected_import_count": 0, "blockers": []}), encoding="utf-8"
            )
            (arch / "landed_cost_register.json").write_text(
                json.dumps({"status": "PASSED", "selected_imports": []}), encoding="utf-8"
            )
            result = enforce_landed_cost_gate(ws)
            self.assertEqual(result["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
