from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from phoenix.structural.regional_profiles import RegionalStructuralProfileRegistry
from phoenix.structural.sketch_input_recognition import SketchInputRecognitionEngine, ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, render_preview_svg
from phoenix.structural.reinforced_concrete_beam import ReinforcedConcreteBeamDesignEngine
ROOT=Path(__file__).resolve().parents[2]
REG=RegionalStructuralProfileRegistry(ROOT/'configs/structural/regional_structural_profiles_v1_0_0.json')
SAMPLE=ROOT/'examples/structural_sketch_input/sample_rc_beam_sketch_SUR.png'
CONF=json.loads((ROOT/'examples/structural_sketch_input/sample_rc_beam_sketch_SUR_confirmation.json').read_text())
ENG=json.loads((ROOT/'examples/structural_sketch_input/sample_SUR_engineer_basis_confirmation.json').read_text())
BASE=json.loads((ROOT/'configs/structural/reinforced_concrete_beam_example_v1_0_0.json').read_text())
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=SketchInputRecognitionEngine(ROOT); cls.rec=cls.engine.recognize(SAMPLE,'SUR',None,CONF); cls.profile=REG.get('SUR'); cls.cfg=cls.engine.to_beam_config(cls.rec,cls.profile,ENG,BASE); cls.design=ReinforcedConcreteBeamDesignEngine().evaluate(cls.cfg)
    def test_profile_count(self): self.assertEqual(7,len(REG.describe()))
    def test_all_codes(self): self.assertEqual({'SUR','BES-BON','BES-EUX','BES-SAB','ABW','CUR','SXM'},{x['jurisdiction_code'] for x in REG.describe()})
    def test_sur_reference(self): self.assertIn('gov.sr',REG.get('SUR')['legal_context'][0]['url'])
    def test_bes_reference(self): self.assertIn('wetten.overheid.nl',REG.get('BES-BON')['legal_context'][0]['url'])
    def test_aruba_reference(self): self.assertIn('gobierno.aw',REG.get('ABW')['legal_context'][0]['url'])
    def test_curacao_reference(self): self.assertIn('gobiernu.cw',REG.get('CUR')['legal_context'][0]['url'])
    def test_sxm_reference(self): self.assertIn('sintmaartengov.org',REG.get('SXM')['legal_context'][0]['url'])
    def test_unknown_profile_rejected(self):
        with self.assertRaises(KeyError): REG.get('XXX')
    def test_allowed_formats(self): self.assertEqual({'.png','.jpg','.jpeg','.bmp','.tif','.tiff','.pdf'},ALLOWED_EXTENSIONS)
    def test_upload_limit(self): self.assertEqual(25*1024*1024,MAX_UPLOAD_BYTES)
    def test_sidecar_used(self): self.assertEqual('SIDECAR_TEXT',self.rec['text_source'])
    def test_span(self): self.assertEqual(5.0,self.rec['resolved']['values']['span_m'])
    def test_section(self): self.assertEqual((300,500),(self.rec['resolved']['values']['width_mm'],self.rec['resolved']['values']['height_mm']))
    def test_materials(self): self.assertEqual(('C30/37','B500B'),(self.rec['resolved']['values']['concrete_class'],self.rec['resolved']['values']['reinforcement_class']))
    def test_cover(self): self.assertEqual(40,self.rec['resolved']['values']['nominal_cover_mm'])
    def test_q_load(self): self.assertEqual(12.0,self.rec['resolved']['distributed_loads'][0]['characteristic_kn_m'])
    def test_point_load(self): self.assertEqual(25.0,self.rec['resolved']['point_loads'][0]['characteristic_kn'])
    def test_point_position(self): self.assertEqual(2.0,self.rec['resolved']['point_loads'][0]['position_m'])
    def test_supports(self): self.assertEqual(('PIN','ROLLER'),(self.rec['resolved']['values']['support_a'],self.rec['resolved']['values']['support_b']))
    def test_input_ready(self): self.assertTrue(self.rec['input_ready'])
    def test_no_confirmation_blocks(self): self.assertFalse(self.engine.recognize(SAMPLE,'SUR',None,None)['input_ready'])
    def test_decimal_comma(self): self.assertEqual(4.5,self.engine.parse_text('L=4,5 m; q=10,5 kN/m')['fields']['span_m']['value'])
    def test_point_without_position_warns(self): self.assertTrue(self.engine.parse_text('P1=20 kN')['warnings'])
    def test_bad_extension(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.exe'; p.write_text('x')
            with self.assertRaises(ValueError): self.engine.validate_upload(p)
    def test_config_jurisdiction(self): self.assertEqual('SUR',self.cfg['regional_profile']['jurisdiction_code'])
    def test_config_span(self): self.assertEqual(5.0,self.cfg['beam']['span_m'])
    def test_config_q(self): self.assertEqual(12.0,self.cfg['loads']['variable_udl_kn_m'])
    def test_config_point(self): self.assertEqual(25.0,self.cfg['loads']['point_loads'][0]['characteristic_kn'])
    def test_design_passes(self): self.assertEqual(self.design['metrics']['technical_check_count'],self.design['metrics']['technical_checks_passed'])
    def test_final_release_blocked(self): self.assertFalse(self.rec['final_structural_release_allowed'])
    def test_preview_svg(self): self.assertIn('L = 5.000 m',render_preview_svg(self.rec))
    def test_engineer_basis_valid(self): self.assertEqual([],REG.validate_confirmation('SUR',ENG))
    def test_engineer_basis_missing_rejected(self): self.assertTrue(REG.validate_confirmation('SUR',{'jurisdiction_code':'SUR'}))
    def test_profile_requires_confirmation(self): self.assertEqual('PROJECT_SPECIFIC_ENGINEER_CONFIRMATION_REQUIRED',self.profile['structural_standard_status'])
    def test_profile_release_blocked(self): self.assertIn('BLOCKED',self.profile['final_release_policy'])
    def test_sample_hash_present(self): self.assertEqual(64,len(self.rec['sketch']['sha256']))
if __name__=='__main__': unittest.main()
