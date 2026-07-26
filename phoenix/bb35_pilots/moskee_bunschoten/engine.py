"""Evidence-based BB35 baseline validation for Moskee Bunschoten."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class MoskeeBunschotenPilotEngine:
    VERSION = "1.0.0"
    SCHEMA_VERSION = "phoenix.bb35.moskee-bunschoten-pilot/1.0"

    def evaluate(
        self,
        *,
        config: Mapping[str, Any],
        evidence_manifest: Mapping[str, Any],
        evidence_root: str | Path,
    ) -> dict[str, Any]:
        root = Path(evidence_root)
        issues: list[dict[str, Any]] = []
        evidence_results: list[dict[str, Any]] = []

        for record in evidence_manifest.get("files", []):
            relative_path = str(record["relative_path"])
            path = root / relative_path
            available = path.is_file()
            actual_hash = (
                hashlib.sha256(path.read_bytes()).hexdigest()
                if available
                else ""
            )
            expected_hash = str(record["sha256"])
            valid = available and actual_hash == expected_hash
            evidence_results.append({
                "evidence_id": record["evidence_id"],
                "file_name": path.name,
                "relative_path": relative_path,
                "role": record["role"],
                "available": available,
                "sha256_valid": valid,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
            })
            if not available:
                issues.append(self._issue(
                    "BB35-EVIDENCE-MISSING",
                    "critical",
                    f"Evidence file is missing: {relative_path}.",
                    True,
                    record["evidence_id"],
                ))
            elif not valid:
                issues.append(self._issue(
                    "BB35-EVIDENCE-HASH",
                    "critical",
                    f"Evidence hash mismatch: {relative_path}.",
                    True,
                    record["evidence_id"],
                ))

        decisions = list(config.get("strategic_decisions", []))
        unresolved_decisions = [
            item for item in decisions
            if not item.get("selected_option")
        ]
        for decision in unresolved_decisions:
            issues.append(self._issue(
                "BB35-DECISION-REQUIRED",
                "critical",
                str(decision["question"]),
                True,
                str(decision["decision_id"]),
            ))

        conflicts = list(config.get("verified_conflicts", []))
        unresolved_conflicts = [
            conflict for conflict in conflicts
            if str(conflict.get("status") or "open").lower() != "resolved"
        ]
        for conflict in unresolved_conflicts:
            issues.append(self._issue(
                "BB35-INPUT-CONFLICT",
                str(conflict.get("severity") or "critical"),
                str(conflict["description"]),
                bool(conflict.get("blocking", True)),
                str(conflict["conflict_id"]),
            ))

        input_requirements = list(config.get("required_input_evidence", []))
        missing_inputs = [
            item for item in input_requirements
            if str(item.get("status") or "missing").lower()
            not in {"available", "verified", "accepted"}
        ]
        for item in missing_inputs:
            issues.append(self._issue(
                "BB35-INPUT-MISSING",
                str(item.get("severity") or "error"),
                str(item["description"]),
                bool(item.get("blocking", True)),
                str(item["input_id"]),
            ))

        deliverable_results: list[dict[str, Any]] = []
        for deliverable in config.get("commercial_deliverables", []):
            readiness = str(deliverable.get("readiness") or "missing")
            ready = readiness == "ready"
            deliverable_results.append({
                "deliverable_id": deliverable["deliverable_id"],
                "name": deliverable["name"],
                "readiness": readiness,
                "available_evidence": list(
                    deliverable.get("available_evidence", [])
                ),
                "remaining_work": list(
                    deliverable.get("remaining_work", [])
                ),
                "ready": ready,
            })

        all_hashes_valid = all(
            item["sha256_valid"] for item in evidence_results
        )
        blocking_count = sum(
            1 for issue in issues if issue["blocking"]
        )

        if not all_hashes_valid:
            status = "INVALID_EVIDENCE"
        elif unresolved_decisions:
            status = "BLOCKED_PENDING_STRATEGIC_DECISION"
        elif blocking_count:
            status = "BLOCKED_PENDING_INPUTS"
        elif all(item["ready"] for item in deliverable_results):
            status = "READY_FOR_INDEPENDENT_ACCEPTANCE"
        else:
            status = "READY_FOR_FULL_PILOT_GENERATION"

        report = {
            "schema_version": self.SCHEMA_VERSION,
            "engine_version": self.VERSION,
            "pilot_id": config["pilot_id"],
            "pilot_name": config["pilot_name"],
            "project_id": config["project"]["project_id"],
            "project_name": config["project"]["project_name"],
            "project_address": config["project"]["address"],
            "architect": config["project"]["architect"],
            "status": status,
            "pilot_started": True,
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "source_evidence_count": len(evidence_results),
            "source_evidence_valid_count": sum(
                1 for item in evidence_results
                if item["sha256_valid"]
            ),
            "strategic_decision_count": len(decisions),
            "unresolved_strategic_decision_count": len(
                unresolved_decisions
            ),
            "verified_conflict_count": len(conflicts),
            "unresolved_conflict_count": len(unresolved_conflicts),
            "required_input_count": len(input_requirements),
            "missing_input_count": len(missing_inputs),
            "commercial_deliverable_count": len(deliverable_results),
            "ready_deliverable_count": sum(
                1 for item in deliverable_results if item["ready"]
            ),
            "blocking_issue_count": blocking_count,
            "evidence_results": evidence_results,
            "strategic_decisions": decisions,
            "verified_conflicts": conflicts,
            "required_input_evidence": input_requirements,
            "commercial_deliverables": deliverable_results,
            "issues": issues,
            "next_gate": (
                "Resolve the authoritative expansion scope before model, "
                "structural, cost, specification and permit generation."
            ),
            "metadata": {
                "real_project_evidence": True,
                "synthetic_pilot": False,
                "production_release_locked": True,
                "professional_review_required": True,
            },
        }
        report["report_fingerprint_sha256"] = self._fingerprint(report)
        return report

    @staticmethod
    def _issue(
        code: str,
        severity: str,
        message: str,
        blocking: bool,
        source: str,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "blocking": blocking,
            "source": source,
        }

    @staticmethod
    def _fingerprint(value: Any) -> str:
        data = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
