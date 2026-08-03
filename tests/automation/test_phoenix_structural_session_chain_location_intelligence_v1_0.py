import json
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

from phoenix.autonomy.location_intelligence import resolve_location_intelligence
from phoenix.autonomy.structural_session_chain import build_v81_input, STAGES

class StructuralChainLocationTests(unittest.TestCase):
    def test_01_chain_registry_covers_v8_1_through_v8_12(self):
        self.assertEqual([x[0] for x in STAGES],[f"8.{i}.0" for i in range(1,13)])
        self.assertEqual(len(STAGES),12)

    def test_02_v80_to_v81_mapping_is_geometric_not_design_value_invention(self):
        v80={
            "schema_version":"phoenix.structural-candidate-model/8.0.0",
            "columns":[{"structural_id":"C1","storey_id":"L0","x_m":0,"y_m":0,"material_hypothesis":"candidate"}],
            "beams":[{"structural_id":"B1","storey_id":"L0","start_x_m":0,"start_y_m":0,"end_x_m":5,"end_y_m":0,"material_hypothesis":"candidate"}],
            "walls":[{"structural_id":"W1","architectural_element_id":"L0-EW1","storey_id":"L0","candidate_type":"loadbearing_wall","thickness_m":0.3,"material_hypothesis":"candidate"}],
            "slabs":[{"panel_id":"S1","storey_id":"L0","architectural_space_id":"L0-R1","material_hypothesis":"candidate"}],
            "stability_zones":[],
        }
        arch={"storeys":[{"storey_id":"L0","elevation_m":0.0,"height_m":3.0,"spaces":[{"space_id":"L0-R1","x_m":0,"y_m":0,"width_m":5,"depth_m":4}]}]}
        detail={"storeys":[{"storey_id":"L0","walls":[{"element_id":"L0-EW1","storey_id":"L0","x1_m":0,"y1_m":0,"x2_m":5,"y2_m":0}]}]}
        payload,mapping=build_v81_input(v80,arch,detail)
        self.assertEqual(payload["structural_candidates"]["columns"][0]["top"],[0,0,3.0])
        self.assertEqual(payload["structural_candidates"]["beams"][0]["start"][2],3.0)
        self.assertEqual(len(payload["structural_candidates"]["loadbearing_walls"][0]["polygon"]),4)
        self.assertFalse(mapping["design_values_invented"])

    def test_03_amsterdam_location_resolves_nl_eur_without_ui_locale(self):
        with tempfile.TemporaryDirectory() as td:
            repo=pathlib.Path(td)
            (repo/"configs"/"phoenix").mkdir(parents=True)
            source=ROOT/"configs"/"phoenix"/"currency_jurisdiction_catalog_v1_0.json"
            (repo/"configs"/"phoenix"/source.name).write_text(source.read_text(encoding="utf-8"),encoding="utf-8")
            result=resolve_location_intelligence(
                repository=repo,project_id="P1",brief="Locatie: Amsterdam, Nederland",
                manifest={},project_context={"facts":{}},
            )
            self.assertEqual(result.status,"RESOLVED")
            self.assertEqual(result.fact_updates["country_code"],"NL")
            self.assertEqual(result.fact_updates["municipality"],"Amsterdam")
            self.assertEqual(result.fact_updates["currency"],"EUR")
            self.assertFalse(result.record["geocoding"]["ui_locale_used"])

    def test_04_paramaribo_locality_can_resolve_suriname_srd(self):
        with tempfile.TemporaryDirectory() as td:
            repo=pathlib.Path(td)
            (repo/"configs"/"phoenix").mkdir(parents=True)
            source=ROOT/"configs"/"phoenix"/"currency_jurisdiction_catalog_v1_0.json"
            (repo/"configs"/"phoenix"/source.name).write_text(source.read_text(encoding="utf-8"),encoding="utf-8")
            result=resolve_location_intelligence(
                repository=repo,project_id="P1",brief="Locatie: Paramaribo",
                manifest={},project_context={"facts":{}},
            )
            self.assertEqual(result.fact_updates["country_code"],"SR")
            self.assertEqual(result.fact_updates["currency"],"SRD")
            self.assertTrue(result.record["geocoding"]["known_locality_catalog_used"])

    def test_05_unknown_location_does_not_invent_country(self):
        with tempfile.TemporaryDirectory() as td:
            repo=pathlib.Path(td);(repo/"configs"/"phoenix").mkdir(parents=True)
            source=ROOT/"configs"/"phoenix"/"currency_jurisdiction_catalog_v1_0.json"
            (repo/"configs"/"phoenix"/source.name).write_text(source.read_text(encoding="utf-8"),encoding="utf-8")
            result=resolve_location_intelligence(
                repository=repo,project_id="P1",brief="Locatie: Onbekendeplaats 123",
                manifest={},project_context={"facts":{}},
            )
            self.assertIsNone(result.fact_updates["country_code"])
            self.assertTrue(any(x["reason"]=="PROJECT_COUNTRY_JURISDICTION_REQUIRED" for x in result.blockers))

    def test_06_structural_templates_do_not_contain_demo_design_values(self):
        text=(ROOT/"phoenix"/"autonomy"/"structural_session_chain.py").read_text(encoding="utf-8")
        self.assertIn("Phoenix vult belastingswaarden",text)
        self.assertIn('"actions":[]',text)
        self.assertIn('"materials":{}',text)
        self.assertIn("HUMAN_ENGINEERING_REVIEW_AND_RELEASE_AUTHORIZATION_REQUIRED",text)

if __name__=="__main__":
    unittest.main()
