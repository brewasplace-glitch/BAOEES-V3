import subprocess,tempfile,unittest
from pathlib import Path
from phoenix.development_console import PhoenixAutomationEngine,PhoenixDevelopmentConsole
class Q:
    def __init__(self,r):self.r=list(r);self.commands=[]
    def __call__(self,c,**k):self.commands.append(tuple(c));return self.r.pop(0)
def cp(rc=0,out='',err=''):return subprocess.CompletedProcess([],rc,out,err)
class T(unittest.TestCase):
    def test_console(self):
        with tempfile.TemporaryDirectory() as f:
            c=PhoenixDevelopmentConsole(f,runner=Q([cp(0,'project-phoenix\n'),cp()]));r=c.inspect();self.assertEqual(r.working_tree,'CLEAN');self.assertIn('PROJECT PHOENIX',c.render(r))
    def test_fail_fast(self):
        with tempfile.TemporaryDirectory() as f:
            q=Q([cp(0,'true\n'),cp(1,err='failed')]);r=PhoenixAutomationEngine(f,runner=q).run(commit_message='x',intended_paths=['a'],validation_commands=[('tests',('python','-m','unittest'))]);self.assertEqual(r.status,'failed');self.assertFalse(any(x[:2]==('git','add') for x in q.commands))
    def test_success(self):
        with tempfile.TemporaryDirectory() as f:
            q=Q([cp(0,'true\n'),cp(),cp(),cp(),cp(1),cp(),cp(0,'abc\n'),cp(0,'project-phoenix\n'),cp(),cp()]);r=PhoenixAutomationEngine(f,runner=q).run(commit_message='x',intended_paths=['a'],validation_commands=[('tests',('python','-m','unittest'))]);self.assertEqual(r.status,'completed');self.assertTrue(r.commit_created);self.assertTrue(r.push_performed);self.assertEqual(len(r.evidence_sha256),64)
    def test_no_empty_commit(self):
        with tempfile.TemporaryDirectory() as f:
            q=Q([cp(0,'true\n'),cp(),cp(),cp(),cp(),cp()]);r=PhoenixAutomationEngine(f,runner=q).run(commit_message='x',intended_paths=['a'],validation_commands=[('tests',('python','-m','unittest'))]);self.assertEqual(r.status,'completed');self.assertFalse(r.commit_created)
    def test_launcher(self):
        p=Path(__file__).resolve().parents[2]/'PROJECT_PHOENIX.cmd';s=p.read_text();self.assertIn('powershell.exe -NoExit',s)
if __name__=='__main__':unittest.main()
