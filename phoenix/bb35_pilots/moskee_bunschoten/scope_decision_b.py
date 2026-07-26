"""Validate and report the authoritative Moskee Bunschoten scope decision B."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


class MoskeeScopeDecisionBValidator:
    VERSION = "1.1.0"

    def validate(
        self,
        config: Mapping[str, Any],
        decision_record: Mapping[str, Any],
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        project = config.get("project", {})
        scope = project.get("authoritative_scope", {})
        expected = {
            "selected_option": "B",
            "extension_width_m": 7.0,
            "extension_depth_m": 10.0,
            "extension_footprint_m2": 70.0,
            "number_of_extension_storeys": 2,
            "gross_extension_area_m2": 140.0,
        }

        for key, value in expected.items():
            if scope.get(key) != value:
                issues.append({
                    "code": "HBM-SCOPE-MISMATCH",
                    "severity": "critical",
                    "message": f"Authoritative scope mismatch for {key}.",
                    "blocking": True,
                })

        decisions = {
            item.get("decision_id"): item
            for item in config.get("strategic_decisions", [])
        }
        main_decision = decisions.get("HBM-SCOPE-001", {})
        if (
            main_decision.get("selected_option") != "B"
            or main_decision.get("status") != "resolved"
        ):
            issues.append({
                "code": "HBM-DECISION-NOT-RESOLVED",
                "severity": "critical",
                "message": "HBM-SCOPE-001 is not resolved as option B.",
                "blocking": True,
            })

        scope_conflict = next(
            (
                item
                for item in config.get("verified_conflicts", [])
                if item.get("conflict_id") == "HBM-CONFLICT-001"
            ),
            {},
        )
        if scope_conflict.get("status") != "resolved":
            issues.append({
                "code": "HBM-CONFLICT-STILL-OPEN",
                "severity": "critical",
                "message": "The 20 m² versus 140 m² conflict remains open.",
                "blocking": True,
            })

        propagation = config.get("mandatory_propagation", {})
        required_modules = {
            "building_model",
            "architectural_drawings",
            "structural_design",
            "quantity_takeoff",
            "cost_estimation",
            "permit_and_bopa",
            "parking_and_traffic",
            "aerius",
            "technical_specification",
            "material_schedules",
            "site_plan",
        }
        actual_modules = set(propagation.get("modules", []))
        missing_modules = sorted(required_modules - actual_modules)
        if missing_modules:
            issues.append({
                "code": "HBM-PROPAGATION-INCOMPLETE",
                "severity": "critical",
                "message": (
                    "Scope propagation is missing modules: "
                    + ", ".join(missing_modules)
                ),
                "blocking": True,
            })

        missing_inputs = [
            item
            for item in config.get("required_input_evidence", [])
            if str(item.get("status") or "missing").lower()
            not in {"available", "verified", "accepted"}
            and bool(item.get("blocking", True))
        ]

        decision_valid = not any(
            issue["blocking"] for issue in issues
        )
        result = {
            "schema_version": "phoenix.bb35.scope-decision-validation/1.0",
            "validator_version": self.VERSION,
            "pilot_id": config.get("pilot_id"),
            "project_id": project.get("project_id"),
            "scope_decision": "B",
            "scope_decision_valid": decision_valid,
            "authoritative_scope": dict(scope),
            "superseded_scope": "approximately 20 m²",
            "mandatory_module_count": len(actual_modules),
            "missing_blocking_input_count": len(missing_inputs),
            "pilot_status": (
                "BLOCKED_PENDING_INPUTS"
                if decision_valid and missing_inputs
                else (
                    "READY_FOR_FULL_PILOT_GENERATION"
                    if decision_valid
                    else "INVALID_SCOPE_DECISION"
                )
            ),
            "bb36_unlock_allowed": False,
            "issues": issues,
            "decision_record_sha256": self._fingerprint(
                decision_record
            ),
        }
        result["report_fingerprint_sha256"] = self._fingerprint(
            result
        )
        return result

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
