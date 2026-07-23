import json,tempfile,unittest
from pathlib import Path
from phoenix.adapters.digital_twin_synchronization_adapter import run_digital_twin_synchronization
from phoenix.digital_twin_sync import DigitalTwinState,DigitalTwinSynchronizationEngine,SyncChange,SyncError
class Wave157Tests(unittest.TestCase):
 def setUp(self): self.engine=DigitalTwinSynchronizationEngine()
 def test_upsert_new_object(self):
  r=self.engine.synchronize(state=DigitalTwinState('PHX'),changes=(SyncChange('wall-1','bim','upsert',{'height':3.0},0),)); self.assertEqual(r['digital_twin']['objects']['wall-1']['_version'],1)
 def test_update_existing_object(self):
  s=DigitalTwinState('PHX',objects={'wall-1':{'height':3.0,'_version':1}}); r=self.engine.synchronize(state=s,changes=(SyncChange('wall-1','structural','upsert',{'height':3.2},1),)); self.assertEqual(r['digital_twin']['objects']['wall-1']['_version'],2)
 def test_strict_conflict_blocks(self):
  with self.assertRaisesRegex(SyncError,'Version conflict'): self.engine.synchronize(state=DigitalTwinState('PHX',objects={'x':{'a':1,'_version':2}}),changes=(SyncChange('x','cost','upsert',{'b':2},1),),mode='strict')
 def test_review_conflict_not_applied(self):
  r=self.engine.synchronize(state=DigitalTwinState('PHX',objects={'x':{'a':1,'_version':2}}),changes=(SyncChange('x','cost','upsert',{'b':2},1),),mode='review'); self.assertEqual(r['status'],'review_required'); self.assertNotIn('b',r['digital_twin']['objects']['x'])
 def test_merge_conflict(self):
  s=DigitalTwinState('PHX',objects={'x':{'geometry':{'width':2,'height':3},'_version':2}}); r=self.engine.synchronize(state=s,changes=(SyncChange('x','bim','upsert',{'geometry':{'height':4}},1),),mode='merge'); self.assertEqual(r['digital_twin']['objects']['x']['geometry'],{'width':2,'height':4})
 def test_delete_object(self):
  r=self.engine.synchronize(state=DigitalTwinState('PHX',objects={'x':{'a':1,'_version':1}}),changes=(SyncChange('x','user','delete',base_version=1),)); self.assertNotIn('x',r['digital_twin']['objects'])
 def test_history_and_evidence(self):
  r=self.engine.synchronize(state=DigitalTwinState('PHX'),changes=(SyncChange('x','bim','upsert',{'a':1},0),)); self.assertEqual(len(r['digital_twin']['history']),1); self.assertEqual(len(r['evidence']['result_sha256']),64)
 def test_adapter_writes_output(self):
  req={'state':{'project_id':'PHX'},'changes':[{'object_id':'x','source':'bim','operation':'upsert','payload':{'a':1},'base_version':0}]}
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)/'result.json'; r=run_digital_twin_synchronization(req,p); stored=json.loads(p.read_text(encoding='utf-8'))
  self.assertEqual(r['revision'],1); self.assertEqual(stored['adapter']['version'],'1.0.0')
 def test_write_result_atomic(self):
  with tempfile.TemporaryDirectory() as f:
   p=Path(f)/'result.json'; self.engine.write_result(state=DigitalTwinState('PHX'),changes=(SyncChange('x','bim','upsert',{'a':1},0),),mode='review',actor='phoenix',destination=p); self.assertTrue(p.exists()); self.assertFalse(p.with_suffix('.json.tmp').exists())
if __name__=='__main__': unittest.main()
