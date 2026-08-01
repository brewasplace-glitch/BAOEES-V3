from __future__ import annotations
import argparse,csv,hashlib,json,math,shutil
from pathlib import Path

def readj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def writej(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def csvw(p,fields,rows):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="raise")
        w.writeheader();w.writerows(rows)

def norm_costs(profile):
    rows=[]
    for i,x in enumerate(profile.get("cost_records",[]),1):
        rows.append({
            "cost_id":x.get("cost_id") or f"COST-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "category":x.get("category",""),
            "year":x.get("year"),
            "amount":x.get("amount"),
            "currency":x.get("currency",""),
            "verified":bool(x.get("verified",False)),
            "source_reference":x.get("source_reference","")
        })
    return rows

def norm_energy(profile):
    rows=[]
    for i,x in enumerate(profile.get("energy_records",[]),1):
        rows.append({
            "energy_id":x.get("energy_id") or f"EN-{i:05d}",
            "period":x.get("period",""),
            "carrier":x.get("carrier",""),
            "consumption":x.get("consumption"),
            "unit":x.get("unit",""),
            "cost":x.get("cost"),
            "meter_reference":x.get("meter_reference",""),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_resources(profile):
    rows=[]
    for i,x in enumerate(profile.get("resource_records",[]),1):
        rows.append({
            "resource_id":x.get("resource_id") or f"RES-{i:05d}",
            "period":x.get("period",""),
            "resource":x.get("resource",""),
            "quantity":x.get("quantity"),
            "unit":x.get("unit",""),
            "cost":x.get("cost"),
            "meter_reference":x.get("meter_reference",""),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_kpis(profile):
    rows=[]
    for i,x in enumerate(profile.get("performance_kpis",[]),1):
        rows.append({
            "kpi_id":x.get("kpi_id") or f"KPI-{i:05d}",
            "name":x.get("name",""),
            "period":x.get("period",""),
            "actual":x.get("actual"),
            "target":x.get("target"),
            "unit":x.get("unit",""),
            "direction":x.get("direction","MAX"),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_condition(profile):
    rows=[]
    for i,x in enumerate(profile.get("condition_records",[]),1):
        rows.append({
            "condition_id":x.get("condition_id") or f"COND-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "date":x.get("date",""),
            "grade":x.get("grade",""),
            "score":x.get("score"),
            "inspection_reference":x.get("inspection_reference",""),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_forecast(profile,key,prefix):
    rows=[]
    for i,x in enumerate(profile.get(key,[]),1):
        rows.append({
            "forecast_id":x.get("forecast_id") or f"{prefix}-{i:05d}",
            "asset_id":x.get("asset_id",""),
            "year":x.get("year"),
            "activity":x.get("activity",""),
            "estimated_cost":x.get("estimated_cost"),
            "currency":x.get("currency",""),
            "basis_reference":x.get("basis_reference",""),
            "verified":bool(x.get("verified",False))
        })
    return rows

def norm_recommendations(profile):
    rows=[]
    for i,x in enumerate(profile.get("optimization_recommendations",[]),1):
        rows.append({
            "recommendation_id":x.get("recommendation_id") or f"OPT-{i:05d}",
            "domain":x.get("domain",""),
            "description":x.get("description",""),
            "expected_annual_saving":x.get("expected_annual_saving"),
            "estimated_investment":x.get("estimated_investment"),
            "simple_payback_years":x.get("simple_payback_years"),
            "evidence_reference":x.get("evidence_reference",""),
            "status":x.get("status","PROPOSED"),
            "approved":bool(x.get("approved",False))
        })
    return rows

def discounted(value,year,rate):
    return float(value)/((1.0+float(rate))**int(year))

def evaluate(profile,costs,energy,kpis,condition,recommendations,operations_gate):
    operations_ok=bool(operations_gate and operations_gate.get("status")=="UNLOCKED")
    assumptions=profile.get("financial_assumptions",{})
    financial_ok=bool(
        assumptions.get("verified") and
        assumptions.get("currency") and
        assumptions.get("analysis_period_years") is not None and
        assumptions.get("discount_rate") is not None
    )

    verified_energy=[e for e in energy if e["verified"]]
    energy_ok=bool(verified_energy) and all(e["consumption"] is not None and e["unit"] and e["meter_reference"] for e in verified_energy)

    verified_condition=[c for c in condition if c["verified"]]
    condition_ok=bool(verified_condition) and all(c["grade"] and c["inspection_reference"] for c in verified_condition)

    verified_kpis=[k for k in kpis if k["verified"]]
    kpi_ok=bool(verified_kpis) and all(k["actual"] is not None and k["target"] is not None and k["unit"] for k in verified_kpis)

    verified_costs=[c for c in costs if c["verified"]]
    cost_ok=bool(verified_costs) and all(c["amount"] is not None and c["currency"] and c["source_reference"] for c in verified_costs)

    recommendation_evidence=bool(recommendations) and all(r["description"] and r["evidence_reference"] for r in recommendations)
    professional=bool(profile.get("professional_optimization_approval",{}).get("approved"))

    ready=all([operations_ok,financial_ok,energy_ok,condition_ok,kpi_ok,cost_ok,recommendation_evidence,professional])

    return {
        "operations_release_gate_pass":operations_ok,
        "financial_assumptions_verified":financial_ok,
        "energy_baseline_verified":energy_ok,
        "condition_data_verified":condition_ok,
        "performance_kpis_verified":kpi_ok,
        "lifecycle_cost_data_verified":cost_ok,
        "optimization_evidence_complete":recommendation_evidence,
        "professional_optimization_approval":professional,
        "optimization_action_ready":ready,
        "automatic_optimization_action":False
    }

def derive_kpi_deviations(kpis):
    rows=[]
    for k in kpis:
        actual=k["actual"];target=k["target"];direction=k["direction"]
        deviation=None;status="NOT_ASSESSABLE"
        if actual is not None and target is not None:
            deviation=float(actual)-float(target)
            if direction=="MAX":
                status="PASS" if float(actual)<=float(target) else "DEVIATION"
            elif direction=="MIN":
                status="PASS" if float(actual)>=float(target) else "DEVIATION"
            else:
                status="PASS" if float(actual)==float(target) else "DEVIATION"
        rows.append({
            "kpi_id":k["kpi_id"],
            "name":k["name"],
            "period":k["period"],
            "actual":actual,
            "target":target,
            "unit":k["unit"],
            "deviation":deviation,
            "status":status
        })
    return rows

def lifecycle_summary(profile,costs,maintenance,replacement):
    assumptions=profile.get("financial_assumptions",{})
    rate=assumptions.get("discount_rate")
    pv_cost=None
    if rate is not None:
        total=0.0
        valid=True
        for x in list(costs)+list(maintenance)+list(replacement):
            amount=x.get("amount",x.get("estimated_cost"))
            year=x.get("year")
            if amount is None or year is None:
                valid=False
                break
            total+=discounted(amount,year,rate)
        if valid:
            pv_cost=round(total,2)
    return {
        "currency":assumptions.get("currency",""),
        "analysis_period_years":assumptions.get("analysis_period_years"),
        "discount_rate":rate,
        "present_value_lifecycle_cost":pv_cost
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",required=True)
    ap.add_argument("--optimization-profile",required=True)
    ap.add_argument("--operations-gate",required=False)
    ap.add_argument("--output",required=True)
    q=ap.parse_args()

    project=readj(q.project)
    profile=readj(q.optimization_profile)
    operations_gate=readj(q.operations_gate) if q.operations_gate else None

    out=Path(q.output).resolve()
    if out.exists():
        shutil.rmtree(out)

    for d in ("cost","energy","resources","kpis","condition","forecast","optimization","reports","digital_twin"):
        (out/d).mkdir(parents=True,exist_ok=True)

    costs=norm_costs(profile)
    energy=norm_energy(profile)
    resources=norm_resources(profile)
    kpis=norm_kpis(profile)
    condition=norm_condition(profile)
    maintenance=norm_forecast(profile,"maintenance_forecasts","MFC")
    replacement=norm_forecast(profile,"replacement_forecasts","RFC")
    recommendations=norm_recommendations(profile)

    gate=evaluate(profile,costs,energy,kpis,condition,recommendations,operations_gate)
    deviations=derive_kpi_deviations(kpis)
    lcc=lifecycle_summary(profile,costs,maintenance,replacement)

    csvw(out/"cost/lifecycle_cost_register.csv",
         ["cost_id","asset_id","category","year","amount","currency","verified","source_reference"],costs)
    csvw(out/"energy/energy_performance_register.csv",
         ["energy_id","period","carrier","consumption","unit","cost","meter_reference","verified"],energy)
    csvw(out/"resources/resource_performance_register.csv",
         ["resource_id","period","resource","quantity","unit","cost","meter_reference","verified"],resources)
    csvw(out/"kpis/performance_kpi_register.csv",
         ["kpi_id","name","period","actual","target","unit","direction","verified"],kpis)
    csvw(out/"kpis/performance_deviation_register.csv",
         ["kpi_id","name","period","actual","target","unit","deviation","status"],deviations)
    csvw(out/"condition/condition_monitoring_register.csv",
         ["condition_id","asset_id","date","grade","score","inspection_reference","verified"],condition)
    csvw(out/"forecast/maintenance_forecast_register.csv",
         ["forecast_id","asset_id","year","activity","estimated_cost","currency","basis_reference","verified"],maintenance)
    csvw(out/"forecast/replacement_forecast_register.csv",
         ["forecast_id","asset_id","year","activity","estimated_cost","currency","basis_reference","verified"],replacement)
    csvw(out/"optimization/optimization_recommendation_register.csv",
         ["recommendation_id","domain","description","expected_annual_saving","estimated_investment","simple_payback_years","evidence_reference","status","approved"],recommendations)

    writej(out/"reports/lifecycle_cost_summary.json",lcc)
    writej(out/"reports/performance_optimization_matrix.json",{
        "lifecycle_cost_summary":lcc,
        "energy_records":energy,
        "resource_records":resources,
        "performance_kpis":kpis,
        "performance_deviations":deviations,
        "condition_records":condition,
        "maintenance_forecasts":maintenance,
        "replacement_forecasts":replacement,
        "optimization_recommendations":recommendations,
        "release":gate
    })

    writej(out/"optimization_action_gate.json",{
        "schema_version":"phoenix.optimization-action-gate/7.4.0",
        "status":"UNLOCKED" if gate["optimization_action_ready"] else "LOCKED",
        **gate,
        "blocking_reasons":[k for k,v in gate.items() if k not in ("optimization_action_ready","automatic_optimization_action") and v is False]
    })

    writej(out/"digital_twin/lifecycle_performance_optimization_v7_4_0.json",{
        "schema_version":"phoenix.digital-twin-lifecycle-optimization/7.4.0",
        "project_id":project.get("project_id",""),
        "cost_record_count":len(costs),
        "energy_record_count":len(energy),
        "resource_record_count":len(resources),
        "kpi_count":len(kpis),
        "condition_record_count":len(condition),
        "maintenance_forecast_count":len(maintenance),
        "replacement_forecast_count":len(replacement),
        "optimization_recommendation_count":len(recommendations),
        "optimization_action_ready":gate["optimization_action_ready"],
        "automatic_optimization_action":False
    })

    artifacts=[]
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="artifact_manifest.json":
            artifacts.append({
                "path":p.relative_to(out).as_posix(),
                "size_bytes":p.stat().st_size,
                "sha256":sha(p)
            })
    writej(out/"artifact_manifest.json",{"artifact_count":len(artifacts),"artifacts":artifacts})

    writej(out/"lifecycle_optimization_engine_run.json",{
        "status":"PASSED",
        "project_id":project.get("project_id",""),
        "pilot_project_dependency":False,
        "optimization_action_ready":gate["optimization_action_ready"],
        "automatic_optimization_action":False
    })

    print("LIFECYCLE COST, ENERGY, PERFORMANCE, CONDITION MONITORING AND OPTIMIZATION ENGINE: PASSED")
    print("LIFECYCLE COST REGISTER: GENERATED")
    print("ENERGY PERFORMANCE REGISTER: GENERATED")
    print("RESOURCE PERFORMANCE REGISTER: GENERATED")
    print("PERFORMANCE KPI REGISTER: GENERATED")
    print("PERFORMANCE DEVIATION REGISTER: GENERATED")
    print("CONDITION MONITORING REGISTER: GENERATED")
    print("MAINTENANCE FORECAST REGISTER: GENERATED")
    print("REPLACEMENT FORECAST REGISTER: GENERATED")
    print("OPTIMIZATION RECOMMENDATION REGISTER: GENERATED")
    print("LIFECYCLE COST SUMMARY: GENERATED")
    print("CENTRAL DIGITAL TWIN LIFECYCLE OPTIMIZATION WRITEBACK: PASSED")
    print("AUTOMATIC OPTIMIZATION ACTION: DISABLED")
    print("OPTIMIZATION-ACTION RELEASE: "+("UNLOCKED" if gate["optimization_action_ready"] else "LOCKED"))

if __name__=="__main__":
    main()
