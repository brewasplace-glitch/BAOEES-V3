from pathlib import Path
import os, shutil, subprocess

def quote(value: str) -> str:
    return '"' + value.replace('"','""') + '"'

def command_for_launcher(launcher: Path, args: list[str]) -> list[str]:
    launcher=launcher.resolve()
    if launcher.suffix.lower() in {".bat",".cmd"}:
        cmd=shutil.which("cmd.exe") or os.environ.get("COMSPEC") or "cmd.exe"
        line=quote(str(launcher))
        if args:
            line+=" "+" ".join(quote(str(x)) for x in args)
        return [cmd,"/d","/c",line]
    return [str(launcher),*args]

def find_qgis_process() -> Path|None:
    env=os.environ.get("QGIS_PROCESS_EXE","").strip()
    candidates=[
        Path(env) if env else None,
        Path(r"C:\OSGeo4W\bin\qgis_process-qgis-ltr.bat"),
        Path(r"C:\OSGeo4W\bin\qgis_process-qgis.bat"),
        Path(r"C:\OSGeo4W\apps\qgis-ltr\bin\qgis_process.exe"),
        Path(r"C:\OSGeo4W64\bin\qgis_process-qgis-ltr.bat"),
    ]
    return next((p for p in candidates if p and p.is_file()),None)

def probe_version(launcher: Path):
    cp=subprocess.run(command_for_launcher(launcher,["--version"]),text=True,capture_output=True,timeout=120,check=False)
    return cp.returncode,cp.stdout or "",cp.stderr or ""
