from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from phoenix.autonomy.global_material_sourcing import build_global_material_sourcing_context


class GlobalMaterialSourcingTests(unittest.TestCase):
    def _base(self):
        root = Path(tempfile.mkdtemp(prefix="phoenix_global_sourcing_"))
        ws = root / "projects" / "runtime" / "P1"
        (ws / "sources" / "global_material_supply").mkdir(parents=True)
        (root / "configs" / "phoenix").mkdir(parents=True)
        (root / "configs" / "phoenix" / "global_material_sourcing_policy_v1_0.json").write_text(
            json.dumps({
                "allow_configured_https_json_sources": True,
                "availability_max_age_days": 30,
                "price_max_age_days": 30,
                "freight_max_age_days": 14,
                "fx_max_age_days": 7
            }), encoding="utf-8"
        )
        context = {"facts": {
            "country_code": "SR", "municipality": "Paramaribo",
            "project_location": "Paramaribo, Suriname", "currency": "SRD"
        }}
        return root, ws, context

    def test_01_cheapest_landed_not_cheapest_product_price_is_selected(self):
        root, ws, context = self._base()
        local = {"selections": [{
            "requirement_id": "REQ-REBAR", "element_role": "reinforcement",
            "material_family": "reinforcement_steel",
            "commercial_availability_confirmed": False,
            "engineering_qualification_status": "NOT_QUALIFIED",
            "selected_product": None
        }]}
        catalog = {"metadata": {
            "currency": "SRD", "availability_verified_date": "2026-08-04",
            "price_date": "2026-08-04"
        }, "products": [
            {
                "product_id": "CHEAP-EX-WORKS-EXPENSIVE-DELIVERED",
                "supplier_name": "Supplier A", "country_code": "TR",
                "material_family": "reinforcement_steel",
                "availability_status": "AVAILABLE_TO_ORDER",
                "engineering_material_id": "REINFORCEMENT_B500B",
                "technical_properties": {"declared_reinforcement_grade": "B500B", "yield_strength_mpa": 500},
                "certifications": [{"standard": "EN 10080", "certificate_id": "A"}],
                "quote_quantity": 1000, "unit": "kg", "unit_price": 20,
                "landed_cost": {"landed_cost_total_srd": 110000, "delivered_to": "Paramaribo"}
            },
            {
                "product_id": "BEST-LANDED",
                "supplier_name": "Supplier B", "country_code": "CN",
                "material_family": "reinforcement_steel",
                "availability_status": "AVAILABLE_TO_ORDER",
                "engineering_material_id": "REINFORCEMENT_B500B",
                "technical_properties": {"declared_reinforcement_grade": "B500B", "yield_strength_mpa": 500},
                "certifications": [{"standard": "EN 10080", "certificate_id": "B"}],
                "quote_quantity": 1000, "unit": "kg", "unit_price": 25,
                "landed_cost": {"landed_cost_total_srd": 90000, "delivered_to": "Paramaribo"}
            }
        ]}
        (ws / "sources" / "global_material_supply" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        result = build_global_material_sourcing_context(
            repository=root, workspace=ws, project_id="P1", project_context=context,
            local_selection_register=local, manifest={}
        )
        self.assertEqual("PASSED", result.status)
        selection = result.structural_selection_register["selections"][0]
        self.assertEqual("BEST-LANDED", selection["selected_product"]["product_id"])
        self.assertEqual("INTERNATIONAL_IMPORT", selection["procurement_route"])
        self.assertEqual(90.0, selection["selected_product"]["landed_cost"]["landed_cost_per_unit_srd"])

    def test_02_uncertified_product_cannot_pass(self):
        root, ws, context = self._base()
        local = {"selections": [{
            "requirement_id": "REQ-REBAR", "element_role": "reinforcement",
            "material_family": "reinforcement_steel",
            "commercial_availability_confirmed": False,
            "engineering_qualification_status": "NOT_QUALIFIED",
            "selected_product": None
        }]}
        catalog = {"metadata": {"currency": "SRD"}, "products": [{
            "product_id": "NO-CERT", "supplier_name": "X", "country_code": "CN",
            "material_family": "reinforcement_steel",
            "availability_status": "AVAILABLE_TO_ORDER",
            "engineering_material_id": "REINFORCEMENT_B500B",
            "technical_properties": {"declared_reinforcement_grade": "B500B"},
            "certifications": [], "quote_quantity": 1000, "unit": "kg",
            "landed_cost": {"landed_cost_total_srd": 1000, "delivered_to": "Paramaribo"}
        }]}
        (ws / "sources" / "global_material_supply" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        result = build_global_material_sourcing_context(
            repository=root, workspace=ws, project_id="P1", project_context=context,
            local_selection_register=local, manifest={}
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertIn("CERTIFIED_ENGINEERING_QUALIFIED_PRODUCT_REQUIRED", result.blockers[0]["reasons"])

    def test_03_missing_landed_cost_cannot_pass(self):
        root, ws, context = self._base()
        local = {"selections": [{
            "requirement_id": "REQ-TIMBER", "element_role": "roof_structure",
            "material_family": "structural_timber",
            "commercial_availability_confirmed": False,
            "engineering_qualification_status": "NOT_QUALIFIED",
            "selected_product": None
        }]}
        catalog = {"metadata": {"currency": "USD"}, "products": [{
            "product_id": "C24", "supplier_name": "TimberCo", "country_code": "NL",
            "material_family": "structural_timber", "availability_status": "AVAILABLE_TO_ORDER",
            "engineering_material_id": "TIMBER_C24",
            "technical_properties": {"declared_timber_strength_class": "C24"},
            "certifications": [{"standard": "EN 338", "certificate_id": "C24-CERT"}],
            "unit_price": 400, "quote_quantity": 10, "unit": "m3"
        }]}
        (ws / "sources" / "global_material_supply" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        result = build_global_material_sourcing_context(
            repository=root, workspace=ws, project_id="P1", project_context=context,
            local_selection_register=local, manifest={}
        )
        self.assertEqual("BLOCKED", result.status)
        self.assertIn("COMPLETE_LANDED_COST_TO_PARAMARIBO_EVIDENCE_REQUIRED", result.blockers[0]["reasons"])

    def test_04_automatic_ordering_is_never_enabled(self):
        root, ws, context = self._base()
        result = build_global_material_sourcing_context(
            repository=root, workspace=ws, project_id="P1", project_context=context,
            local_selection_register={"selections": []}, manifest={}
        )
        self.assertFalse(result.sourcing_register["automatic_ordering"])
        self.assertFalse(result.structural_selection_register["automatic_ordering"])

    def test_05_ready_mix_import_does_not_gain_qualification_by_description_only(self):
        root, ws, context = self._base()
        local = {"selections": [{
            "requirement_id": "REQ-CONC", "element_role": "column",
            "material_family": "structural_concrete",
            "commercial_availability_confirmed": False,
            "engineering_qualification_status": "NOT_QUALIFIED",
            "selected_product": None
        }]}
        catalog = {"metadata": {"currency": "SRD"}, "products": [{
            "product_id": "WET-CONCRETE", "supplier_name": "Foreign Concrete", "country_code": "NL",
            "description": "Ready-mix concrete C25/30", "material_family": "structural_concrete",
            "availability_status": "AVAILABLE_TO_ORDER", "engineering_material_id": "CONCRETE_C25_30",
            "technical_properties": {"declared_concrete_strength_class": "C25/30"},
            "certifications": [{"standard": "EN 206", "certificate_id": "EN206"}],
            "quote_quantity": 10, "unit": "m3",
            "landed_cost": {"landed_cost_total_srd": 50000, "delivered_to": "Paramaribo"}
        }]}
        (ws / "sources" / "global_material_supply" / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        result = build_global_material_sourcing_context(
            repository=root, workspace=ws, project_id="P1", project_context=context,
            local_selection_register=local, manifest={}
        )
        self.assertEqual("BLOCKED", result.status)


if __name__ == "__main__":
    unittest.main()
