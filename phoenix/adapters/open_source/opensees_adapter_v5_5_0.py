from __future__ import annotations
from pathlib import Path
import json, os, subprocess, sys
from phoenix.adapters.open_source.base import Detection, EngineAdapter, EngineSpec

class OpenSeesPyAdapter(EngineAdapter):
    spec=EngineSpec(
        "opensees","OpenSeesPy",
        ("python.exe","python3.exe","python"),
        ("OPENSEESPY_PYTHON",),
        (".py",".tcl"),(".json",".csv",".txt"),
        "https://opensees.github.io/OpenSeesDocumentation/",
    )
    def detect(self):
        configured=os.environ.get("OPENSEESPY_PYTHON","").strip()
        exe=Path(configured) if configured else Path(r"C:\PHOENIX-ENGINES\OpenSeesPy\3.8.0.0\venv\Scripts\python.exe")
        if not exe.is_file():
            return Detection("opensees",False,None,"not_found","",[])
        cp=subprocess.run(
            [str(exe),"-c","import openseespy.opensees as ops;print(ops.version())"],
            text=True,capture_output=True,check=False,timeout=120,
        )
        evidence=Path(
            "outputs/runtime/open_source_engines_v5_0_0/"
            "opensees_acceptance/opensees_engine_acceptance.json"
        )
        accepted=False
        notes=[]
        if evidence.is_file():
            try:
                data=json.loads(evidence.read_text(encoding="utf-8"))
                accepted=(
                    data.get("status")=="ACCEPTED"
                    and data.get("simulated") is False
                    and data.get("analysis_code")==0
                    and data.get("acceptance_basis")
                        =="REAL_OPENSEES_LINEAR_STATIC_ARTIFACT"
                )
                if accepted:
                    notes.append("availability confirmed by real accepted structural evidence")
            except Exception as exc:
                notes.append(f"acceptance evidence unreadable: {exc}")
        if cp.returncode!=0:
            notes.append(f"OpenSeesPy import probe exit code {cp.returncode}")
        return Detection(
            "opensees",
            cp.returncode==0 and accepted,
            str(exe.resolve()),
            "openseespy_python_module",
            cp.stdout.strip(),
            notes,
        )
    def build_command(self,job,executable):
        script=job.get("script")
        if not script:
            raise ValueError("OpenSeesPy job requires script")
        return [executable,str(script)]
