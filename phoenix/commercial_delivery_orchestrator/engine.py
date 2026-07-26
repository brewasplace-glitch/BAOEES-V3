from __future__ import annotations
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

REQUIRED_UPSTREAM = (
    "building_model","architectural_drawings","structural_design","quantity_takeoff",
    "cost_estimation","bim_coordination","construction_documentation",
    "construction_planning","procurement_tendering","contract_administration",
    "site_qaqc","commissioning_handover","digital_twin_operations",
)
REQUIRED_DELIVERABLES = (
    "3d_impression","structural_calculations","structural_report","building_drawings",
    "technical_specification","specification_drawings","cost_calculation",
    "material_schedules","site_plan",
)

class CommercialDeliveryOrchestrator:
    VERSION = "1.0.0"
    SCHEMA_VERSION = "phoenix.commercial-building-delivery/1.0"

    def create_delivery_manifest(self, project_metadata: Mapping[str, Any], *,
                                 upstream_reports: Mapping[str, Mapping[str, Any]],
                                 deliverables: Sequence[Mapping[str, Any]],
                                 release_requested: bool=False) -> dict[str, Any]:
        project_id=str(project_metadata.get("project_id") or "PHX-UNSPECIFIED")
        project_name=str(project_metadata.get("project_name") or project_metadata.get("name") or project_id)
        issues=[]; upstream_status=[]
        for name in REQUIRED_UPSTREAM:
            report=upstream_reports.get(name)
            if not isinstance(report,Mapping):
                issues.append(self._issue("BB30-UPSTREAM-MISSING","critical",f"Missing upstream report: {name}.",True,name))
                upstream_status.append({"source":name,"available":False,"passed":False,"fingerprint_sha256":""})
                continue
            if report.get("project_id") and str(report.get("project_id")) != project_id:
                issues.append(self._issue("BB30-PROJECT-MISMATCH","critical",
                                          f"{name} belongs to {report.get('project_id')}, not {project_id}.",True,name))
            passed=self._report_passed(report)
            if not passed:
                issues.append(self._issue("BB30-UPSTREAM-BLOCKED","error",f"Upstream source has not passed: {name}.",True,name))
            upstream_status.append({"source":name,"available":True,"passed":passed,
                                    "fingerprint_sha256":self._fingerprint(report)})

        by_type={}; seen_ids=set()
        for item in deliverables:
            deliverable_id=str(item.get("deliverable_id") or "").strip()
            deliverable_type=str(item.get("deliverable_type") or "").strip()
            if not deliverable_id or not deliverable_type:
                issues.append(self._issue("BB30-DELIVERABLE-ID","error",
                                          "Deliverable requires ID and type.",True,deliverable_type or "unknown"))
                continue
            if deliverable_id in seen_ids:
                issues.append(self._issue("BB30-DELIVERABLE-DUP","error",
                                          f"Duplicate deliverable ID: {deliverable_id}.",True,deliverable_type))
            seen_ids.add(deliverable_id); by_type.setdefault(deliverable_type,item)

        checklist=[]
        for deliverable_type in REQUIRED_DELIVERABLES:
            item=by_type.get(deliverable_type)
            if item is None:
                issues.append(self._issue("BB30-DELIVERABLE-MISSING","critical",
                                          f"Missing commercial deliverable: {deliverable_type}.",True,deliverable_type))
                checklist.append({"deliverable_type":deliverable_type,"available":False,"released":False,
                                  "revision":"","file_name":"","sha256":""})
                continue
            status=str(item.get("status") or "").lower()
            digest=str(item.get("sha256") or "").lower().strip()
            released=status=="released"
            valid_hash=len(digest)==64 and all(c in "0123456789abcdef" for c in digest)
            if not released:
                issues.append(self._issue("BB30-DELIVERABLE-STATUS","error",
                                          f"{deliverable_type} is not released.",True,deliverable_type))
            if not valid_hash:
                issues.append(self._issue("BB30-DELIVERABLE-HASH","error",
                                          f"{deliverable_type} lacks valid SHA-256 evidence.",True,deliverable_type))
            checklist.append({"deliverable_type":deliverable_type,"available":True,"released":released,
                              "revision":str(item.get("revision") or ""),
                              "file_name":str(item.get("file_name") or ""),"sha256":digest})

        blocking=any(x["blocking"] for x in issues)
        status="blocked" if blocking else ("released_for_commercial_pilot" if release_requested else "ready_for_review")
        manifest={
            "schema_version":self.SCHEMA_VERSION,"engine_version":self.VERSION,
            "project_id":project_id,"project_name":project_name,"release_status":status,
            "release_requested":bool(release_requested),"commercial_package_ready":not blocking,
            "upstream_status":sorted(upstream_status,key=lambda x:x["source"]),
            "deliverable_checklist":checklist,"deliverable_count":len(deliverables),
            "required_deliverable_count":len(REQUIRED_DELIVERABLES),
            "blocking_issue_count":sum(1 for x in issues if x["blocking"]),"issues":issues,
            "metadata":{
                "commercial_scope":[
                    "3D impression","structural calculations","structural report",
                    "building drawings","technical specification","specification drawings",
                    "cost calculation","material schedules","site plan",
                ],
                "pilot_release_only":True,"professional_review_required":True,
                "final_product_release_requires_bb31_bb36":True,
            },
        }
        manifest["manifest_fingerprint_sha256"]=self._fingerprint(manifest)
        return manifest

    @staticmethod
    def _report_passed(report):
        keys=("coordination_passed","planning_passed","procurement_passed",
              "contract_control_passed","site_quality_passed","handover_passed",
              "operations_ready","release_ready","passed")
        found=False; result=True
        for key in keys:
            if key in report:
                found=True; result=result and bool(report[key])
        if "blocking_issue_count" in report:
            found=True; result=result and int(report["blocking_issue_count"])==0
        return result if found else True

    @staticmethod
    def _issue(code,severity,message,blocking,source):
        return {"code":code,"severity":severity,"message":message,"blocking":blocking,"source":source}
    @staticmethod
    def _fingerprint(value):
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
