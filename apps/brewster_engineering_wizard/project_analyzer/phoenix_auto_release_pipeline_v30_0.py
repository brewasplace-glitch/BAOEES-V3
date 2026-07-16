from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from datetime import datetime
from pathlib import Path

NAME='Phoenix Auto Release Pipeline'; VER='v30.0'

def root():
    p=Path.cwd().resolve()
    for x in [p,*p.parents]:
        if (x/'.git').exists(): return x
    raise RuntimeError('PROJECT-PHOENIX root niet gevonden.')

ROOT=root(); CFG=ROOT/'configs/phoenix'; OUT=ROOT/'outputs/runtime/v30_0'; REL=ROOT/'outputs/releases/v30_0'

class Pipeline:
    def __init__(self):
        self.policy=self.read(CFG/'auto_release_pipeline_policy_v30_0.json')
        self.registry=self.read(CFG/'auto_release_pipeline_registry_v30_0.json')
    def self_test(self):
        c={'policy':bool(self.policy),'registry':bool(self.registry),'python':sys.version_info>=(3,10),'git':self.run(['git','--version'])['returncode']==0}
        return self.save(OUT/'auto_release_self_test_v30_0.json',{'engine':NAME,'version':VER,'checks':c,'status':'PASS' if all(c.values()) else 'FAIL'})
    def validate(self):
        errors=[]; stages=self.registry.get('stages',[])
        required=set(self.policy['required_stages']); available={s['stage_id'] for s in stages}
        missing=sorted(required-available)
        if missing: errors.append(f'Ontbrekende stages: {missing}')
        orders=[s['order'] for s in stages]
        if len(orders)!=len(set(orders)): errors.append('Dubbele stagevolgorde.')
        return self.save(OUT/'auto_release_validation_v30_0.json',{'engine':NAME,'version':VER,'errors':errors,'status':'PASS' if not errors else 'FAIL'})
    def plan(self):
        v=self.validate()
        if v['status']!='PASS': return self.save(REL/'auto_release_plan_v30_0.json',{'engine':NAME,'version':VER,'status':'BLOCKED_INVALID_PIPELINE'})
        stages=sorted(self.registry['stages'],key=lambda x:x['order'])
        return self.save(REL/'auto_release_plan_v30_0.json',{'engine':NAME,'version':VER,'stages':[{'sequence':i,'stage_id':s['stage_id'],'description':s['description'],'blocking':s['blocking'],'status':'PLANNED'} for i,s in enumerate(stages,1)],'automatic_commit':True,'automatic_push':True,'final_gate':'WORKING_TREE_CLEAN','status':'PASS'})
    def audit(self):
        b=self.run(['git','branch','--show-current']); s=self.run(['git','status','--porcelain']); d=self.run(['git','diff','--check'])
        r={'engine':NAME,'version':VER,'branch':b['stdout'].strip(),'working_tree_clean':not s['stdout'].strip(),'diff_check_pass':d['returncode']==0,'status':'PASS' if b['returncode']==0 and s['returncode']==0 and d['returncode']==0 else 'FAIL'}
        r['fingerprint']=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
        return self.save(OUT/'auto_release_audit_v30_0.json',r)
    def summary(self):
        p=self.plan(); a=self.audit(); status='PASS' if p['status']=='PASS' and a['status']=='PASS' else 'FAIL'
        return self.save(REL/'auto_release_summary_v30_0.json',{'engine':NAME,'version':VER,'pipeline_status':p['status'],'audit_status':a['status'],'automatic_commit':True,'automatic_push':True,'requires_manual_git_steps':False,'status':status})
    def run(self,cmd):
        x=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=False)
        return {'returncode':x.returncode,'stdout':x.stdout,'stderr':x.stderr}
    def read(self,p): return json.loads(p.read_text(encoding='utf-8-sig'))
    def save(self,p,d):
        p.parent.mkdir(parents=True,exist_ok=True); d['generated_at']=datetime.now().isoformat(timespec='seconds')
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8-sig'); d['output_path']=str(p); return d

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('cmd',choices=['self-test','validate','plan','audit','summary']); a=ap.parse_args(); e=Pipeline()
    r={'self-test':e.self_test,'validate':e.validate,'plan':e.plan,'audit':e.audit,'summary':e.summary}[a.cmd]()
    print(json.dumps(r,ensure_ascii=True,indent=2))
    if r.get('status') in {'FAIL','BLOCKED_INVALID_PIPELINE'}: raise SystemExit(1)
if __name__=='__main__': main()
