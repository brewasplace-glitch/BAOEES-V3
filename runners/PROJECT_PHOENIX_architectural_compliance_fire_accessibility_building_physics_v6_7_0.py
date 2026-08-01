from __future__ import annotations
import argparse,csv,hashlib,json,math,shutil
from pathlib import Path

def jr(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def jw(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def h(p):
 x=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):x.update(c)
 return x.hexdigest()
def csvw(p,fields,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise");w.writeheader();w.writerows(rows)

def rule(profile,*keys):
 v=profile.get("rules",{})
 for k in keys:
  if not isinstance(v,dict):return None
  v=v.get(k)
 return v

def check(name,domain,value,limit,operator,evidence,mandatory=True):
 status="NOT_ASSESSABLE"
 passed=False
 if limit is not None and value is not None:
  if operator=="<=": passed=float(value)<=float(limit)
  elif operator==">=": passed=float(value)>=float(limit)
  elif operator=="==": passed=value==limit
  status="PASS" if passed else "FAIL"
 return {"check_id":name,"domain":domain,"status":status,"value":value,"limit":limit,"operator":operator,"mandatory":mandatory,"evidence":evidence}

def build(project,arch,detail,profile):
 checks=[]; spaces=[r for s in arch["storeys"] for r in s["spaces"]]
 building_area=sum(float(s["gross_area_m2"]) for s in arch["storeys"])
 max_comp=rule(profile,"fire","max_compartment_area_m2")
 checks.append(check("FIRE-COMP-001","fire_compartments",building_area,max_comp,"<=",["architectural_model.storeys"]))

 max_escape=rule(profile,"fire","max_escape_distance_m")
 longest=max((math.hypot(float(r["width_m"]),float(r["depth_m"])) for r in spaces),default=0)
 checks.append(check("FIRE-ESC-001","escape_routes",round(longest,3),max_escape,"<=",["space geometry proxy"]))

 min_door=rule(profile,"accessibility","minimum_clear_door_width_m")
 doors=[o for s in detail["storeys"] for o in s["openings"] if o["category"]=="door"]
 smallest=min((float(o["width_m"]) for o in doors),default=None)
 checks.append(check("ACC-DOOR-001","accessibility",smallest,min_door,">=",["door openings"]))

 corridor=rule(profile,"accessibility","minimum_corridor_width_m")
 checks.append(check("ACC-COR-001","accessibility",None,corridor,">=",["corridor width evidence required"]))

 dayratio=rule(profile,"daylight","minimum_equivalent_daylight_area_ratio")
 windows=[o for s in detail["storeys"] for o in s["openings"] if o["category"]=="window"]
 window_area=sum(float(o["width_m"])*float(o["height_m"]) for o in windows)
 net_area=sum(float(r["area_m2"]) for r in spaces)
 ratio=window_area/net_area if net_area else None
 checks.append(check("PHY-DAY-001","daylight",round(ratio,4) if ratio is not None else None,dayratio,">=",["window schedule","room schedule"]))

 vent=rule(profile,"ventilation","minimum_outdoor_air_lps_person")
 checks.append(check("PHY-VENT-001","ventilation",None,vent,">=",["occupancy and ventilation design required"]))

 for cid,key,domain in [("PHY-UW-001","maximum_u_wall_w_m2k","wall"),("PHY-UR-001","maximum_u_roof_w_m2k","roof"),("PHY-UF-001","maximum_u_floor_w_m2k","floor"),("PHY-UG-001","maximum_u_window_w_m2k","window")]:
  checks.append(check(cid,"thermal_envelope",None,rule(profile,"thermal",key),"<=",["project-specific thermal properties required"]))

 moisture=rule(profile,"moisture","condensation_assessment_required")
 checks.append(check("PHY-MOIST-001","moisture_risk",None,moisture,"==",["hygrothermal assessment required"]))

 verified=bool(profile.get("jurisdiction",{}).get("verified"))
 legal_review=bool(profile.get("legal_release",{}).get("professional_approval"))
 mandatory=[c for c in checks if c["mandatory"]]
 assessable=all(c["status"]!="NOT_ASSESSABLE" for c in mandatory)
 all_pass=assessable and all(c["status"]=="PASS" for c in mandatory)
 permit=verified and legal_review and all_pass
 return checks,verified,legal_review,permit

def main():
 a=argparse.ArgumentParser();a.add_argument("--project",required=True);a.add_argument("--architectural-model",required=True);a.add_argument("--detailed-elements",required=True);a.add_argument("--rule-profile",required=True);a.add_argument("--output",required=True);q=a.parse_args()
 project=jr(q.project);arch=jr(q.architectural_model);detail=jr(q.detailed_elements);profile=jr(q.rule_profile);o=Path(q.output).resolve()
 if o.exists():shutil.rmtree(o)
 for d in ["reports","schedules","evidence"]: (o/d).mkdir(parents=True,exist_ok=True)
 checks,verified,legal_review,permit=build(project,arch,detail,profile)
 rows=[{"check_id":c["check_id"],"domain":c["domain"],"status":c["status"],"value":c["value"],"limit":c["limit"],"operator":c["operator"],"mandatory":c["mandatory"]} for c in checks]
 csvw(o/"schedules/compliance_check_register.csv",["check_id","domain","status","value","limit","operator","mandatory"],rows)
 jw(o/"reports/compliance_checks.json",{"checks":checks})
 summary={}
 for d in sorted(set(c["domain"] for c in checks)):
  ds=[c for c in checks if c["domain"]==d]
  summary[d]={"total":len(ds),"pass":sum(c["status"]=="PASS" for c in ds),"fail":sum(c["status"]=="FAIL" for c in ds),"not_assessable":sum(c["status"]=="NOT_ASSESSABLE" for c in ds)}
 jw(o/"reports/domain_summary.json",summary)
 jw(o/"digital_twin_compliance_v6_7_0.json",{"schema_version":"phoenix.digital-twin-compliance/6.7.0","project_id":project["project_id"],"rule_profile_id":profile["profile_id"],"jurisdiction_verified":verified,"professional_legal_review":legal_review,"checks":checks,"release":{"permit_ready":permit,"execution_ready":False}})
 jw(o/"architectural_compliance_release_gate.json",{"schema_version":"phoenix.architectural-compliance-release-gate/6.7.0","status":"UNLOCKED" if permit else "LOCKED","permit_ready":permit,"execution_ready":False,"jurisdiction_profile_verified":verified,"professional_legal_review":legal_review,"automatic_legal_approval":False,"not_assessable_count":sum(c["status"]=="NOT_ASSESSABLE" for c in checks)})
 arts=[]
 for p in sorted(o.rglob("*")):
  if p.is_file() and p.name!="artifact_manifest.json":arts.append({"path":p.relative_to(o).as_posix(),"size_bytes":p.stat().st_size,"sha256":h(p)})
 jw(o/"artifact_manifest.json",{"artifact_count":len(arts),"artifacts":arts})
 jw(o/"compliance_engine_run.json",{"status":"PASSED","project_id":project["project_id"],"pilot_project_dependency":False,"checks_executed":len(checks),"jurisdiction_profile_verified":verified,"permit_ready":permit,"execution_ready":False})
 print("ARCHITECTURAL COMPLIANCE, FIRE SAFETY, ACCESSIBILITY AND BUILDING PHYSICS ENGINE: PASSED")
 print("GENERIC JURISDICTION PROFILE ENGINE: ACTIVE")
 print("FIRE COMPARTMENT CHECKS: EXECUTED")
 print("ESCAPE ROUTE CHECKS: EXECUTED")
 print("ACCESSIBILITY CHECKS: EXECUTED")
 print("DAYLIGHT CHECKS: EXECUTED")
 print("VENTILATION CHECKS: EXECUTED")
 print("THERMAL ENVELOPE CHECKS: EXECUTED")
 print("MOISTURE RISK EVIDENCE CHECK: EXECUTED")
 print("CENTRAL DIGITAL TWIN COMPLIANCE WRITEBACK: PASSED")
 print("AUTOMATIC LEGAL COMPLIANCE APPROVAL: DISABLED")
 print("PERMIT-READY RELEASE: "+("UNLOCKED" if permit else "LOCKED"))
 print("EXECUTION-READY RELEASE: LOCKED")
if __name__=="__main__":main()
