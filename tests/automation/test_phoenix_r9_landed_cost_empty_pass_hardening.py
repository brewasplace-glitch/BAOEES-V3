from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.global_material_sourcing import build_global_material_sourcing_context


class R9LandedCostEmptyPassHardeningTests(unittest.TestCase):
    def context(self):
        return {
            "facts": {
                "country_code": "SR",
                "region": "Paramaribo",
                "municipality": "Paramaribo",
                "project_location": "Paramaribo",
                "currency": "SRD",
            }
        }

    def test_zero_imports_plus_unresolved_supply_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            local = {
                "selections": [{
                    "requirement_id": "REQ-ROOF-STRUCTURE-STRUCTURAL-STEEL-SECTION",
                    "element_role": "roof_structure",
                    "material_family": "structural_steel_section",
                    "commercial_availability_confirmed": False,
                    "engineering_qualification_status": "NOT_QUALIFIED",
                    "selected_product": None,
                    "selection_status": "AVAILABILITY_UNKNOWN",
                }]
            }
            result = build_global_material_sourcing_context(
                repository=root,
                workspace=root / "workspace",
                project_id="PLUTOSTRAAT",
                project_context=self.context(),
                local_selection_register=local,
                manifest={},
                policy={},
            )
            reg = result.landed_cost_register
            self.assertEqual(result.sourcing_register["selected_import_count"], 0)
            self.assertEqual(reg["status"], "BLOCKED")
            self.assertTrue(reg["empty_import_pass_forbidden"])
            self.assertEqual(
                reg["gate_reason"],
                "NO_SELECTED_IMPORTS_WHILE_MATERIAL_SUPPLY_REQUIREMENTS_REMAIN_UNRESOLVED",
            )

    def test_no_fabrication_guards_remain_false(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = build_global_material_sourcing_context(
                repository=root,
                workspace=root / "workspace",
                project_id="P2",
                project_context=self.context(),
                local_selection_register={"selections": []},
                manifest={},
                policy={},
            )
            reg = result.landed_cost_register
            self.assertFalse(reg["tax_or_duty_fabrication"])
            self.assertFalse(reg["freight_fabrication"])
            self.assertFalse(reg["fx_fabrication"])
            self.assertEqual(reg["production_release"], "LOCKED")


if __name__ == "__main__":
    unittest.main()
