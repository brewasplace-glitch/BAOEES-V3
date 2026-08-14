import os,tempfile,unittest
from pathlib import Path
from phoenix.autonomy.pat001_opensees_live_evidence_v1_0 import *
DECK="""model BasicBuilder -ndm 3 -ndf 6
node 1 0 0 0
node 2 5 0 0
node 3 5 4 0
node 4 0 4 0
element elasticBeamColumn 1 1 2 1 1 1 1 1 1 1 ;# M0001
element elasticBeamColumn 2 2 3 1 1 1 1 1 1 1 ;# M0002
element ShellMITC4 1 1 2 3 4 1 ;# S0001
load 2 0 0 -10 0 0 0 ;# N0002
analysis Static
set ok [analyze 1]
if {$ok != 0} { error "OpenSees analysis failed" }
puts "PHOENIX_ANALYSIS_OK"
puts "PHX_NODE N0001 DISP [nodeDisp 1] REACTION [nodeReaction 1]"
puts "PHX_NODE N0002 DISP [nodeDisp 2] REACTION [nodeReaction 2]"
puts "PHX_NODE N0003 DISP [nodeDisp 3] REACTION [nodeReaction 3]"
puts "PHX_NODE N0004 DISP [nodeDisp 4] REACTION [nodeReaction 4]"
"""

TRI_DECK="""model BasicBuilder -ndm 3 -ndf 6
node 1 0 0 0
node 2 5 0 0
node 3 5 4 0
node 4 0 4 0
element elasticBeamColumn 1 1 2 1 1 1 1 1 1 1 ;# M0001
element elasticBeamColumn 2 2 3 1 1 1 1 1 1 1 ;# M0002
element ShellMITC4 1 1 2 3 4 1 ;# S0001
element ShellDKGT 2 1 3 4 1 ;# S0002
puts "PHOENIX_ANALYSIS_OK"
puts "PHX_NODE N0001 DISP 0 0 0 0 0 0 REACTION 0 0 0 0 0 0"
"""
STD="""PHOENIX_ANALYSIS_OK
PHX_NODE N0001 DISP 0 0 0 0 0 0 REACTION 0 0 10 0 0 0
PHX_NODE N0002 DISP 0 0 -0.01 0 0 0 REACTION 0 0 0 0 0 0
PHX_NODE N0003 DISP 0 0 -0.005 0 0 0 REACTION 0 0 0 0 0 0
PHX_NODE N0004 DISP 0 0 0 0 0 0 REACTION 0 0 0 0 0 0
PHX_ELEMENT_FORCE MEMBER M0001 TAG 1 VALUES {1 2 3}
PHX_ELEMENT_STRESS MEMBER M0001 TAG 1 VALUES {}
PHX_ELEMENT_FORCE MEMBER M0002 TAG 2 VALUES {3 2 1}
PHX_ELEMENT_STRESS MEMBER M0002 TAG 2 VALUES {}
PHX_ELEMENT_FORCE SHELL S0001 TAG 3 VALUES {1 2 3}
PHX_ELEMENT_STRESS SHELL S0001 TAG 3 VALUES {4 5 6}
PHOENIX_EVIDENCE_CAPTURE_OK
"""
class T(unittest.TestCase):
 def test01_collision(self): self.assertEqual([1],tag_maps(DECK)["source_collisions"])
 def test02_repair(self): self.assertEqual(3,tag_maps(DECK)["execution_shell_tags"]["S0001"])
 def test03_unique(self):
  t=tag_maps(DECK);v=list(t["execution_member_tags"].values())+list(t["execution_shell_tags"].values());self.assertEqual(len(v),len(set(v)))
 def test04_shell_preserved(self): self.assertIn("element ShellMITC4 3",harden_deck(DECK)[0])
 def test05_reactions(self):
  h,a=harden_deck(DECK);self.assertTrue(a["reaction_command_inserted"]);self.assertLess(h.index("\nreactions\n"),h.index('puts "PHX_NODE'))
 def test06_marker(self): self.assertIn("PHOENIX_EVIDENCE_CAPTURE_OK",harden_deck(DECK)[0])
 def test07_member_capture(self): self.assertIn("PHX_ELEMENT_FORCE MEMBER M0001 TAG 1",harden_deck(DECK)[0])
 def test08_shell_capture(self): self.assertIn("PHX_ELEMENT_FORCE SHELL S0001 TAG 3",harden_deck(DECK)[0])
 def test09_load(self): self.assertEqual([0.0,0.0,-10.0],applied(DECK))
 def nr(self):
  h,_=harden_deck(DECK);return normalize(STD,["N0001","N0002","N0003","N0004"],tag_maps(h),h)
 def test10_norm(self): self.assertEqual("COMPLETE",self.nr()["normalization_status"])
 def test11_disp(self): self.assertEqual(-0.01,self.nr()["node_results"]["N0002"]["displacement"][2])
 def test12_react(self): self.assertEqual(10.0,self.nr()["node_results"]["N0001"]["reaction"][2])
 def test13_force(self): self.assertEqual([1.0,2.0,3.0],self.nr()["element_results"]["S0001"]["force"])
 def test14_stress(self): self.assertEqual([4.0,5.0,6.0],self.nr()["element_results"]["S0001"]["stress"])
 def test15_residual(self): self.assertEqual([0.0,0.0,0.0],self.nr()["global_equilibrium_evidence"]["residual_force"])
 def test16_no_tol(self): self.assertIsNone(self.nr()["global_equilibrium_evidence"]["acceptance_tolerance"])
 def test17_case_ok(self): self.assertTrue(case_ok(0,STD,self.nr())["qualified"])
 def test18_nonzero(self): self.assertFalse(case_ok(1,STD,self.nr())["qualified"])
 def test19_missing_marker(self): self.assertFalse(case_ok(0,STD.replace("PHOENIX_EVIDENCE_CAPTURE_OK",""),self.nr())["qualified"])
 def test20_exe_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"OpenSees.exe";p.write_bytes(b"x");r=discover_executable(str(p));self.assertEqual(64,len(r["sha256"]))
 def test21_safety1(self): self.assertFalse(SAFETY["source_v8_3_decks_overwritten"])
 def test22_safety2(self): self.assertFalse(SAFETY["automatic_professional_approval"])
 def test23_safety3(self): self.assertEqual("LOCKED",SAFETY["production_release"])
 def test24_safety4(self): self.assertFalse(SAFETY["scia_gap_changed"])
 def test25_combined_stream_preserves_stderr_semantics(self):
  c=solver_console_output("",STD);self.assertIn("PHOENIX_ANALYSIS_OK",c);self.assertIn("PHX_NODE N0001",c)
 def test26_marker_stream_detection_stderr(self):
  r=marker_streams("PHOENIX_OPENSEES_PROBE_OK","","banner\nPHOENIX_OPENSEES_PROBE_OK\n");self.assertFalse(r["stdout"]);self.assertTrue(r["stderr"])
 def test27_stderr_only_results_normalize(self):
  h,_=harden_deck(DECK);r=normalize(solver_console_output("",STD),["N0001","N0002","N0003","N0004"],tag_maps(h),h);self.assertEqual("COMPLETE",r["normalization_status"])
 def test28_stderr_only_markers_qualify(self):
  h,_=harden_deck(DECK);combined=solver_console_output("",STD);r=normalize(combined,["N0001","N0002","N0003","N0004"],tag_maps(h),h);self.assertTrue(case_ok(0,combined,r)["qualified"])

 def test29_shelldkgt_is_recognized_as_shell(self):
  t=tag_maps(TRI_DECK);self.assertIn("S0002",t["source_shell_tags"]);self.assertEqual("ShellDKGT",t["source_shell_element_types"]["S0002"])
 def test30_all_shell_types_are_preserved(self):
  h,_=harden_deck(TRI_DECK);self.assertIn("element ShellMITC4 3",h);self.assertIn("element ShellDKGT 4",h)
 def test31_triangle_and_quad_collisions_are_repaired(self):
  t=tag_maps(TRI_DECK);self.assertEqual([1,2],t["source_collisions"]);self.assertEqual(3,t["execution_shell_tags"]["S0001"]);self.assertEqual(4,t["execution_shell_tags"]["S0002"])
 def test32_shell_type_counts_are_audited(self):
  t=tag_maps(TRI_DECK);self.assertEqual({"ShellDKGT":1,"ShellMITC4":1},t["source_shell_type_counts"])
 def test33_model_coverage_complete(self):
  t=tag_maps(TRI_DECK);r=assert_model_coverage(t,["M0001","M0002"],["S0001","S0002"]);self.assertTrue(r["complete"]);self.assertEqual(4,r["expected_element_count"])
 def test34_model_coverage_blocks_missing_triangle(self):
  t=tag_maps(DECK)
  with self.assertRaises(ValueError):assert_model_coverage(t,["M0001","M0002"],["S0001","S0002"])
 def test35_hardened_element_tags_globally_unique_across_shell_types(self):
  h,_=harden_deck(TRI_DECK);t=tag_maps(h);v=list(t["execution_member_tags"].values())+list(t["execution_shell_tags"].values());self.assertEqual(len(v),len(set(v)))
 def test36_shell_command_is_not_rewritten_to_mitc4(self):
  h,_=harden_deck(TRI_DECK);self.assertIn("element ShellDKGT 4",h);self.assertNotIn("element ShellMITC4 4",h)

if __name__=="__main__":unittest.main()
