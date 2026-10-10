from __future__ import annotations

import unittest
from phoenix.autonomy.structured_product_evidence_acquisition import _query_plan

class R9TargetedMissingFamilyQueryPlanFixR1Tests(unittest.TestCase):
    def plan_text(self, family: str) -> str:
        selection={"requirement_id":"REQ-TEST","material_family":family,"element_role":"test"}
        route={"requirement_id":"REQ-TEST","material_family":family,"search_priority":[]}
        return " ".join(str(x.get("query") or "") for x in _query_plan(selection,route)).lower()

    def test_masonry_is_product_supplier_focused(self):
        text=self.plan_text("masonry_unit")
        self.assertIn("supplier",text)
        self.assertIn("manufacturer",text)
        self.assertIn("suriname",text)
        self.assertIn("compressive strength",text)
        self.assertIn("en 771-3",text)

    def test_concrete_is_local_ready_mix_supplier_focused(self):
        text=self.plan_text("structural_concrete")
        self.assertIn("ready mix",text)
        self.assertIn("supplier",text)
        self.assertIn("paramaribo",text)
        self.assertIn("suriname",text)
        self.assertIn("concrete class",text)

    def test_roof_steel_is_tube_hollow_section_focused(self):
        text=self.plan_text("structural_steel_section")
        self.assertIn("hollow section",text)
        self.assertIn("rhs",text)
        self.assertIn("shs",text)
        self.assertIn("chs",text)
        self.assertIn("suriname",text)
        self.assertIn("netherlands",text)
        self.assertIn("belgium",text)

    def test_rebar_existing_query_path_remains_available(self):
        plan=_query_plan(
            {"requirement_id":"REQ-REBAR","material_family":"reinforcement_steel","element_role":"reinforcement"},
            {"requirement_id":"REQ-REBAR","material_family":"reinforcement_steel","search_priority":["NETHERLANDS","EU27"]},
        )
        self.assertTrue(isinstance(plan,list) and len(plan)>0)

if __name__=="__main__":
    unittest.main()
