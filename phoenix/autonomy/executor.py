from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import json, os, re, shutil, subprocess, tempfile, time, uuid
from .models import Task, RiskLevel, LearningEvent
from .policy import AutonomyPolicy, RiskClassifier
from .worktree import SafeWorktreeManager
from .learning import LearningStore

@dataclass(frozen=True)
class TextMutation:
    path:str
    content:str
    operation:str='replace'

@dataclass(frozen=True)
class LowRiskExecutionPolicy:
    enabled:bool; execution_mode:str; mainline_promotion:str
    allowed_roots:tuple[str,...]; allowed_extensions:tuple[str,...]
    max_files:int; max_file_bytes:int; max_total_bytes:int
    forbidden_path_segments:tuple[str,...]; forbidden_content_patterns:tuple[str,...]
    @classmethod
    def from_json(cls,path:Path):
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(bool(d['enabled']),str(d['execution_mode']),str(d['mainline_promotion']),tuple(d['allowed_roots']),tuple(d['allowed_extensions']),int(d['max_files']),int(d['max_file_bytes']),int(d['max_total_bytes']),tuple(d['forbidden_path_segments']),tuple(d['forbidden_content_patterns']))

def norm(path:str)->str: return path.replace('\\','/').lstrip('./')
def status_paths(lines:Iterable[str])->tuple[str,...]:
    out=[]
    for line in lines:
        if not line or len(line)<4: continue
        raw=line[3:].strip().replace('\\','/')
        if ' -> ' in raw: raw=raw.split(' -> ',1)[1].strip()
        out.append(raw.lstrip('./'))
    return tuple(out)

class LowRiskExecutor:
    def __init__(self,repo_root:Path,autonomy_policy:AutonomyPolicy,execution_policy:LowRiskExecutionPolicy,learning:LearningStore,branch='project-phoenix',runtime_root:Path|None=None):
        self.repo_root=Path(repo_root).resolve(); self.autonomy_policy=autonomy_policy; self.execution_policy=execution_policy; self.learning=learning; self.branch=branch
        self.classifier=RiskClassifier(autonomy_policy); self.worktree=SafeWorktreeManager(self.repo_root,branch)
        local=Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))
        if runtime_root is None:
            runtime_root=local/'PROJECT-PHOENIX'/'autonomy'/'low_risk_execution'
        self.runtime_root=Path(runtime_root)
        override=os.environ.get('PHOENIX_AUTONOMY_WORKTREE_ROOT')
        self.worktree_root=Path(override) if override else local/'PXW'
    def git(self,cwd:Path,*args:str,check=True)->str:
        cp=subprocess.run(['git','-c','core.longpaths=true','-C',str(cwd),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if check and cp.returncode: raise RuntimeError(f"git {' '.join(args)} failed: {cp.stdout.rstrip()}")
        return cp.stdout.rstrip('\r\n')
    def validate_main(self,expected_head,allowed_main_dirty_paths):
        snap=self.worktree.snapshot(fetch=False)
        if snap.branch!=self.branch: raise RuntimeError(f'branch={snap.branch}, expected={self.branch}')
        if expected_head and snap.head!=expected_head: raise RuntimeError(f'head={snap.head}, expected={expected_head}')
        if snap.origin_head and snap.origin_head!=snap.head: raise RuntimeError('main branch is not synced with origin')
        actual=status_paths(snap.status); allowed={norm(p).lower() for p in allowed_main_dirty_paths}
        if actual:
            if not allowed: raise RuntimeError('main worktree dirty')
            unexpected=[p for p in actual if p.lower() not in allowed]
            if unexpected: raise RuntimeError('unexpected main dirty paths: '+', '.join(unexpected))
        return snap,actual
    def validate_mutations(self,mutations):
        p=self.execution_policy
        if not p.enabled or p.execution_mode!='candidate_branch_only' or p.mainline_promotion!='LOCKED': raise RuntimeError('LOW-risk execution policy invalid')
        if not mutations or len(mutations)>p.max_files: raise RuntimeError('invalid mutation file count')
        total=0; seen=set(); out=[]; allowed_ext={x.lower() for x in p.allowed_extensions}; forbidden={x.lower() for x in p.forbidden_path_segments}
        for m in mutations:
            rel=norm(m.path); low=rel.lower()
            if not rel or rel.startswith('../') or '/../' in f'/{rel}/': raise RuntimeError(f'unsafe path: {m.path}')
            if low in seen: raise RuntimeError(f'duplicate path: {rel}')
            seen.add(low)
            if Path(rel).suffix.lower() not in allowed_ext: raise RuntimeError(f'extension not allowed: {rel}')
            if not any(low.startswith(norm(root).lower()) for root in p.allowed_roots): raise RuntimeError(f'root not allowed: {rel}')
            if {x.lower() for x in Path(rel).parts} & forbidden: raise RuntimeError(f'forbidden path segment: {rel}')
            data=m.content.encode('utf-8'); total+=len(data)
            if len(data)>p.max_file_bytes or total>p.max_total_bytes: raise RuntimeError('mutation payload too large')
            for pattern in p.forbidden_content_patterns:
                if re.search(pattern,m.content): raise RuntimeError(f'forbidden content pattern: {rel}')
            if m.operation!='replace': raise RuntimeError('only replace operation allowed')
            out.append(TextMutation(rel,m.content,m.operation))
        return tuple(out)
    def execute(self,task:Task,mutations:tuple[TextMutation,...],expected_head=None,allowed_main_dirty_paths=(),keep_candidate=True,publish_candidate=False):
        execution_id='LOW-'+uuid.uuid4().hex[:12].upper(); report_dir=self.runtime_root/execution_id; report_dir.mkdir(parents=True,exist_ok=True)
        snap,main_dirty=self.validate_main(expected_head,allowed_main_dirty_paths)
        risk,evidence=self.classifier.classify(task)
        if risk!=RiskLevel.LOW: raise RuntimeError(f'risk must be LOW, got {risk.value}')
        if not self.autonomy_policy.low_risk_auto_enabled: raise RuntimeError('central LOW-risk gate locked')
        mutations=self.validate_mutations(mutations); requested=tuple(m.path for m in mutations)
        branch_name=f'auto/lowrisk-{execution_id.lower()}'; worktree=self.worktree_root/execution_id; worktree.parent.mkdir(parents=True,exist_ok=True)
        if worktree.exists(): shutil.rmtree(worktree)
        created=False
        try:
            self.git(self.repo_root,'worktree','add','-b',branch_name,str(worktree),snap.head); created=True
            if self.git(worktree,'rev-parse','HEAD')!=snap.head: raise RuntimeError('candidate baseline mismatch')
            for m in mutations:
                dst=worktree/m.path; dst.parent.mkdir(parents=True,exist_ok=True)
                cur=worktree
                for part in Path(m.path).parts[:-1]:
                    cur=cur/part
                    if cur.exists() and cur.is_symlink(): raise RuntimeError(f'symlinked parent forbidden: {m.path}')
                dst.write_text(m.content,encoding='utf-8',newline='\n')
            actual=status_paths(self.git(worktree,'status','--porcelain=v1','--untracked-files=all').splitlines())
            if {x.lower() for x in actual}!={x.lower() for x in requested}: raise RuntimeError(f'candidate scope mismatch actual={actual} requested={requested}')
            self.git(worktree,'diff','--check','--',*requested)
            for m in mutations:
                fp=worktree/m.path
                if not fp.exists() or fp.is_symlink(): raise RuntimeError(f'invalid candidate file: {m.path}')
                if fp.suffix.lower()=='.json': json.loads(fp.read_text(encoding='utf-8'))
            self.git(worktree,'add','--',*requested); self.git(worktree,'diff','--cached','--check')
            staged=status_paths(self.git(worktree,'status','--porcelain=v1','--untracked-files=all').splitlines())
            if {x.lower() for x in staged}!={x.lower() for x in requested}: raise RuntimeError('staged scope mismatch')
            self.git(worktree,'commit','-m',f'chore(autonomy): low-risk candidate {execution_id}')
            candidate_commit=self.git(worktree,'rev-parse','HEAD')
            self.git(self.repo_root,'fetch','origin',self.branch); origin_now=self.git(self.repo_root,'rev-parse',f'origin/{self.branch}')
            if snap.origin_head and origin_now!=snap.origin_head: raise RuntimeError('REMOTE_RACE_GUARD: origin changed during execution')
            published=False
            if publish_candidate:
                self.git(worktree,'push','-u','origin',branch_name); published=True
            result={'schema':'PHOENIX_LOW_RISK_EXECUTION_REPORT_V1','status':'PASS','execution_id':execution_id,'mode':'candidate_branch_only','main_branch':self.branch,'main_head_before':snap.head,'main_origin_before':snap.origin_head,'main_dirty_allowed':list(main_dirty),'risk':risk.value,'risk_evidence':evidence,'requested_paths':list(requested),'candidate_branch':branch_name,'candidate_commit':candidate_commit,'candidate_published':published,'mainline_promoted':False,'mainline_promotion':'LOCKED','mutation_performed':True,'mutation_location':'isolated_worktree_only','worktree':str(worktree),'worktree_root':str(self.worktree_root),'git_core_longpaths':True,'keep_candidate':keep_candidate}
            (report_dir/'execution_report.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8',newline='\n')
            self.learning.append(LearningEvent.create(execution_id,'low_risk_candidate_execution',result)); return result
        finally:
            if created and not keep_candidate:
                self.git(self.repo_root,'worktree','remove','--force',str(worktree),check=False); self.git(self.repo_root,'branch','-D',branch_name,check=False)
                (report_dir/'cleanup_status.json').write_text(json.dumps({'execution_id':execution_id,'cleanup':'PASS','worktree_exists':worktree.exists()},indent=2),encoding='utf-8',newline='\n')
