import json
import os
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

from phoenix.autonomy.public_html_source_integration import normalize_material_catalog, normalize_market_ratebook
from phoenix.autonomy.site_parcel_intelligence import analyze_site_drawings
from phoenix.autonomy.local_material_supply_intelligence import build_local_material_supply_context

class RealWorldSourceAdvancedSiteTests(unittest.TestCase):
    def test_01_bestbuy_style_html_normalizes_prices_and_availability(self):
        raw=("Beton Ijzer Rond 12 Gerib SRD 535,00 Beschikbaar Toevoegen "
             "Beton Ijzer Rond 16 Gerib SRD 960,00 Beschikbaar Toevoegen "
             "Steen 4'' VABI SRD 30,50 Toevoegen").encode()
        provider={"provider_id":"TEST","country_code":"SR","region_name":"Paramaribo","municipality":"Paramaribo","currency":"SRD","source_name":"TEST","url":"https://example.test"}
        catalog=normalize_material_catalog(raw,provider,"2026-08-03T12:00:00+00:00")
        self.assertTrue(any(x["material_family"]=="reinforcement_steel" for x in catalog["products"]))
        self.assertTrue(any(x["availability_status"]=="AVAILABLE_TO_ORDER" for x in catalog["products"]))
        ratebook=normalize_market_ratebook(raw,provider,"2026-08-03T12:00:00+00:00")
        self.assertGreaterEqual(len(ratebook["prices"]),3)
        self.assertEqual(ratebook["metadata"]["currency"],"SRD")

    def test_02_supplier_capability_can_confirm_commercial_concrete_without_engineering_id(self):
        raw=b"SUBEMA ready mix concrete public evidence"
        provider={"provider_id":"SUBEMA","country_code":"SR","region_name":"Paramaribo","municipality":"Paramaribo","currency":"SRD","source_name":"SUBEMA","supplier_name":"SUBEMA","url":"https://example.test","capability_records":[{"product_id":"READY","description":"Ready-mix concrete C8/10-C53/65","material_family":"structural_concrete","availability_status":"AVAILABLE_TO_ORDER","unit":"m3","technical_properties":{"declared_grade_range":"C8/10-C53/65"}}]}
        cat=normalize_material_catalog(raw,provider,"2026-08-03T12:00:00+00:00")
        product=cat["products"][0]
        self.assertEqual(product["material_family"],"structural_concrete")
        self.assertIsNone(product["engineering_material_id"])

    def test_03_material_engine_separates_commercial_from_engineering_qualification(self):
        td=tempfile.TemporaryDirectory();repo=pathlib.Path(td.name)
        try:
            (repo/"configs/phoenix").mkdir(parents=True)
            for name in ("local_material_supply_policy_v1_0.json","material_supply_source_registry_v1_0.json"):
                src=ROOT/"configs/phoenix"/name;(repo/"configs/phoenix"/name).write_text(src.read_text(encoding="utf-8"),encoding="utf-8")
            folder=repo/"inputs/material_supply";folder.mkdir(parents=True)
            products=[]
            for family in ("masonry_unit","structural_concrete","reinforcement_steel","structural_timber"):
                products.append({"product_id":family,"description":family,"material_family":family,"availability_status":"AVAILABLE_TO_ORDER","availability_verified_date":"2026-08-03","unit":"piece","technical_properties":{"candidate":True}})
            (folder/"local.json").write_text(json.dumps({"metadata":{"catalog_id":"C","supplier_id":"S","supplier_name":"S","country_code":"SR","region_name":"Paramaribo","city":"Paramaribo","currency":"SRD","source_name":"S","availability_verified_date":"2026-08-03"},"products":products}))
            profile={"assumptions":{"default_wall_material":"masonry_candidate","default_column_material":"reinforced_concrete_candidate","default_slab_material":"reinforced_concrete_candidate","default_beam_material":"reinforced_concrete_candidate","default_roof_material":"timber_candidate"}}
            result=build_local_material_supply_context(repository=repo,project_id="P",architectural_model={"building":{"type":"house"}},structural_profile=profile,project_context={"facts":{"country_code":"SR","region":"Paramaribo","municipality":"Paramaribo"}},manifest={},as_of_date="2026-08-03")
            self.assertTrue(result.selection_register["all_requirements_commercially_available"])
            self.assertFalse(result.selection_register["all_structural_requirements_engineering_qualified"])
            self.assertEqual(result.status,"BLOCKED")
        finally:td.cleanup()

    def test_04_vector_pdf_with_explicit_scale_can_yield_site_dimensions(self):
        try:import fitz
        except Exception:self.skipTest("PyMuPDF not installed")
        td=tempfile.TemporaryDirectory();root=pathlib.Path(td.name)
        try:
            pdf=root/"site.pdf";doc=fitz.open();page=doc.new_page(width=595,height=842)
            page.insert_text((60,60),"SITUATIE  Schaal 1:500  Anijstraat 616")
            # 20 x 30 m at 1:500 -> about 113.4 x 170.1 pt
            page.draw_rect(fitz.Rect(100,120,213.3858,290.0787),color=(0,0,0),width=1)
            doc.save(str(pdf));doc.close()
            result=analyze_site_drawings(project_id="P",upload_paths=[pdf],base_site_context={"status":"SCHEMATIC_ASSUMPTION"},brief="",repository=root)
            self.assertEqual(result.status,"PASSED")
            self.assertAlmostEqual(result.site_context["plot"]["width_m"],20,delta=1.0)
            self.assertAlmostEqual(result.site_context["plot"]["depth_m"],30,delta=1.0)
            self.assertFalse(result.site_context["cadastral_validation"])
        finally:td.cleanup()

    def test_05_pdf_without_scale_or_dimensions_does_not_false_pass(self):
        try:import fitz
        except Exception:self.skipTest("PyMuPDF not installed")
        td=tempfile.TemporaryDirectory();root=pathlib.Path(td.name)
        try:
            pdf=root/"photo.pdf";doc=fitz.open();page=doc.new_page();page.insert_text((50,50),"Google foto locatie");page.draw_rect(fitz.Rect(50,100,500,500));doc.save(str(pdf));doc.close()
            result=analyze_site_drawings(project_id="P",upload_paths=[pdf],base_site_context={"status":"SCHEMATIC_ASSUMPTION"},brief="",repository=root)
            self.assertEqual(result.status,"NO_NEW_EVIDENCE")
        finally:td.cleanup()


    def test_06_kuldipsingh_style_html_normalizes_srd_price_and_store_availability(self):
        raw=("UNITED Cement 40 kg 126416 SRD 354,55 excl. BTW "
             "Alleen beschikbaar in de winkels "
             "Betonnen U-Goot 3000x700x600mm C30/37 SRD 12.377,75 excl. BTW "
             "Alleen beschikbaar in de winkels").encode()
        provider={
            "provider_id":"KULDIPSINGH-TEST",
            "country_code":"SR","region_name":"Paramaribo","municipality":"Paramaribo",
            "currency":"SRD","source_name":"Kuldipsingh test",
            "url":"https://webshop.kuldipsingh.net/nl/bouwmaterialen",
            "taxes_included":False
        }
        catalog=normalize_material_catalog(raw,provider,"2026-08-03T12:00:00+00:00")
        self.assertTrue(catalog["products"])
        self.assertTrue(any(x["availability_status"]=="AVAILABLE_TO_ORDER" for x in catalog["products"]))
        ratebook=normalize_market_ratebook(raw,provider,"2026-08-03T12:00:00+00:00")
        prices=[x["unit_price"] for x in ratebook["prices"]]
        self.assertIn(354.55,prices)
        self.assertIn(12377.75,prices)
        self.assertFalse(ratebook["metadata"]["taxes_included"])


if __name__=="__main__":unittest.main()
