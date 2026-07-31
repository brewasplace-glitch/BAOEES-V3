from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
REQS=("REQ-102","REQ-103","REQ-104","REQ-105","REQ-106","REQ-108")
def rj(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def wj(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(p):
 h=hashlib.sha256();h.update(Path(p).read_bytes());return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument("--repository",default=".");a.add_argument("--project",required=True);a.add_argument("--output",required=True);a.add_argument("--evidence-root");q=a.parse_args()
 repo=Path(q.repository).resolve();out=Path(q.output).resolve();project=rj(q.project)
 if out.exists():shutil.rmtree(out)
 out.mkdir(parents=True);wj(out/"project_manifest_snapshot.json",project)
 pipe=repo/"runners/PROJECT_PHOENIX_real_project_execution_pipeline_v6_2_0.py";po=out/"pipeline"
 cp=subprocess.run([sys.executable,str(pipe),"--repository",str(repo),"--project",str(Path(q.project).resolve()),"--output",str(po)],cwd=repo,text=True,capture_output=True,check=False,timeout=7200)
 (out/"pipeline_stdout.txt").write_text(cp.stdout or "",encoding="utf-8");(out/"pipeline_stderr.txt").write_text(cp.stderr or "",encoding="utf-8")
 if cp.returncode or not (po/"project_execution_run.json").is_file():raise RuntimeError("v6.2.0 prerequisite failed")
 root=Path(q.evidence_root).resolve() if q.evidence_root else out/"evidence_inputs";root.mkdir(parents=True,exist_ok=True)
 results={}
 for req in REQS:
  rd=root/req;rd.mkdir(parents=True,exist_ok=True);review=root/"professional_reviews"/f"{req}_professional_review.json"
  files=[p for p in rd.iterdir() if p.is_file() and p.stat().st_size>0]
  valid=False;decision="NOT_REVIEWED";reviewer=None
  if review.is_file():
   x=rj(review);reviewer=x.get("reviewer");decision=x.get("decision","NOT_REVIEWED");valid=bool(reviewer and reviewer.get("name") and reviewer.get("role") and reviewer.get("organization") and x.get("review_date") and decision in {"APPROVED","REJECTED"})
  closed=bool(files) and valid and decision=="APPROVED"
  results[req]={'status':'CLOSED' if closed else 'OPEN','files':[{'path':str(p),'size_bytes':p.stat().st_size,'sha256':sha(p)} for p in files],'professional_review':{'status':'VALID' if valid else 'MISSING_OR_INVALID','decision':decision,'reviewer':reviewer},'automatic_approval':False}
  wj(out/'requirements'/f'{req}_closure.json',results[req])
 if results['REQ-108']['status']=='CLOSED' and not all(results[r]['status']=='CLOSED' for r in REQS[:-1]):results['REQ-108']['status']='OPEN';wj(out/'requirements/REQ-108_closure.json',results['REQ-108'])
 closed=[r for r in REQS if results[r]['status']=='CLOSED'];openr=[r for r in REQS if results[r]['status']!='CLOSED'];permit=not openr
 twin=rj(po/'digital_twin_v6_2_0.json');twin['schema_version']='phoenix.digital-twin-project/6.3.0';twin['professional_evidence_closure']=results;twin['release']={'permit_ready':permit,'closed_requirements':closed,'open_requirements':openr};wj(out/'digital_twin_v6_3_0.json',twin)
 wj(out/'professional_evidence_register.json',{'closed_requirements':closed,'open_requirements':openr,'automatic_professional_approval':False,'requirements':results})
 arts=[]
 for p in sorted(out.rglob('*')):
  if p.is_file() and p.name!='artifact_manifest.json':arts.append({'path':p.relative_to(out).as_posix(),'size_bytes':p.stat().st_size,'sha256':sha(p)})
 wj(out/'artifact_manifest.json',{'artifact_count':len(arts),'artifacts':arts})
 wj(out/'permit_ready_release_gate.json',{'status':'UNLOCKED' if permit else 'LOCKED','permit_ready':permit,'closed_requirement_count':len(closed),'required_requirement_count':6,'open_requirements':openr,'automatic_professional_approval':False})
 wj(out/'evidence_closure_run.json',{'status':'PASSED','requirements_evaluated':6,'requirements_closed':len(closed),'requirements_open':len(openr),'permit_ready':permit,'automatic_approval':False})
 print('PROFESSIONAL EVIDENCE CLOSURE ENGINE: PASSED');print('REQUIREMENTS EVALUATED: 6');print('AUTOMATIC PROFESSIONAL APPROVAL: DISABLED');print('CENTRAL DIGITAL TWIN EVIDENCE WRITEBACK: PASSED');print('PERMIT-READY RELEASE GATE: '+('UNLOCKED' if permit else 'LOCKED'))
if __name__=='__main__':main()
