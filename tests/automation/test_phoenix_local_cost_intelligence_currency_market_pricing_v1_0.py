import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

from phoenix.autonomy.local_cost_intelligence import (
    build_local_cost_market_context,
    calculate_cost_items,
    currency_for_country,
)

class LocalCostIntelligenceTests(unittest.TestCase):
    def make_repo(self):
        td=tempfile.TemporaryDirectory()
        repo=pathlib.Path(td.name)
        (repo/"configs"/"phoenix").mkdir(parents=True)
        for name in (
            "local_cost_intelligence_policy_v1_0.json",
            "currency_jurisdiction_catalog_v1_0.json",
            "market_price_source_registry_v1_0.json",
        ):
            src=ROOT/"configs"/"phoenix"/name
            (repo/"configs"/"phoenix"/name).write_text(src.read_text(encoding="utf-8"),encoding="utf-8")
        return td,repo

    def add_ratebook(self,repo,*,country="SR",currency="SRD",effective="2026-08-01",valid_until=None,region=None,city=None,price=1850.0):
        folder=repo/"inputs"/"market_prices"
        folder.mkdir(parents=True,exist_ok=True)
        md={
            "ratebook_id":"RB-1","title":"Local test ratebook","country_code":country,
            "currency":currency,"effective_date":effective,"source_name":"TEST LOCAL SOURCE",
            "confidence":"HIGH","taxes_included":False,
        }
        if valid_until: md["valid_until"]=valid_until
        if region: md["region_name"]=region
        if city: md["city"]=city
        rb={"metadata":md,"prices":[{
            "item_code":"CONC-001","description":"Beton C30/37","unit":"m3","unit_price":price,
            "components":{"material":1200.0,"labour":400.0,"equipment":150.0,"transport":100.0}
        }]}
        (folder/"ratebook.json").write_text(json.dumps(rb),encoding="utf-8")

    def context(self,country="SR",currency=None,region=None,municipality=None):
        facts={"country_code":country,"currency":currency,"region":region,"municipality":municipality}
        return {"facts":facts}

    def test_01_country_currency_catalog(self):
        td,repo=self.make_repo()
        try:
            self.assertEqual(currency_for_country(repo,"NL"),"EUR")
            self.assertEqual(currency_for_country(repo,"SR"),"SRD")
            self.assertEqual(currency_for_country(repo,"CW"),"XCG")
            self.assertEqual(currency_for_country(repo,"BQ"),"USD")
        finally: td.cleanup()

    def test_02_missing_country_blocks(self):
        td,repo=self.make_repo()
        try:
            result=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context={"facts":{}},manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertEqual(result.blockers[0]["reason"],"PROJECT_COUNTRY_REQUIRED_FOR_LOCAL_COSTS")
        finally: td.cleanup()

    def test_03_current_country_ratebook_passes_and_derives_local_currency(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo)
            result=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"PASSED")
            self.assertEqual(result.market_context["project_currency"],"SRD")
            self.assertEqual(result.market_context["selected_pricing_level"],"COUNTRY")
            self.assertFalse(result.market_context["fx_used"])
        finally: td.cleanup()

    def test_04_region_ratebook_requires_matching_project_region(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo,region="Paramaribo")
            blocked=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(blocked.status,"BLOCKED")
            self.assertTrue(any(x.get("reason")=="PROJECT_REGION_REQUIRED_FOR_REGIONAL_PRICEBOOK" for x in blocked.source_register["rejections"]))
            passed=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR",region="Paramaribo"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(passed.status,"PASSED")
            self.assertEqual(passed.market_context["selected_pricing_level"],"REGION")
        finally: td.cleanup()

    def test_05_stale_ratebook_blocks(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo,effective="2025-01-01")
            result=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertEqual(result.blockers[0]["reason"],"LOCAL_MARKET_PRICE_DATA_STALE")
        finally: td.cleanup()

    def test_06_valid_until_can_keep_official_period_current(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo,effective="2026-01-01",valid_until="2026-12-31")
            result=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"PASSED")
            self.assertEqual(result.market_context["primary_ratebook"]["freshness_basis"],"VALIDITY_WINDOW")
        finally: td.cleanup()

    def test_07_currency_mismatch_blocks_no_silent_fx(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo,currency="USD")
            result=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(result.status,"BLOCKED")
            self.assertEqual(result.blockers[0]["reason"],"LOCAL_MARKET_PRICE_CURRENCY_MISMATCH")
            self.assertFalse(result.market_context["fx_fallback_allowed"])
        finally: td.cleanup()

    def test_08_cost_line_carries_source_date_region_currency_and_no_fx(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo,region="Paramaribo")
            market=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR",region="Paramaribo"),manifest={},as_of_date="2026-08-03"
            )
            calc=calculate_cost_items(
                quantity_items=[{"item_code":"CONC-001","description":"Beton C30/37","unit":"m3","quantity":10}],
                market_result=market,
            )
            self.assertEqual(calc["status"],"PASSED")
            line=calc["items"][0]
            self.assertEqual(line["currency"],"SRD")
            self.assertEqual(line["line_total"],18500.0)
            self.assertEqual(line["price_source"]["effective_date"],"2026-08-01")
            self.assertEqual(line["price_source"]["region_name"],"Paramaribo")
            self.assertFalse(line["fx_used"])
        finally: td.cleanup()

    def test_09_tax_is_not_invented(self):
        td,repo=self.make_repo()
        try:
            self.add_ratebook(repo)
            market=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("SR"),manifest={},as_of_date="2026-08-03"
            )
            self.assertFalse(market.market_context["automatic_tax_application"])
            self.assertEqual(market.market_context["tax_policy_status"],"SOURCE_DECLARED")
        finally: td.cleanup()

    def test_10_no_ratebook_means_current_local_price_data_required(self):
        td,repo=self.make_repo()
        try:
            market=build_local_cost_market_context(
                repository=repo,project_id="P1",project_context=self.context("NL"),manifest={},as_of_date="2026-08-03"
            )
            self.assertEqual(market.status,"BLOCKED")
            self.assertEqual(market.blockers[0]["reason"],"CURRENT_LOCAL_MARKET_PRICE_DATA_REQUIRED")
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
