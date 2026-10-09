from __future__ import annotations

import unittest
from unittest.mock import patch

from phoenix.autonomy import global_supplier_import_acquisition as g


class StructuredProductEvidenceDataclassBridgeR9Tests(unittest.TestCase):
    def test_dataclass_result_is_bridged_to_dict_enhancer_and_legacy_type_preserved(self):
        base=g.AcquisitionResult(
            "BLOCKED",
            {"schema_version":"test"},
            {"request_count":1},
            [],
            [{"reason":"BASE_BLOCK"}],
        )
        seen={}

        def fake_enhance(value, *, args=(), kwargs=None):
            self.assertIsInstance(value,dict)
            self.assertEqual(value["status"],"BLOCKED")
            seen["called"]=True
            value["structured_product_evidence_enabled"]=True
            value["structured_product_evidence_register"]="projects/runtime/P/sources/import_acquisition/structured.json"
            value["production_release"]="LOCKED"
            return value

        with patch.object(
            g,
            "_phoenix_structured_evidence_original_acquire_global_supplier_import_evidence",
            return_value=base,
        ), patch.object(
            g,
            "_phoenix_structured_evidence_enhance",
            side_effect=fake_enhance,
        ):
            result=g.acquire_global_supplier_import_evidence(
                repository=None,
                workspace=None,
                project_id="P",
                project_context={},
                local_selection_register={},
                manifest={},
            )

        self.assertTrue(seen.get("called"))
        self.assertIs(result,base)
        self.assertTrue(result.register["structured_product_evidence_enabled"])
        self.assertEqual(result.register["production_release"],"LOCKED")

    def test_enhancer_failure_fails_closed_on_dataclass_result(self):
        base=g.AcquisitionResult("BLOCKED",{},{"request_count":1},[],[])
        with patch.object(
            g,
            "_phoenix_structured_evidence_original_acquire_global_supplier_import_evidence",
            return_value=base,
        ), patch.object(
            g,
            "_phoenix_structured_evidence_enhance",
            side_effect=RuntimeError("secret body must not escape"),
        ):
            result=g.acquire_global_supplier_import_evidence(
                repository=None,
                workspace=None,
                project_id="P",
                project_context={},
                local_selection_register={},
                manifest={},
            )

        self.assertIs(result,base)
        self.assertEqual(result.register["structured_product_evidence_runtime_status"],"BLOCKED")
        self.assertEqual(result.register["structured_product_evidence_runtime_error"],"RuntimeError")
        self.assertEqual(result.register["production_release"],"LOCKED")


if __name__=="__main__":
    unittest.main()
