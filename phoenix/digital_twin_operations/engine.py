from __future__ import annotations
import hashlib, json
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

class DigitalTwinOperationsEngine:
    VERSION = "1.0.0"
    SCHEMA_VERSION = "phoenix.digital-twin-operations-report/1.0"

    def create_report(self, project_metadata: Mapping[str, Any], *,
                      assets: Sequence[Mapping[str, Any]],
                      maintenance_plans: Sequence[Mapping[str, Any]] = (),
                      service_events: Sequence[Mapping[str, Any]] = (),
                      condition_assessments: Sequence[Mapping[str, Any]] = (),
                      as_of_date: str | date = "2026-01-01",
                      forecast_years: int = 10) -> dict[str, Any]:
        project_id = str(project_metadata.get("project_id") or "PHX-UNSPECIFIED")
        as_of = as_of_date if isinstance(as_of_date,date) else date.fromisoformat(str(as_of_date))
        issues = []
        asset_ids = self._check_ids(assets,"asset_id",issues)
        self._check_ids(maintenance_plans,"plan_id",issues)
        self._check_ids(service_events,"event_id",issues)
        self._check_ids(condition_assessments,"assessment_id",issues)

        due=[]; annual_cost=0.0
        for plan in maintenance_plans:
            asset_id=str(plan.get("asset_id") or "")
            if asset_id not in asset_ids:
                issues.append(self._issue("BB29-PLAN-ASSET","error","Maintenance plan references unknown asset.",True)); continue
            interval=plan.get("interval_days"); cost=plan.get("annual_cost",0)
            if isinstance(interval,bool) or not isinstance(interval,int) or interval<=0:
                issues.append(self._issue("BB29-PLAN-INTERVAL","error","Invalid maintenance interval.",True)); continue
            if isinstance(cost,bool) or not isinstance(cost,(int,float)) or cost<0:
                issues.append(self._issue("BB29-PLAN-COST","error","Invalid maintenance cost.",True)); continue
            annual_cost += float(cost)
            prior = [
                date.fromisoformat(str(x.get("service_date")))
                for x in service_events
                if str(x.get("asset_id") or "") == asset_id and x.get("service_date")
            ]
            base=max(prior) if prior else as_of
            next_due=base+timedelta(days=interval)
            if next_due <= as_of+timedelta(days=90):
                due.append({"asset_id":asset_id,"plan_id":str(plan.get("plan_id")),
                            "next_due_date":next_due.isoformat(),"overdue":next_due<as_of})

        poor=sorted({str(x.get("asset_id")) for x in condition_assessments
                     if str(x.get("condition") or "").lower() in {"poor","critical"}})
        for asset_id in poor:
            issues.append(self._issue("BB29-CONDITION","warning",f"Asset {asset_id} has poor/critical condition.",False))
        uncommissioned=[str(x.get("asset_id")) for x in assets if not bool(x.get("commissioned",False))]
        if uncommissioned:
            issues.append(self._issue("BB29-ASSET-NOT-COMMISSIONED","critical",
                                      f"{len(uncommissioned)} asset(s) not commissioned.",True))

        report = {
            "schema_version":self.SCHEMA_VERSION,"engine_version":self.VERSION,"project_id":project_id,
            "as_of_date":as_of.isoformat(),"forecast_years":forecast_years,"asset_count":len(assets),
            "maintenance_plan_count":len(maintenance_plans),"service_event_count":len(service_events),
            "condition_assessment_count":len(condition_assessments),
            "due_maintenance_actions":sorted(due,key=lambda x:(x["next_due_date"],x["asset_id"])),
            "poor_condition_asset_ids":poor,"uncommissioned_asset_ids":uncommissioned,
            "annual_planned_maintenance_cost":round(annual_cost,2),
            "lifecycle_maintenance_forecast":round(annual_cost*forecast_years,2),
            "issues":issues,"blocking_issue_count":sum(1 for x in issues if x["blocking"]),
            "operations_ready":not any(x["blocking"] for x in issues),
            "metadata":{"non_certifying":True,"forecast_excludes_inflation":True,"automatic_work_order_release":False},
        }
        report["report_fingerprint_sha256"]=self._fingerprint(report)
        return report

    @staticmethod
    def _check_ids(items,key,issues):
        seen=set()
        for item in items:
            value=str(item.get(key) or "").strip()
            if not value: issues.append({"code":"BB29-ID-MISSING","severity":"error","message":f"Record has no {key}.","blocking":True})
            elif value in seen: issues.append({"code":"BB29-ID-DUPLICATE","severity":"error","message":f"Duplicate {key}: {value}.","blocking":True})
            seen.add(value)
        return seen
    @staticmethod
    def _issue(code,severity,message,blocking): return {"code":code,"severity":severity,"message":message,"blocking":blocking}
    @staticmethod
    def _fingerprint(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
