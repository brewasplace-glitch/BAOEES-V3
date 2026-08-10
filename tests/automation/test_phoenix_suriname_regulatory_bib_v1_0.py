from __future__ import annotations
import hashlib, os, sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ["PHOENIX_REPO_ROOT"]=str(ROOT)
from phoenix.knowledge.suriname_regulatory_bib_v1_0 import *
class T(unittest.TestCase):
 def test_01(self): self.assertEqual(3,len(load_source_registry()["sources"]))
 def test_02(self): self.assertGreater(source_priority(source_by_id("SR-SUR-BW-1956-001")),source_priority(source_by_id("SR-SUR-BB1-1956-001")))
 def test_03(self): self.assertFalse(automatic_numeric_use_allowed("SR-SUR-BG-2026-001"))
 def test_04(self): self.assertEqual(3,len(applicable_sources("Paramaribo, Suriname")))
 def test_05(self): self.assertEqual([],applicable_sources("Bunschoten, Nederland"))
 def test_06(self): self.assertAlmostEqual(1.96133,rule_by_id("SUR-BB1-A30-LIVE-RESIDENTIAL-FLOOR")["normalized_si"]["value"],5)
 def test_07(self): self.assertAlmostEqual(.588399,rule_by_id("SUR-BB1-A30-WIND-BASE")["normalized_si"]["base_stuwdruk"],6)
 def test_08(self): self.assertAlmostEqual(23.53596,rule_by_id("SUR-BB1-A29-SELFWEIGHT-RC")["normalized_si"]["value"],5)
 def test_09(self): self.assertGreaterEqual(len(rules(category="FOUNDATION")),2)
 def test_10(self): self.assertEqual("NOT_ESTABLISHED_BY_SOURCE",r9_4_local_source_bridge()["GLOBAL_BUCKLING_FACTOR"]["v8_6_acceptance_limit"])
 def test_11(self): self.assertEqual("NOT_ESTABLISHED_BY_UPLOADED_PRIMARY_SOURCES",r9_4_local_source_bridge()["eurocode_2_legal_adoption"])
 def test_12(self): self.assertFalse(load_policy()["calculation_behavior"]["automatic_override_between_local_rule_and_foreign_standard"])
 def test_13(self): self.assertFalse(load_knowledge()["summary"]["current_legal_status_verified_for_2026"])
 def test_14(self):
  for s in load_source_registry()["sources"]:
   p=ROOT/s["file"]; self.assertTrue(p.is_file()); self.assertEqual(s["sha256"],hashlib.sha256(p.read_bytes()).hexdigest())
 def test_15(self): self.assertEqual("LOCKED",build_project_regulatory_context(location="Paramaribo, Suriname")["safety"]["production_release"])
 def test_16(self): self.assertIn("SUR-BB1-A30-WIND-BASE",build_project_regulatory_context(location="Paramaribo, Suriname")["rule_ids"])
if __name__=="__main__": unittest.main()
