"""Phoenix AF-R2: fail-closed integration preflight and evidence, no mutating execution."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone

EXPECTED_BRANCH = 'project-phoenix'
MODULES = {
 'build_runner':'phoenix/autonomy/autonomous_build_orchestrator_v1_0.py',
 'execution_orchestrator':'phoenix/autonomy/execution_orchestrator.py',
 'repair_fsm':'phoenix/autonomy/repair_fsm.py',
 'worktree_guard':'phoenix/autonomy/worktree_guard.py',
 'isolated_runtime':'phoenix/autonomy/isolated_runtime.py',
 'geometry_consistency':'phoenix/design/tropical_residential/canonical_geometry_consistency.py',
 'topology_quality':'phoenix/design/tropical_residential/aec_topology_quality.py',
 'sketchup_adapter':'phoenix/building_model/adapters/sketchup.py',
 'startscreen_sync':'phoenix/startscreen_runtime_sync/sync.py',
 'local_project_runtime':'phoenix/local_app/architectural_orchestration_runtime.py',
}

def run_git(repo, *args):
 p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=30)
 if p.returncode: raise RuntimeError('git '+ ' '.join(args)+' failed: '+p.stderr.strip())
 return p.stdout.strip()

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()

def assess(repo:Path, expected_head:str):
 repo=repo.resolve()
 if not re.fullmatch(r'[0-9a-f]{40}', expected_head):raise ValueError('expected_head must be full Git SHA')
 branch=run_git(repo,'branch','--show-current')
 head=run_git(repo,'rev-parse','HEAD')
 upstream=run_git(repo,'rev-parse','@{upstream}')
 dirty=run_git(repo,'status','--porcelain','--untracked-files=normal')
 violations=[]
 if branch!=EXPECTED_BRANCH: violations.append('WRONG_BRANCH')
 if head!=expected_head: violations.append('BASELINE_DRIFT')
 if upstream!=head: violations.append('UPSTREAM_MISMATCH')
 if dirty: violations.append('DIRTY_WORKTREE')
 modules={}
 for name,rel in MODULES.items():
  p=repo/rel
  found=p.is_file()
  modules[name]={'relative_path':rel,'present':found,'sha256':digest(p) if found else None}
  if not found:violations.append('MISSING_'+name.upper())
 engines={
  'git':bool(shutil.which('git')),
  'python':bool(shutil.which('python') or shutil.which('py')),
  'sketchup_2020':bool((Path(os.environ.get('ProgramFiles','C:/Program Files'))/'SketchUp'/'SketchUp 2020'/'SketchUp.exe').exists()) if os.name=='nt' else False,
  'oda_converter':bool((Path(os.environ.get('ProgramFiles','C:/Program Files'))/'ODA'/'ODAFileConverter 27.9.0'/'ODAFileConverter.exe').exists()) if os.name=='nt' else False,
  'libredwg_dwgread':bool(Path('C:/PHOENIX_TOOLS/LibreDWG/dwgread.exe').exists()) if os.name=='nt' else False,
 }
 return {'schema':'phoenix.af-r2.preflight.v1','utc':datetime.now(timezone.utc).isoformat(),
 'repo':str(repo),'branch':branch,'head':head,'upstream':upstream,'dirty':bool(dirty),
 'modules':modules,'engines':engines,'geometry_qa':{'status':'NOT_YET_IMPLEMENTED','native_dwg_reference':False,'metric_coverage':None},
 'execution_policy':{'mode':'READ_ONLY','automatic_commit':False,'automatic_push':False,'automatic_repair':False,'professional_release':'LOCKED'},
 'status':'PASS' if not violations else 'BLOCKED','violations':violations}

def main(argv=None):
 p=argparse.ArgumentParser()
 p.add_argument('--repo',required=True)
 p.add_argument('--expected-head',required=True)
 p.add_argument('--output',required=True)
 ns=p.parse_args(argv)
 report=assess(Path(ns.repo),ns.expected_head)
 out=Path(ns.output)
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('PHOENIX_AF_R2_STATUS='+report['status'])
 print('REPORT='+str(out))
 return 0 if report['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
