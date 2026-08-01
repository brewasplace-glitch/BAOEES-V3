from pathlib import Path
import ast,json,unittest
R=Path(__file__).resolve().parents[2];C=R/"configs/phoenix/detailed_architectural_element_opening_engine_v6_6_0.json";P=R/"configs/projects/generic_building_detailed_architecture_v6_6_0.json";X=R/"runners/PROJECT_PHOENIX_detailed_architectural_element_opening_engine_v6_6_0.py"
ROOT=R
RUNNER=X
class T(unittest.TestCase):
 def test_generic(self):
  c=json.loads(C.read_text());self.assertFalse(c["pilot_project_dependency"])
 def test_catalog(self):
  p=json.loads(P.read_text());self.assertIn("element_catalog",p)
 def test_python(self):ast.parse(X.read_text())
 def test_elements(self):
  t=X.read_text()
  for x in ("external_walls","internal_walls","openings","roof","stairs","junctions"):self.assertIn(x,t)
 def test_hosting(self):
  t=X.read_text();self.assertIn("opening does not fit host",t)
 def test_gates(self):
  t=X.read_text();self.assertIn("permit_ready",t);self.assertIn("execution_ready",t)
if __name__=="__main__":unittest.main()


class WallScheduleSchemaAlignmentTests(unittest.TestCase):
    def test_wall_schedule_has_explicit_coordinates(self):
        text=RUNNER.read_text(encoding="utf-8")
        for marker in (
            "'start_x_m':x['start'][0]",
            "'start_y_m':x['start'][1]",
            "'end_x_m':x['end'][0]",
            "'end_y_m':x['end'][1]",
        ):
            self.assertIn(marker,text)

    def test_host_space_ids_are_serialized_deterministically(self):
        text=RUNNER.read_text(encoding="utf-8")
        self.assertIn("'|'.join(sorted(",text)
        self.assertIn("x.get('host_space_ids',[])",text)

    def test_csv_writer_remains_strict(self):
        text=RUNNER.read_text(encoding="utf-8")
        self.assertIn('extrasaction="raise"',text)

    def test_raw_wall_dict_is_not_written_directly(self):
        text=RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("thickness_m'],walls)",text)


class TestPathAlignmentRecoveryTests(unittest.TestCase):
    def test_canonical_runner_constant_is_defined(self):
        self.assertEqual(RUNNER, X)
        self.assertTrue(RUNNER.is_file())

    def test_canonical_root_constant_is_defined(self):
        self.assertEqual(ROOT, R)
        self.assertTrue(ROOT.is_dir())
