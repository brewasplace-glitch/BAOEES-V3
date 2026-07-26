from __future__ import annotations
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

class ContractAdministrationEngine:
    VERSION = "1.0.0"
    SCHEMA_VERSION = "phoenix.contract-administration-report/1.0"

    def create_report(self, project_metadata: Mapping[str, Any], *,
                      contracts: Sequence[Mapping[str, Any]],
                      variations: Sequence[Mapping[str, Any]] = (),
                      payments: Sequence[Mapping[str, Any]] = (),
                      rfis: Sequence[Mapping[str, Any]] = (),
                      submittals: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
        project_id = str(project_metadata.get("project_id") or "PHX-UNSPECIFIED")
        issues: list[dict[str, Any]] = []
        for items, key, blocking in (
            (contracts, "contract_id", True), (variations, "variation_id", True),
            (payments, "payment_id", True), (rfis, "rfi_id", False),
            (submittals, "submittal_id", False),
        ):
            self._check_ids(items, key, issues, blocking)

        contract_ids = {str(x.get("contract_id")) for x in contracts if x.get("contract_id")}
        contract_sum = sum(self._amount(x.get("awarded_amount"), "contract", issues) for x in contracts)
        approved = pending = 0.0
        for item in variations:
            if str(item.get("contract_id") or "") not in contract_ids:
                issues.append(self._issue("BB26-VAR-REF", "error", "Variation references unknown contract.", True))
            amount = self._amount(item.get("amount"), "variation", issues)
            if str(item.get("status") or "").lower() == "approved":
                approved += amount
            else:
                pending += amount

        certified = 0.0
        for item in payments:
            if str(item.get("contract_id") or "") not in contract_ids:
                issues.append(self._issue("BB26-PAY-REF", "error", "Payment references unknown contract.", True))
            certified += self._amount(item.get("certified_amount"), "payment", issues)

        forecast = round(contract_sum + approved + pending, 2)
        if certified > forecast:
            issues.append(self._issue("BB26-PAY-OVER", "critical", "Certified payments exceed forecast final cost.", True))

        overdue_submittals = sum(
            1 for x in submittals
            if bool(x.get("overdue")) and str(x.get("status") or "").lower() not in {"approved", "closed"}
        )
        if overdue_submittals:
            issues.append(self._issue("BB26-SUB-OVERDUE", "warning", f"{overdue_submittals} submittal(s) overdue.", False))

        report = {
            "schema_version": self.SCHEMA_VERSION, "engine_version": self.VERSION,
            "project_id": project_id, "contract_count": len(contracts),
            "contract_sum": round(contract_sum, 2), "approved_variations": round(approved, 2),
            "pending_variations": round(pending, 2), "forecast_final_cost": forecast,
            "certified_payments": round(certified, 2),
            "remaining_to_certify": round(forecast - certified, 2),
            "open_rfi_count": sum(1 for x in rfis if str(x.get("status") or "open").lower() not in {"closed", "answered"}),
            "overdue_submittal_count": overdue_submittals, "issues": issues,
            "blocking_issue_count": sum(1 for x in issues if x["blocking"]),
            "contract_control_passed": not any(x["blocking"] for x in issues),
            "metadata": {"non_certifying": True, "automatic_payment_approval": False, "automatic_variation_approval": False},
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _check_ids(items, key, issues, blocking):
        seen = set()
        for item in items:
            value = str(item.get(key) or "").strip()
            if not value:
                issues.append({"code":"BB26-ID-MISSING","severity":"error","message":f"Record has no {key}.","blocking":blocking})
            elif value in seen:
                issues.append({"code":"BB26-ID-DUPLICATE","severity":"error","message":f"Duplicate {key}: {value}.","blocking":blocking})
            seen.add(value)

    @staticmethod
    def _amount(value, label, issues):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) < 0:
            issues.append({"code":"BB26-AMOUNT","severity":"error","message":f"Invalid {label} amount.","blocking":True})
            return 0.0
        return float(value)

    @staticmethod
    def _issue(code, severity, message, blocking):
        return {"code":code,"severity":severity,"message":message,"blocking":blocking}

    @staticmethod
    def _fingerprint(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",",":")).encode()).hexdigest()
