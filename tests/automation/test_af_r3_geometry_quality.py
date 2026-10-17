import importlib.util
import pathlib
import unittest
HERE=pathlib.Path(__file__).resolve()
ROOT=next((p for p in (HERE.parents[1], HERE.parents[2]) if (p/'phoenix'/'afoundation'/'geometry_quality.py').is_file()), None)
if ROOT is None: raise RuntimeError('Geometry QA module not found at package or repository root')
SPEC=importlib.util.spec_from_file_location('geometry_quality', ROOT/'phoenix'/'afoundation'/'geometry_quality.py')
mod=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mod)

def data(segments):
 return {'schema':mod.SCHEMA,'units':'mm','coordinate_system':'source_world_xy','evidence_status':'MEASURED','segments':segments}

class GeometryTests(unittest.TestCase):
 def test_exact(self):
  x=data([[[0,0],[100,0]]]); r=mod.evaluate(x,x)
  self.assertEqual(r['metrics']['source_edge_coverage_pct'],100)
  self.assertEqual(r['gates']['architectural_wall_identity'],'NOT_EVALUATED')
 def test_gap(self):
  r=mod.evaluate(data([[[0,0],[100,0]]]),data([[[0,0],[60,0]]]))
  self.assertEqual(r['metrics']['source_edge_coverage_pct'],60)
 def test_duplicates_do_not_overcount(self):
  r=mod.evaluate(data([[[0,0],[100,0]]]),data([[[0,0],[100,0]],[[0,0],[100,0]]]))
  self.assertEqual(r['metrics']['source_edge_coverage_pct'],100)
 def test_regression_blocks(self):
  r=mod.evaluate(data([[[0,0],[100,0]]]),data([[[0,0],[50,0]]]),baseline={'metrics':{'source_edge_coverage_pct':60}})
  self.assertEqual(r['status'],'REGRESSION_BLOCKED')
 def test_missing_evidence_blocks(self):
  x=data([[[0,0],[100,0]]]);x['evidence_status']='UNVERIFIED'
  with self.assertRaises(ValueError):mod.evaluate(x,data([[[0,0],[100,0]]]))
 def test_offset_rejects(self):
  r=mod.evaluate(data([[[0,0],[100,0]]]),data([[[0,30],[100,30]]]))
  self.assertEqual(r['metrics']['source_edge_coverage_pct'],0)
 def test_overlap_merge(self):
  r=mod.evaluate(data([[[0,0],[100,0]]]),data([[[0,0],[60,0]],[[40,0],[100,0]]]))
  self.assertEqual(r['metrics']['source_edge_coverage_pct'],100)
 def test_source_r4_format(self):
  d={'components':{'floorplan':{'edges':[[[0,0,0],[100,0,0]]]}}}
  self.assertEqual(len(mod.get_edges(d,'source')),1)

if __name__=='__main__':unittest.main()
