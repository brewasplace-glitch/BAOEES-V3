import json
import pathlib
import tempfile
import unittest
import sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from phoenix.autonomy.architectural_bootstrap import generate_architectural_bootstrap

class ArchitecturalBootstrapTests(unittest.TestCase):
    def test_01_two_storey_detached_house_from_dutch_brief(self):
        r=generate_architectural_bootstrap(project_id="PHOENIX-PAT-001",project_type="BOUW",brief="PHOENIX-PAT-001\nOntwerp een vrijstaande woning van twee bouwlagen.")
        self.assertEqual(r.status,"PASSED")
        self.assertEqual(r.model["building"]["storey_count"],2)
        self.assertEqual(len(r.model["storeys"]),2)
    def test_02_default_dimensions_are_explicit_assumptions(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een woning van twee bouwlagen")
        items={x["id"]:x for x in r.assumptions["items"]}
        self.assertEqual(items["footprint_width_m"]["basis"],"AUTO_CONCEPT_DEFAULT")
        self.assertTrue(items["footprint_width_m"]["review_required"])
    def test_03_explicit_dimensions_are_preserved(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een woning van twee bouwlagen 12 x 9 m")
        self.assertEqual(r.model["building"]["footprint_width_m"],12.0)
        self.assertEqual(r.model["building"]["footprint_depth_m"],9.0)
    def test_04_no_site_facts_are_invented(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een woning")
        self.assertEqual(r.model["site_context"]["status"],"MISSING")
        self.assertIsNone(r.model["site_context"]["plot_boundary"])
    def test_05_no_structural_profile_is_fabricated(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een woning")
        self.assertEqual(r.structural_handoff["structural_profile_status"],"REQUIRED_SEPARATELY")
        self.assertTrue(r.structural_handoff["no_structural_material_or_load_assumptions_generated"])
    def test_06_final_drawings_not_falsely_passed(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een woning")
        self.assertNotEqual(r.desired_output_states["floor_plans"]["status"],"PASSED")
        self.assertEqual(r.desired_output_states["site_plan"]["status"],"BLOCKED")
    def test_07_unsupported_use_blocks_cleanly(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een onbekend gebouw")
        self.assertEqual(r.status,"BLOCKED")
        self.assertEqual(r.reason,"ARCHITECTURAL_USE_TYPE_REQUIRED")
    def test_08_model_has_dimensioned_spaces_and_elements(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een vrijstaande woning van twee bouwlagen")
        s=r.model["storeys"][0]
        self.assertTrue(s["spaces"]); self.assertTrue(s["walls"]); self.assertTrue(s["doors"]); self.assertTrue(s["windows"])
        self.assertGreater(s["spaces"][0]["width_m"],0)
    def test_09_production_release_locked(self):
        r=generate_architectural_bootstrap(project_id="P",project_type="BOUW",brief="Ontwerp een woning")
        self.assertEqual(r.model["production_release"],"LOCKED")
        self.assertFalse(r.model["professional_approval"])

if __name__=='__main__': unittest.main()
