from __future__ import annotations
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

class SiteExecutionQAQCEngine:
    VERSION = "1.0.0"
    SCHEMA_VERSION = "phoenix.site-execution-qaqc-report/1.0"

    def create_report(self, project_metadata: Mapping[str, Any], *,
                      activities: Sequence[Mapping[str, Any]],
                      inspections: Sequence[Mapping[str, Any]] = (),
                      ncrs: Sequence[Mapping[str, Any]] = (),
                      daily_logs: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
        project_id = str(project_metadata.get("project_id") or "PHX-UNSPECIFIED")
        issues = []
        for items, key, blocking in (
            (activities,"activity_id",True),(inspections,"inspection_id",False),
            (ncrs,"ncr_id",True),(daily_logs,"log_id",False),
        ):
            self._check_ids(items, key, issues, blocking)

        total_weight = completed = 0.0
        for item in activities:
            weight = item.get("weight", item.get("direct_cost", 1.0))
            if isinstance(weight, bool) or not isinstance(weight, (int,float)) or weight < 0:
                issues.append(self._issue("BB27-WEIGHT","error","Invalid activity weight.",True)); weight = 0
            progress = item.get("progress_percent", 0)
            if isinstance(progress, bool) or not isinstance(progress,(int,float)) or not 0 <= progress <= 100:
                issues.append(self._issue("BB27-PROGRESS","error","Invalid activity progress.",True)); progress = 0
            total_weight += float(weight); completed += float(weight) * float(progress) / 100.0

        failed = sum(1 for x in inspections if str(x.get("result") or "").lower() == "failed")
        overdue = sum(1 for x in inspections if bool(x.get("overdue")) and str(x.get("result") or "").lower() not in {"passed","closed"})
        if failed:
            issues.append(self._issue("BB27-INSP-FAILED","error",f"{failed} inspection(s) failed.",True))
        if overdue:
            issues.append(self._issue("BB27-INSP-OVERDUE","warning",f"{overdue} inspection(s) overdue.",False))

        open_major = sum(
            1 for x in ncrs
            if str(x.get("status") or "open").lower() not in {"closed","resolved","accepted"}
            and str(x.get("severity") or "minor").lower() in {"major","critical"}
        )
        open_minor = sum(
            1 for x in ncrs
            if str(x.get("status") or "open").lower() not in {"closed","resolved","accepted"}
            and str(x.get("severity") or "minor").lower() not in {"major","critical"}
        )
        if open_major:
            issues.append(self._issue("BB27-NCR-MAJOR","critical",f"{open_major} major/critical NCR(s) open.",True))

        report = {
            "schema_version":self.SCHEMA_VERSION,"engine_version":self.VERSION,"project_id":project_id,
            "activity_count":len(activities),
            "weighted_progress_percent":round(completed/total_weight*100,2) if total_weight else 0.0,
            "inspection_count":len(inspections),"failed_inspection_count":failed,"overdue_inspection_count":overdue,
            "open_major_ncr_count":open_major,"open_minor_ncr_count":open_minor,"daily_log_count":len(daily_logs),
            "issues":issues,"blocking_issue_count":sum(1 for x in issues if x["blocking"]),
            "site_quality_passed":not any(x["blocking"] for x in issues),
            "metadata":{"non_certifying":True,"inspection_approval_requires_human":True},
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _check_ids(items,key,issues,blocking):
        seen=set()
        for item in items:
            value=str(item.get(key) or "").strip()
            if not value: issues.append({"code":"BB27-ID-MISSING","severity":"error","message":f"Record has no {key}.","blocking":blocking})
            elif value in seen: issues.append({"code":"BB27-ID-DUPLICATE","severity":"error","message":f"Duplicate {key}: {value}.","blocking":blocking})
            seen.add(value)
    @staticmethod
    def _issue(code,severity,message,blocking): return {"code":code,"severity":severity,"message":message,"blocking":blocking}
    @staticmethod
    def _fingerprint(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
