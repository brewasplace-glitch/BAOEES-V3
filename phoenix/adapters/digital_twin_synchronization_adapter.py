"""Adapter for Phoenix Digital Twin Synchronization Engine Wave 15.7."""
import json
from pathlib import Path
from phoenix.digital_twin_sync import DigitalTwinState, DigitalTwinSynchronizationEngine, SyncChange
ADAPTER_ID='phoenix.adapter.digital_twin_synchronization.wave15_7'; ADAPTER_VERSION='1.0.0'
def run_digital_twin_synchronization(request,output_path=None):
    s=dict(request['state']); state=DigitalTwinState(str(s['project_id']),int(s.get('revision',0)),dict(s.get('objects',{})),list(s.get('history',[])))
    changes=tuple(SyncChange(str(i['object_id']),str(i['source']),str(i['operation']),dict(i.get('payload',{})),None if i.get('base_version') is None else int(i['base_version']),str(i.get('reason',''))) for i in request.get('changes',[]))
    result=DigitalTwinSynchronizationEngine().synchronize(state=state,changes=changes,mode=str(request.get('mode','review')),actor=str(request.get('actor','phoenix'))); result['adapter']={'id':ADAPTER_ID,'version':ADAPTER_VERSION}
    if output_path is not None:
        p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    return result
