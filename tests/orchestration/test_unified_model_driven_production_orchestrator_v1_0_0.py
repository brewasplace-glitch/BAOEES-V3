from __future__ import annotations
import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from phoenix.orchestration.unified_model_driven_production import UnifiedProductionOrchestrator, canonical_bytes
ROOT=Path(__file__).resolve().parents[2]
CONFIG=json.loads((ROOT/'configs/projects/moskee_bunschoten_unified_production_orchestrator_v1_0_0.json').read_text(encoding='utf-8'))
class OrchestratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=UnifiedProductionOrchestrator(ROOT,CONFIG)
        cls.tmp=tempfile.TemporaryDirectory()
        cls.out=Path(cls.tmp.name)/'out'
        cls.out2=Path(cls.tmp.name)/'out2'
        cls.result=cls.engine.execute(cls.out,execute_changed=False,ignore_previous=True)
        cls.result2=cls.engine.execute(cls.out2,execute_changed=False,ignore_previous=True)
        cls.release=cls.result['release']
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_version(self):self.assertEqual('1.0.0',self.engine.VERSION)
    def test_three_components(self):self.assertEqual(3,len(CONFIG['components']))
    def test_dependency_graph(self):self.assertEqual(['central_model'],CONFIG['components']['drawings_reports']['depends_on'])
    def test_source_state(self):fps,rows=self.engine.current_source_state();self.assertEqual({'central_model','drawings_reports','calculations'},set(fps));self.assertGreater(len(rows),10)
    def test_source_fingerprints_sha256(self):fps,_=self.engine.current_source_state();self.assertTrue(all(len(x)==64 for x in fps.values()))
    def test_initial_changes_all_direct(self):fps,_=self.engine.current_source_state();self.assertTrue(all(x['direct_change'] for x in self.engine.detect_changes(fps,None)))
    def test_initial_plan_all_regenerate(self):fps,_=self.engine.current_source_state();self.assertTrue(all(x['action']=='REGENERATE' for x in self.engine.regeneration_plan(self.engine.detect_changes(fps,None))))
    def test_no_change_plan_reuses_all(self):fps,_=self.engine.current_source_state();prev={'source_fingerprints':fps};self.assertTrue(all(x['action']=='REUSE_AND_REVALIDATE' for x in self.engine.regeneration_plan(self.engine.detect_changes(fps,prev))))
    def test_model_change_cascades(self):fps,_=self.engine.current_source_state();prev={'source_fingerprints':dict(fps)};prev['source_fingerprints']['central_model']='0'*64;self.assertTrue(all(x['action']=='REGENERATE' for x in self.engine.regeneration_plan(self.engine.detect_changes(fps,prev))))
    def test_production_change_is_selective(self):fps,_=self.engine.current_source_state();prev={'source_fingerprints':dict(fps)};prev['source_fingerprints']['drawings_reports']='0'*64;plan={x['component_id']:x['action'] for x in self.engine.regeneration_plan(self.engine.detect_changes(fps,prev))};self.assertEqual(('REUSE_AND_REVALIDATE','REGENERATE','REUSE_AND_REVALIDATE'),(plan['central_model'],plan['drawings_reports'],plan['calculations']))
    def test_calculation_change_is_selective(self):fps,_=self.engine.current_source_state();prev={'source_fingerprints':dict(fps)};prev['source_fingerprints']['calculations']='0'*64;plan={x['component_id']:x['action'] for x in self.engine.regeneration_plan(self.engine.detect_changes(fps,prev))};self.assertEqual(('REUSE_AND_REVALIDATE','REUSE_AND_REVALIDATE','REGENERATE'),(plan['central_model'],plan['drawings_reports'],plan['calculations']))
    def test_initial_revision_c01(self):fps,_=self.engine.current_source_state();plan=self.engine.regeneration_plan(self.engine.detect_changes(fps,None));self.assertEqual('C01',self.engine.revision(None,plan)['revision_code'])
    def test_no_change_keeps_revision(self):fps,_=self.engine.current_source_state();prev={'revision_number':3,'revision_code':'C03','source_fingerprints':fps};plan=self.engine.regeneration_plan(self.engine.detect_changes(fps,prev));rev=self.engine.revision(prev,plan);self.assertEqual(('C03','REVALIDATION'),(rev['revision_code'],rev['run_mode']))
    def test_change_increments_revision(self):fps,_=self.engine.current_source_state();old=dict(fps);old['calculations']='0'*64;prev={'revision_number':3,'revision_code':'C03','source_fingerprints':old};plan=self.engine.regeneration_plan(self.engine.detect_changes(fps,prev));self.assertEqual('C04',self.engine.revision(prev,plan)['revision_code'])
    def test_force_all(self):fps,_=self.engine.current_source_state();self.assertTrue(all(x['direct_change'] for x in self.engine.detect_changes(fps,{'source_fingerprints':fps},force_all=True)))
    def test_canonical_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.txt';p.write_bytes(b'a\r\nb\r\n');self.assertEqual(b'a\nb\n',canonical_bytes(p))
    def test_missing_source_fails(self):
        bad=copy.deepcopy(CONFIG);bad['components']['central_model']['source_paths']=['missing.txt']
        with self.assertRaises(FileNotFoundError):UnifiedProductionOrchestrator(ROOT,bad).current_source_state()
    def test_release_status(self):self.assertEqual('UNIFIED_MODEL_DRIVEN_CONCEPT_ISSUE_READY',self.release['status'])
    def test_cross_checks(self):self.assertEqual((22,22,True),(self.release['cross_check_count'],self.release['cross_checks_passed'],self.release['all_cross_checks_passed']))
    def test_output_file_count(self):self.assertEqual(16,sum(1 for p in self.out.rglob('*') if p.is_file()))
    def test_issue_zip_exists(self):self.assertTrue(self.result['paths']['issue_package'].is_file())
    def test_release_blocked_for_permit(self):self.assertFalse(self.release['gates']['final_permit_ready_generation_allowed'])
    def test_bb36_locked(self):self.assertFalse(self.release['gates']['bb36_production_release_allowed'])
    def test_professional_blockers_six(self):self.assertEqual(6,self.release['professional_blocker_count'])
    def test_model_fingerprint_propagated(self):self.assertEqual(64,len(self.release['model_fingerprint_sha256']))
    def test_complete_issue_has_many_members(self):
        with zipfile.ZipFile(self.result['paths']['issue_package']) as z:self.assertGreater(len(z.namelist()),80)
    def test_deterministic_exports(self):
        names=sorted(x.relative_to(self.out).as_posix() for x in self.out.rglob('*') if x.is_file());self.assertEqual(names,sorted(x.relative_to(self.out2).as_posix() for x in self.out2.rglob('*') if x.is_file()));self.assertTrue(all((self.out/n).read_bytes()==(self.out2/n).read_bytes() for n in names))
    def test_dashboard_generated(self):self.assertTrue(self.result['paths']['dashboard'].is_file())
    def test_revision_state_generated(self):self.assertTrue(self.result['paths']['revision_state'].is_file())
    def test_change_register_generated(self):self.assertTrue(self.result['paths']['changes'].is_file())
    def test_all_products_current(self):self.assertTrue(self.release['gates']['all_products_current'])
if __name__=='__main__':unittest.main()
