"""Digital Twin Synchronization Engine for Project Phoenix — Wave 15.7."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4
ENGINE_ID="phoenix.digital_twin_synchronization.wave15_7"; ENGINE_VERSION="1.0.0"; SCHEMA_VERSION="1.0"
class SyncError(RuntimeError): pass
@dataclass(frozen=True)
class SyncChange:
    object_id:str; source:str; operation:str; payload:Mapping[str,Any]=field(default_factory=dict); base_version:int|None=None; reason:str=""
    def validate(self):
        if not self.object_id.strip(): raise SyncError("object_id must not be empty.")
        if not self.source.strip(): raise SyncError("source must not be empty.")
        if self.operation not in {"upsert","delete"}: raise SyncError(f"Unsupported operation: {self.operation}")
        if self.base_version is not None and self.base_version<0: raise SyncError("base_version must be zero or positive.")
@dataclass(frozen=True)
class SyncConflict:
    object_id:str; source:str; conflict_type:str; expected_version:int|None; actual_version:int|None; resolution:str
@dataclass
class DigitalTwinState:
    project_id:str; revision:int=0; objects:dict[str,dict[str,Any]]=field(default_factory=dict); history:list[dict[str,Any]]=field(default_factory=list)
    def validate(self):
        if not self.project_id.strip(): raise SyncError("project_id must not be empty.")
        if self.revision<0: raise SyncError("revision must be zero or positive.")
class DigitalTwinSynchronizationEngine:
    MODES={"strict","merge","review"}
    @staticmethod
    def _canonical_json(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False,default=str)
    @classmethod
    def _digest(cls,value): return sha256(cls._canonical_json(value).encode('utf-8')).hexdigest()
    @staticmethod
    def _merge_payload(current,incoming):
        merged=deepcopy(dict(current))
        for k,v in incoming.items():
            if k in merged and isinstance(merged[k],Mapping) and isinstance(v,Mapping): merged[k]=DigitalTwinSynchronizationEngine._merge_payload(merged[k],v)
            else: merged[k]=deepcopy(v)
        return merged
    def synchronize(self,*,state,changes,mode='review',actor='phoenix'):
        state.validate()
        if mode not in self.MODES: raise SyncError(f"Unsupported synchronization mode: {mode}")
        if not actor.strip(): raise SyncError("actor must not be empty.")
        working=deepcopy(state); applied=[]; conflicts=[]
        for sequence,change in enumerate(changes,start=1):
            change.validate(); current=working.objects.get(change.object_id); actual=int(current.get('_version',0)) if current else 0; expected=change.base_version; conflict=expected is not None and expected!=actual
            if conflict:
                resolution={"strict":"blocked","merge":"merged","review":"pending_review"}[mode]
                conflicts.append(SyncConflict(change.object_id,change.source,'version_mismatch',expected,actual,resolution))
                if mode=='strict': raise SyncError(f"Version conflict for {change.object_id}: expected {expected}, actual {actual}.")
                if mode=='review': continue
            before=deepcopy(current) if current else None
            if change.operation=='delete':
                if current is None:
                    applied.append({'sequence':sequence,'object_id':change.object_id,'source':change.source,'operation':'delete','status':'noop','reason':'object_missing'}); continue
                del working.objects[change.object_id]; after=None; next_version=actual+1
            else:
                current_payload={k:v for k,v in (current or {}).items() if not k.startswith('_')}
                next_payload=self._merge_payload(current_payload,change.payload) if conflict and mode=='merge' else deepcopy(dict(change.payload))
                next_version=actual+1; next_payload['_version']=next_version; next_payload['_source']=change.source
                next_payload['_sha256']=self._digest({'object_id':change.object_id,'version':next_version,'payload':{k:v for k,v in next_payload.items() if k!='_sha256'}})
                working.objects[change.object_id]=next_payload; after=deepcopy(next_payload)
            event={'event_id':str(uuid4()),'sequence':sequence,'object_id':change.object_id,'source':change.source,'actor':actor,'operation':change.operation,'reason':change.reason,'base_version':expected,'previous_version':actual,'new_version':next_version,'before_sha256':self._digest(before),'after_sha256':self._digest(after)}
            working.history.append(event); applied.append({'sequence':sequence,'object_id':change.object_id,'source':change.source,'operation':change.operation,'status':'applied','new_version':next_version,'event_id':event['event_id']})
        working.revision+=1
        result={'schema_version':SCHEMA_VERSION,'engine':{'id':ENGINE_ID,'version':ENGINE_VERSION},'project_id':working.project_id,'mode':mode,'status':'review_required' if conflicts and mode=='review' else 'synchronized','revision':working.revision,'applied_changes':applied,'conflicts':[asdict(x) for x in conflicts],'digital_twin':{'project_id':working.project_id,'revision':working.revision,'objects':working.objects,'history':working.history},'integration_contract':{'upstream_engine':'phoenix.autonomous_design_orchestrator.wave15_6','downstream_engine':'phoenix.permit_compliance.wave15_8'},'limitations':['The engine synchronizes structured data only.','External BIM/CAD/database connectors require separate adapters.','Review mode does not apply conflicting changes automatically.','No technical or regulatory certification is claimed.']}
        result['evidence']={'algorithm':'sha256','digital_twin_sha256':self._digest(result['digital_twin']),'result_sha256':self._digest(result)}
        return result
    def write_result(self,*,state,changes,mode,actor,destination):
        result=self.synchronize(state=state,changes=changes,mode=mode,actor=actor); path=Path(destination); path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(path.suffix+'.tmp'); temp.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n'); temp.replace(path); return path
