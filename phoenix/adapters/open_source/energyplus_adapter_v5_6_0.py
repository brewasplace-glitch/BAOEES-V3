from pathlib import Path
import json,os,subprocess
from phoenix.adapters.open_source.base import Detection,EngineAdapter,EngineSpec
class EnergyPlusWindowsAdapter(EngineAdapter):
    spec=EngineSpec("energyplus","EnergyPlus",("energyplus.exe",),("ENERGYPLUS_EXE",),(".idf",".epjson"),(".sql",".csv",".err",".end"),"https://energyplus.net/")
    def detect(self):
        exe=Path(os.environ.get("ENERGYPLUS_EXE",r"C:\PHOENIX-ENGINES\EnergyPlus\26.1.0\energyplus.exe"))
        if not exe.is_file(): return Detection("energyplus",False,None,"not_found","",[])
        cp=subprocess.run([str(exe),"--version"],text=True,capture_output=True,check=False,timeout=120)
        e=Path("outputs/runtime/open_source_engines_v5_0_0/energyplus_acceptance/energyplus_engine_acceptance.json")
        ok=False;notes=[]
        if e.is_file():
            try:
                d=json.loads(e.read_text(encoding="utf-8"))
                ok=d.get("status")=="ACCEPTED" and d.get("simulated") is False and d.get("simulation_exit_code")==0 and d.get("severe_errors")==0 and d.get("fatal_errors")==0
            except Exception as x: notes.append(str(x))
        return Detection("energyplus",cp.returncode==0 and ok,str(exe.resolve()),"energyplus_windows_executable",(cp.stdout or cp.stderr).strip(),notes)
    def build_command(self,job,executable):
        return [executable,"-d",str(job["output"]),"-D",str(job["model"])]
