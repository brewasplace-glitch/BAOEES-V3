from __future__ import annotations
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

class CommissioningHandoverEngine:
    VERSION = "1.0.0"
    SCHEMA_VERSION = "phoenix.commissioning-handover-report/1.0"

    def create_report(self, project_metadata: Mapping[str, Any], *,
                      assets: Sequence[Mapping[str, Any]],
                      commissioning_tests: Sequence[Mapping[str, Any]] = (),
                      punch_items: Sequence[Mapping[str, Any]] = (),
                      handover_documents: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
        project_id = str(project_metadata.get("project_id") or "PHX-UNSPECIFIED")
        issues = []
        asset_ids = self._check_ids(assets, "asset_id", issues, True)
        self._check_ids(commissioning_tests, "test_id", issues, True)
        self._check_ids(punch_items, "punch_id", issues, True)
        self._check_ids(handover_documents, "document_id", issues, False)

        tests_by_asset = {}
        for item in commissioning_tests:
            asset_id = str(item.get("asset_id") or "")
            tests_by_asset.setdefault(asset_id, []).append(item)
            if asset_id not in asset_ids:
                issues.append(self._issue("BB28-TEST-ASSET","error","Commissioning test references unknown asset.",True))

        docs_by_asset = {}
        for item in handover_documents:
            docs_by_asset.setdefault(str(item.get("asset_id") or ""), []).append(item)

        ready_assets = 0
        for asset in assets:
            asset_id = str(asset.get("asset_id") or "")
            test_passed = any(str(x.get("result") or "").lower() == "passed" for x in tests_by_asset.get(asset_id, []))
            as_built = bool(asset.get("as_built_complete"))
            om_ready = any(
                str(x.get("document_type") or "").lower() in {"om_manual","operation_manual","maintenance_manual"}
                and str(x.get("status") or "").lower() in {"approved","released"}
                for x in docs_by_asset.get(asset_id, [])
            )
            if test_passed and as_built and om_ready:
                ready_assets += 1
            else:
                issues.append(self._issue("BB28-ASSET-INCOMPLETE","warning",f"Asset {asset_id} is not handover-ready.",False))

        open_critical = sum(
            1 for x in punch_items
            if str(x.get("status") or "open").lower() not in {"closed","resolved","accepted"}
            and str(x.get("severity") or "minor").lower() in {"major","critical"}
        )
        if open_critical:
            issues.append(self._issue("BB28-PUNCH-CRITICAL","critical",f"{open_critical} major/critical punch item(s) open.",True))
        if assets and ready_assets < len(assets):
            issues.append(self._issue("BB28-HANDOVER-NOT-READY","error","Not all assets meet commissioning and dossier requirements.",True))

        report = {
            "schema_version":self.SCHEMA_VERSION,"engine_version":self.VERSION,"project_id":project_id,
            "asset_count":len(assets),"commissioning_test_count":len(commissioning_tests),
            "handover_document_count":len(handover_documents),"punch_item_count":len(punch_items),
            "ready_asset_count":ready_assets,
            "handover_readiness_percent":round(ready_assets/len(assets)*100,2) if assets else 0.0,
            "open_critical_punch_count":open_critical,"issues":issues,
            "blocking_issue_count":sum(1 for x in issues if x["blocking"]),
            "handover_passed":not any(x["blocking"] for x in issues),
            "metadata":{"non_certifying":True,"human_acceptance_required":True},
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _check_ids(items,key,issues,blocking):
        seen=set()
        for item in items:
            value=str(item.get(key) or "").strip()
            if not value: issues.append({"code":"BB28-ID-MISSING","severity":"error","message":f"Record has no {key}.","blocking":blocking})
            elif value in seen: issues.append({"code":"BB28-ID-DUPLICATE","severity":"error","message":f"Duplicate {key}: {value}.","blocking":blocking})
            seen.add(value)
        return seen
    @staticmethod
    def _issue(code,severity,message,blocking): return {"code":code,"severity":severity,"message":message,"blocking":blocking}
    @staticmethod
    def _fingerprint(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
