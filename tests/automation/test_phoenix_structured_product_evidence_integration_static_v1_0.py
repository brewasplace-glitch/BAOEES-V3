import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StructuredProductEvidenceStaticIntegrationTests(unittest.TestCase):
    def test_policy_is_fail_safe(self):
        policy = json.loads((ROOT / "configs" / "phoenix" / "structured_product_evidence_material_route_policy_v1_0.json").read_text(encoding="utf-8"))
        p = policy["principles"]
        self.assertFalse(p["fabricate_certificates"])
        self.assertFalse(p["fabricate_material_properties"])
        self.assertFalse(p["fabricate_freight"])
        self.assertFalse(p["fabricate_customs"])
        self.assertFalse(p["automatic_ordering"])
        self.assertFalse(p["automatic_payment"])
        self.assertEqual(p["production_release"], "LOCKED")

    def test_acquisition_hook_marker_present(self):
        path = ROOT / "phoenix" / "autonomy" / "global_supplier_import_acquisition.py"
        text = path.read_text(encoding="utf-8-sig")
        self.assertIn("PHOENIX_STRUCTURED_PRODUCT_EVIDENCE_INTEGRATION_v1_0", text)
        self.assertIn("enhance_acquisition_result", text)

    def test_landed_cost_guard_hook_marker_present(self):
        found = []
        for path in (ROOT / "phoenix").rglob("*.py"):
            if path.name in {"landed_cost_gate_guard.py", "structured_product_evidence_acquisition.py"}:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            if "PHOENIX_LANDED_COST_FALSE_PASS_GUARD_v1_0" in text:
                found.append(path)
        self.assertEqual(len(found), 1, found)

    def test_no_credential_literal_in_policy(self):
        key = os.environ.get("PHOENIX_BRAVE_SEARCH_API_KEY", "")
        if not key:
            self.skipTest("No live credential in test process")
        for rel in [
            "configs/phoenix/structured_product_evidence_material_route_policy_v1_0.json",
            "docs/automation/PHOENIX_STRUCTURED_PRODUCT_EVIDENCE_MATERIAL_ROUTE_LANDED_COST_FIX_MASTERPACK_v1_0.md",
        ]:
            self.assertNotIn(key, (ROOT / rel).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
