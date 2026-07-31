from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser();a.add_argument("--executable",required=True);a.add_argument("--output",required=True);x=a.parse_args()
    exe=Path(x.executable).resolve();root=exe.parent;out=Path(x.output).resolve();out.mkdir(parents=True,exist_ok=True)
    candidates=list((root/"ExampleFiles").glob("1ZoneUncontrolled*.idf"))
    if not candidates: raise RuntimeError("Official 1ZoneUncontrolled example missing")
    model=out/"phoenix_energyplus_acceptance.idf";shutil.copy2(candidates[0],model)
    model_text=model.read_text(encoding="utf-8",errors="replace")
    if "Output:SQLite" not in model_text:
        model_text=model_text.rstrip()+"\n\nOutput:SQLite,\n  SimpleAndTabular;\n"
        model.write_text(model_text,encoding="utf-8",newline="\n")
    cp=subprocess.run([str(exe),"-D","-d",str(out),str(model)],cwd=str(out),text=True,capture_output=True,check=False,timeout=1800)
    (out/"energyplus_stdout.txt").write_text(cp.stdout or "",encoding="utf-8")
    (out/"energyplus_stderr.txt").write_text(cp.stderr or "",encoding="utf-8")
    err,end,sql=out/"eplusout.err",out/"eplusout.end",out/"eplusout.sql"
    for p in (err,end,sql):
        if not p.is_file() or p.stat().st_size==0: raise RuntimeError(f"Missing {p.name}")
    et=err.read_text(encoding="utf-8",errors="replace");nt=end.read_text(encoding="utf-8",errors="replace")
    severe=len(re.findall(r"\*\* Severe\s+\*\*",et));fatal=len(re.findall(r"\*\* Fatal\s+\*\*",et))
    if cp.returncode or severe or fatal or "completed successfully" not in nt.lower(): raise RuntimeError(f"EnergyPlus acceptance failed code={cp.returncode} severe={severe} fatal={fatal}")
    d={"status":"ACCEPTED","engine_id":"energyplus","simulation_exit_code":0,"severe_errors":0,"fatal_errors":0,"sqlite_output_requested":True,"sqlite_option_type":"SimpleAndTabular","acceptance_basis":"REAL_ENERGYPLUS_DESIGN_DAY_ARTIFACT","simulated":False,"artifacts":[{"path":p.name,"sha256":h(p),"size_bytes":p.stat().st_size} for p in (model,err,end,sql)]}
    (out/"energyplus_engine_acceptance.json").write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8");print(json.dumps(d,indent=2));return 0
if __name__=="__main__": raise SystemExit(main())
