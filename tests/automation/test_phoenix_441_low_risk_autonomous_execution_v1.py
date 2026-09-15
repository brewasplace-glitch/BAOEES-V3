import json, os, subprocess, tempfile, unittest
from pathlib import Path
from phoenix.autonomy import AutonomyPolicy, LearningStore, Task, LowRiskExecutor, LowRiskExecutionPolicy, TextMutation, load_json_request

def git(cwd,*args):
    cp=subprocess.run(['git','-C',str(cwd),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if cp.returncode: raise RuntimeError(cp.stderr or cp.stdout)
    return cp.stdout.rstrip('\r\n')

class TestLowRiskExecution(unittest.TestCase):

    def test_request_json_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"request.json"
            p.write_text('{"title":"BOM","mutations":[]}',encoding="utf-8-sig")
            self.assertEqual(load_json_request(p)["title"],"BOM")

    def test_request_json_accepts_utf8_without_bom(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"request.json"
            p.write_text('{"title":"NO-BOM","mutations":[]}',encoding="utf-8")
            self.assertEqual(load_json_request(p)["title"],"NO-BOM")

    def repo(self,td):
        repo=Path(td)/'repo'; remote=Path(td)/'remote.git'; subprocess.run(['git','init','--bare',str(remote)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE); subprocess.run(['git','init',str(repo)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE); git(repo,'config','user.email','x@example.invalid'); git(repo,'config','user.name','Phoenix Test'); (repo/'README.md').write_text('baseline\n',encoding='utf-8'); git(repo,'add','README.md'); git(repo,'commit','-m','baseline'); git(repo,'branch','-M','project-phoenix'); git(repo,'remote','add','origin',str(remote)); git(repo,'push','-u','origin','project-phoenix'); return repo
    def policy(self,repo):
        p=repo.parent/'policy.json'; p.write_text(json.dumps({'enabled':True,'execution_mode':'candidate_branch_only','mainline_promotion':'LOCKED','allowed_roots':['docs/automation/autonomous_generated/'],'allowed_extensions':['.md','.txt','.json'],'max_files':5,'max_file_bytes':65536,'max_total_bytes':262144,'forbidden_path_segments':['.git','bib','phoenix','runners','configs','tests'],'forbidden_content_patterns':['(?i)password\\s*[:=]']}),encoding='utf-8'); return LowRiskExecutionPolicy.from_json(p)
    def executor(self,repo,td): return LowRiskExecutor(repo,AutonomyPolicy(low_risk_auto_enabled=True),self.policy(repo),LearningStore(Path(td)/'learn.jsonl'),runtime_root=Path(td)/'runtime')
    def test_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo(td); ex=self.executor(repo,td)
            with self.assertRaises(RuntimeError): ex.validate_mutations((TextMutation('phoenix/core.py','x'),))
    def test_secret_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo(td); ex=self.executor(repo,td)
            with self.assertRaises(RuntimeError): ex.validate_mutations((TextMutation('docs/automation/autonomous_generated/x.md','password = no'),))
    def test_short_default_worktree_root(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo(td)
            old_local=os.environ.get('LOCALAPPDATA')
            old_override=os.environ.pop('PHOENIX_AUTONOMY_WORKTREE_ROOT',None)
            try:
                os.environ['LOCALAPPDATA']=str(Path(td)/'Local')
                ex=LowRiskExecutor(repo,AutonomyPolicy(low_risk_auto_enabled=True),self.policy(repo),LearningStore(Path(td)/'learn2.jsonl'))
                self.assertEqual(ex.worktree_root,Path(td)/'Local'/'PXW')
            finally:
                if old_local is None: os.environ.pop('LOCALAPPDATA',None)
                else: os.environ['LOCALAPPDATA']=old_local
                if old_override is not None: os.environ['PHOENIX_AUTONOMY_WORKTREE_ROOT']=old_override
    def test_real_candidate_and_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo(td); head=git(repo,'rev-parse','HEAD'); ex=self.executor(repo,td); task=Task('T','Generate autonomy evidence','AUTO-LOWRISK-002','update',('docs/automation/autonomous_generated/probe.md',)); result=ex.execute(task,(TextMutation('docs/automation/autonomous_generated/probe.md','# Probe\n\nPASS\n'),),expected_head=head,keep_candidate=False)
            self.assertEqual(result['status'],'PASS'); self.assertTrue(result['mutation_performed']); self.assertFalse(result['mainline_promoted']); self.assertEqual(git(repo,'rev-parse','HEAD'),head); self.assertEqual(git(repo,'status','--porcelain=v1'),''); self.assertFalse(Path(result['worktree']).exists()); self.assertTrue(result['git_core_longpaths']); self.assertEqual(Path(result['worktree']).parent,ex.worktree_root); self.assertEqual(git(repo,'branch','--list','auto/lowrisk-*'),'')
    def test_dirty_outside_allowlist_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=self.repo(td); (repo/'README.md').write_text('dirty\n',encoding='utf-8'); ex=self.executor(repo,td); task=Task('T','Generate evidence','AUTO','update',('docs/automation/autonomous_generated/probe.md',))
            with self.assertRaises(RuntimeError): ex.execute(task,(TextMutation('docs/automation/autonomous_generated/probe.md','PASS\n'),),allowed_main_dirty_paths=('docs/automation/x.md',),keep_candidate=False)
if __name__=='__main__': unittest.main()
