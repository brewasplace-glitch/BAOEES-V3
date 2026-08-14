"""PROJECT PHOENIX Structural Golden Reference Suite v1.0."""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json

ANALYTICAL_VALIDATED="GOLDEN_BENCHMARK_ANALYTICAL_VALIDATED"
ANALYTICAL_FAILED="GOLDEN_BENCHMARK_ANALYTICAL_FAILED"
CALCULIX_PREPARED="GOLDEN_BENCHMARK_CALCULIX_PREPARED"
SUITE_PARTIAL="GOLDEN_REFERENCE_SUITE_ANALYTICAL_VALIDATED_NUMERICAL_PARTIAL"
SUITE_ANALYTICAL="GOLDEN_REFERENCE_SUITE_ANALYTICAL_VALIDATED"
SAFETY={"automatic_professional_approval":False,"automatic_code_compliance_claim":False,"production_release":"LOCKED","for_construction_release":"LOCKED"}

def rj(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def wj(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def analytical(d):
    k=d["idealization"]; i=d["inputs"]; e=d["expected"]
    if k=="SIMPLY_SUPPORTED_BEAM_UDL":
        q=float(i["q_N_per_m"]); L=float(i["L_m"]); c={"total_load_N":q*L,"reaction_each_N":q*L/2,"max_moment_Nm":q*L*L/8}
    elif k=="CANTILEVER_END_POINT_LOAD":
        P=float(i["P_N"]); L=float(i["L_m"]); E=float(i["E_Pa"]); I=float(i["I_m4"]); c={"reaction_N":P,"fixed_end_moment_Nm":P*L,"tip_deflection_m":P*L**3/(3*E*I)}
    elif k=="AXIAL_BAR":
        P=float(i["P_N"]); L=float(i["L_m"]); E=float(i["E_Pa"]); A=float(i["A_m2"]); c={"axial_stress_Pa":P/A,"elongation_m":P*L/(E*A)}
    else: raise ValueError(k)
    errs={}
    for key,val in e.items():
        a=float(c[key]); t=float(val)
        if abs(a-t)>1e-12*max(1.0,abs(t)): errs[key]={"actual":a,"expected":t}
    return {"status":ANALYTICAL_VALIDATED if not errs else ANALYTICAL_FAILED,"benchmark_id":d["id"],"computed":c,"expected":e,"errors":errs,"safety":dict(SAFETY)}

def deck(d,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    k=d["idealization"]; i=d["inputs"]; n=int(d["calculix"]["element_count"]); bid=d["id"]
    lines=["*HEADING",f"PROJECT PHOENIX {bid}","*NODE"]
    if k in ("SIMPLY_SUPPORTED_BEAM_UDL","CANTILEVER_END_POINT_LOAD"):
        L=float(i["L_m"]); dx=L/n
        lines += [f"{j+1}, {j*dx:.12g}, 0., 0." for j in range(n+1)]
        lines += ["*ELEMENT, TYPE=B31, ELSET=EALL"]+[f"{j+1}, {j+1}, {j+2}" for j in range(n)]
        E=float(i.get("E_Pa",210e9)); b=float(i.get("section_b_m",0.1)); h=float(i.get("section_h_m",0.1))
        lines += ["*MATERIAL, NAME=REFMAT","*ELASTIC",f"{E:.12g}, 0.3","*BEAM SECTION, ELSET=EALL, MATERIAL=REFMAT, SECTION=RECT",f"{b:.12g}, {h:.12g}","0., 1., 0."]
        if k=="SIMPLY_SUPPORTED_BEAM_UDL":
            q=float(i["q_N_per_m"]); lines += ["*NSET, NSET=SUPPORTS",f"1, {n+1}","*BOUNDARY","1, 1, 3","1, 4, 4",f"{n+1}, 2, 3","*STEP","*STATIC","*CLOAD"]
            for j in range(n+1):
                load=-q*dx*(0.5 if j in (0,n) else 1.0); lines.append(f"{j+1}, 3, {load:.12g}")
            lines += ["*NODE PRINT, NSET=SUPPORTS, TOTALS=YES","RF","*END STEP"]
        else:
            P=float(i["P_N"]); lines += ["*NSET, NSET=FIXED","1","*NSET, NSET=TIP",f"{n+1}","*BOUNDARY","1, 1, 6","*STEP","*STATIC","*CLOAD",f"{n+1}, 3, {-P:.12g}","*NODE PRINT, NSET=FIXED, TOTALS=YES","RF","*NODE PRINT, NSET=TIP","U","*END STEP"]
    elif k=="AXIAL_BAR":
        L=float(i["L_m"]); dx=L/n; P=float(i["P_N"]); E=float(i["E_Pa"]); A=float(i["A_m2"])
        lines += [f"{j+1}, {j*dx:.12g}, 0., 0." for j in range(n+1)]
        lines += ["*ELEMENT, TYPE=T3D2, ELSET=EALL"]+[f"{j+1}, {j+1}, {j+2}" for j in range(n)]
        lines += ["*MATERIAL, NAME=REFMAT","*ELASTIC",f"{E:.12g}, 0.3","*SOLID SECTION, ELSET=EALL, MATERIAL=REFMAT",f"{A:.12g}","*NSET, NSET=FIXED","1","*NSET, NSET=TIP",f"{n+1}","*BOUNDARY","1, 1, 3","*STEP","*STATIC","*CLOAD",f"{n+1}, 1, {P:.12g}","*NODE PRINT, NSET=FIXED, TOTALS=YES","RF","*NODE PRINT, NSET=TIP","U","*EL PRINT, ELSET=EALL","S","*END STEP"]
    else: raise ValueError(k)
    p=out/f"{bid}.inp"; p.write_text("\n".join(lines)+"\n",encoding="ascii")
    r={"status":CALCULIX_PREPARED,"benchmark_id":bid,"deck":str(p),"deck_sha256":sha(p),"element_count":n,"live_solver_started":False,"numerical_validation":d["calculix"].get("validation_status"),"numerical_tolerance":d["calculix"].get("numerical_tolerance",d["calculix"].get("software_test_tolerance_N")),"safety":dict(SAFETY)}
    wj(out/f"{bid}.preparation.json",r); return r

def prepare_all(repo,reg,out):
    repo=Path(repo); reg=rj(reg); out=Path(out); items=[]
    for x in reg["benchmarks"]:
        d=rj(repo/x["definition"])
        a=analytical(d)
        if a["status"]!=ANALYTICAL_VALIDATED: raise RuntimeError(x["id"])
        items.append(deck(d,out/x["id"]))
    r={"status":"GOLDEN_REFERENCE_SUITE_CALCULIX_DECKS_PREPARED","suite_id":reg["suite_id"],"prepared_count":len(items),"live_solver_started":False,"benchmarks":items,"safety":dict(SAFETY)}
    wj(out/"golden_reference_suite_preparation.json",r); return r

def assess(repo,reg,out):
    repo=Path(repo); reg=rj(reg); rows=[]; calc_ok=0
    for x in reg["benchmarks"]:
        d=rj(repo/x["definition"]); a=analytical(d); cs=d["calculix"].get("validation_status","PENDING")
        ev=x.get("existing_calculix_reevaluation")
        evidence=None
        if ev and (repo/ev).is_file():
            e=rj(repo/ev); cs=e.get("status",cs); evidence={"path":str(repo/ev),"sha256":sha(repo/ev)}
        if cs=="CALCULIX_GOLDEN_REFERENCE_VALIDATED": calc_ok+=1
        rows.append({"benchmark_id":x["id"],"analytical":a,"calculix_status":cs,"calculix_evidence":evidence,"scia_status":"GOLDEN_BENCHMARK_SCIA_LIVE_PENDING" if x.get("scia_source_available") else "GOLDEN_BENCHMARK_SCIA_NOT_CONFIGURED"})
    all_a=all(x["analytical"]["status"]==ANALYTICAL_VALIDATED for x in rows)
    status=SUITE_PARTIAL if all_a and calc_ok else SUITE_ANALYTICAL if all_a else ANALYTICAL_FAILED
    r={"status":status,"suite_id":reg["suite_id"],"benchmark_count":len(rows),"analytical_validated_count":sum(x["analytical"]["status"]==ANALYTICAL_VALIDATED for x in rows),"calculix_validated_count":calc_ok,"benchmarks":rows,"scia_live_suite_validation_complete":False,"professional_review":False,"safety":dict(SAFETY)}
    wj(out,r); return r

def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="a",required=True)
    q=s.add_parser("prepare-all"); q.add_argument("--repository",required=True); q.add_argument("--registry",required=True); q.add_argument("--output",required=True)
    q=s.add_parser("assess"); q.add_argument("--repository",required=True); q.add_argument("--registry",required=True); q.add_argument("--output",required=True)
    a=p.parse_args(); r=prepare_all(a.repository,a.registry,a.output) if a.a=="prepare-all" else assess(a.repository,a.registry,a.output); print(json.dumps(r,indent=2))
    if r.get("status")==ANALYTICAL_FAILED: raise SystemExit(1)
if __name__=="__main__": main()
