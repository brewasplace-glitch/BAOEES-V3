"""Fail-fast validation and Git automation."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json, subprocess
from pathlib import Path
from typing import Callable, Iterable
Runner=Callable[...,subprocess.CompletedProcess[str]]
class AutomationError(RuntimeError): pass
@dataclass(frozen=True)
class AutomationStep:
    name:str; command:tuple[str,...]; return_code:int; stdout:str; stderr:str; status:str
@dataclass(frozen=True)
class AutomationReport:
    status:str; commit_created:bool; push_performed:bool; commit_hash:str; steps:tuple[AutomationStep,...]; evidence_sha256:str
    def to_dict(self):
        return {"status":self.status,"commit_created":self.commit_created,"push_performed":self.push_performed,"commit_hash":self.commit_hash,"steps":[x.__dict__ for x in self.steps],"evidence_sha256":self.evidence_sha256}
class PhoenixAutomationEngine:
    def __init__(self,repo_root:str|Path,*,runner:Runner=subprocess.run): self.repo_root=Path(repo_root).resolve(); self._runner=runner
    def _run(self,name,command,timeout=900):
        cmd=tuple(command)
        try: c=self._runner(list(cmd),cwd=self.repo_root,capture_output=True,text=True,timeout=timeout,shell=False,check=False); rc=c.returncode; out=c.stdout; err=c.stderr
        except subprocess.TimeoutExpired as e: rc=124; out=e.stdout or ''; err=e.stderr or ''
        return AutomationStep(name,cmd,rc,out,err,'passed' if rc==0 else ('timed_out' if rc==124 else 'failed'))
    @staticmethod
    def _digest(data): return sha256(json.dumps(data,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
    def _report(self,status,cc,pp,ch,steps):
        data={"status":status,"commit_created":cc,"push_performed":pp,"commit_hash":ch,"steps":[x.__dict__ for x in steps]}
        return AutomationReport(status,cc,pp,ch,tuple(steps),self._digest(data))
    def run(self,*,commit_message:str,intended_paths:Iterable[str],validation_commands:Iterable[tuple[str,Iterable[str]]],push=True,remote='origin'):
        if not commit_message.strip(): raise AutomationError('commit_message must not be empty.')
        paths=tuple(dict.fromkeys(map(str,intended_paths)))
        if not paths: raise AutomationError('intended_paths must not be empty.')
        steps=[]
        for name,cmd in [("repository preflight",("git","rev-parse","--is-inside-work-tree")),*list(validation_commands),("git diff check",("git","diff","--check"))]:
            s=self._run(name,cmd); steps.append(s)
            if s.return_code!=0: return self._report('failed',False,False,'',steps)
        s=self._run('git stage intended paths',('git','add','--',*paths)); steps.append(s)
        if s.return_code!=0:return self._report('failed',False,False,'',steps)
        staged=self._run('verify staged changes',('git','diff','--cached','--quiet')); steps.append(staged)
        if staged.return_code==0:
            final=self._run('final git status',('git','status','--porcelain')); steps.append(final)
            return self._report('completed' if final.return_code==0 and not final.stdout.strip() else 'failed',False,False,'',steps)
        if staged.return_code!=1:return self._report('failed',False,False,'',steps)
        commit=self._run('git commit',('git','commit','-m',commit_message),120); steps.append(commit)
        if commit.return_code!=0:return self._report('failed',False,False,'',steps)
        head=self._run('git head',('git','rev-parse','HEAD'),30); steps.append(head); ch=head.stdout.strip()
        pushed=False
        if push:
            branch=self._run('resolve branch',('git','rev-parse','--abbrev-ref','HEAD'),30); steps.append(branch)
            if branch.return_code!=0:return self._report('failed',True,False,ch,steps)
            ps=self._run('git push',('git','push',remote,branch.stdout.strip()),300); steps.append(ps)
            if ps.return_code!=0:return self._report('failed',True,False,ch,steps)
            pushed=True
        final=self._run('final git status',('git','status','--porcelain'),30); steps.append(final)
        return self._report('completed' if final.return_code==0 and not final.stdout.strip() else 'failed',True,pushed,ch,steps)
