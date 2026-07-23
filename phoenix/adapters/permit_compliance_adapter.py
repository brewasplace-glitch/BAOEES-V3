"""Adapter for Phoenix Permit & Compliance Engine Wave 15.8."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from phoenix.permit_compliance import (
    ComplianceRule,
    PermitComplianceEngine,
    PermitProjectContext,
)


ADAPTER_ID = "phoenix.adapter.permit_compliance.wave15_8"
ADAPTER_VERSION = "1.0.0"


def run_permit_compliance(
    request: Mapping[str, Any],
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    context_raw = dict(request["context"])
    context = PermitProjectContext(
        project_id=str(context_raw["project_id"]),
        jurisdiction=str(context_raw["jurisdiction"]),
        permit_type=str(context_raw["permit_type"]),
        digital_twin_revision=int(context_raw.get("digital_twin_revision", 0)),
        human_approval_required=bool(
            context_raw.get("human_approval_required", True)
        ),
    )
    rules = tuple(
        ComplianceRule(
            rule_id=str(item["rule_id"]),
            title=str(item["title"]),
            path=str(item["path"]),
            operator=str(item["operator"]),
            expected=item.get("expected"),
            severity=str(item.get("severity", "error")),
            required=bool(item.get("required", True)),
            standard_reference=str(item.get("standard_reference", "")),
            remediation=str(item.get("remediation", "")),
        )
        for item in request.get("rules", [])
    )
    result = PermitComplianceEngine().evaluate(
        context=context,
        digital_twin=dict(request.get("digital_twin", {})),
        rules=rules,
        rule_set_id=str(request["rule_set_id"]),
        rule_set_version=str(request["rule_set_version"]),
    )
    result["adapter"] = {"id": ADAPTER_ID, "version": ADAPTER_VERSION}

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return result
