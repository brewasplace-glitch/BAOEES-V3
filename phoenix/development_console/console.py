"""Environment checks for Project Phoenix."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import importlib.util, json, shutil, subprocess, sys
from pathlib import Path
from typing import Callable
Runner=Callable[...,subprocess.CompletedProcess[str]]
@dataclass(frozen=True)
class ConsoleCheck:
    name:str; status:str; details:str
@dataclass(frozen=True)
class ConsoleReport:
    repository:str; branch:str; working_tree:str; checks:tuple[ConsoleCheck,...]
    def to_dict(self):
        return {"repository":self.repository,"branch":self.branch,"working_tree":self.working_tree,"checks":[asdict(x) for x in self.checks]}
class PhoenixDevelopmentConsole:
    def __init__(self,repo_root:str|Path,*,runner:Runner=subprocess.run):
        self.repo_root=Path(repo_root).expanduser().resolve(); self._runner=runner
    def _run(self,cmd):
        return self._runner(cmd,cwd=self.repo_root,capture_output=True,text=True,timeout=20,shell=False,check=False)
    def inspect(self):
        branch=self._run(["git","rev-parse","--abbrev-ref","HEAD"])
        status=self._run(["git","status","--porcelain"])
        wt="CLEAN" if status.returncode==0 and not status.stdout.strip() else ("DIRTY" if status.returncode==0 else "ERROR")
        checks=[
            ConsoleCheck("Git","OK" if shutil.which("git") else "NOT FOUND",shutil.which("git") or "git"),
            ConsoleCheck("Python","OK",f"{sys.executable} ({sys.version.split()[0]})"),
            ConsoleCheck("Phoenix Package Manager","OK" if importlib.util.find_spec("phoenix.package_manager") else "NOT FOUND","phoenix.package_manager"),
            ConsoleCheck("FreeCAD","OK" if (shutil.which("FreeCADCmd.exe") or shutil.which("FreeCADCmd")) else "NOT FOUND",shutil.which("FreeCADCmd.exe") or shutil.which("FreeCADCmd") or "FreeCADCmd"),
            ConsoleCheck("IfcOpenShell","OK" if importlib.util.find_spec("ifcopenshell") else "NOT FOUND","ifcopenshell"),
            ConsoleCheck("Blender","OK" if (shutil.which("blender.exe") or shutil.which("blender")) else "NOT FOUND",shutil.which("blender.exe") or shutil.which("blender") or "blender"),
            ConsoleCheck("Working tree",wt,"nothing to commit, working tree clean" if wt=="CLEAN" else "changes or error detected"),
        ]
        return ConsoleReport(self.repo_root.name,branch.stdout.strip() if branch.returncode==0 else "unknown",wt,tuple(checks))
    @staticmethod
    def render(report):
        lines=["="*57,"                 PROJECT PHOENIX","               Development Console","="*57,f"Repository   : {report.repository}",f"Branch       : {report.branch}",f"Working tree : {report.working_tree}","-"*57]
        lines += [f"{x.name:<24}: {x.status:<10} {x.details}" for x in report.checks]
        lines.append("="*57); return "\n".join(lines)
    @staticmethod
    def write_json(report,destination):
        p=Path(destination).resolve(); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(report.to_dict(),indent=2,sort_keys=True)+'\n',encoding='utf-8'); t.replace(p); return p
