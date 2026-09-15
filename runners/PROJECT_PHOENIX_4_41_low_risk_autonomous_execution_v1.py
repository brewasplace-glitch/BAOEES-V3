from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path(r'C:\PROJECT-PHOENIX')); ap.add_argument('--request',type=Path,required=True); ap.add_argument('--expected-head',default=None); ap.add_argument('--keep-candidate',action='store_true'); ap.add_argument('--publish-candidate',action='store_true'); ap.add_argument('--allowed-main-dirty-path',action='append',default=[]); a=ap.parse_args()
    repo=a.repo_root.resolve(); sys.path.insert(0,str(repo))
    from phoenix.autonomy import AutonomyPolicy, LearningStore, Task, LowRiskExecutor, LowRiskExecutionPolicy, TextMutation
    from phoenix.autonomy.request_io import load_json_request
    req=load_json_request(a.request)
    task=Task(str(req.get('task_id','LOW-RISK-REQUEST')),str(req['title']),str(req.get('capability_id','AUTO-LOWRISK-002')),str(req.get('action','update')),tuple(str(x['path']) for x in req['mutations']))
    muts=tuple(TextMutation(str(x['path']),str(x['content']),str(x.get('operation','replace'))) for x in req['mutations'])
    central=AutonomyPolicy.from_json(repo/'configs/phoenix/autonomy_policy_v1.json'); ep=LowRiskExecutionPolicy.from_json(repo/'configs/phoenix/low_risk_execution_policy_v1.json')
    local=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share'))); runtime=local/'PROJECT-PHOENIX'/'autonomy'/'low_risk_execution'
    ex=LowRiskExecutor(repo,central,ep,LearningStore(runtime/'learning_events_v1.jsonl'),runtime_root=runtime)
    result=ex.execute(task,muts,expected_head=a.expected_head,allowed_main_dirty_paths=tuple(a.allowed_main_dirty_path),keep_candidate=a.keep_candidate,publish_candidate=a.publish_candidate)
    print(json.dumps(result,indent=2,ensure_ascii=True)); return 0
if __name__=='__main__': raise SystemExit(main())
