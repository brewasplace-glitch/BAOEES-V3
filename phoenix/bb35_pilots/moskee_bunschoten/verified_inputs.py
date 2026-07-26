"""BB35 Moskee Bunschoten verified-input gate and downstream readiness."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class MoskeeBunschotenVerifiedInputsGate:
    VERSION = "1.2.0"
    SCHEMA_VERSION = "phoenix.bb35.moskee-verified-inputs/1.0"

    def evaluate(
        self,
        *,
        config: Mapping[str, Any],
        register: Mapping[str, Any],
        baseline_manifest: Mapping[str, Any],
        baseline_evidence_root: str | Path,
        administrative_manifest: Mapping[str, Any],
        administrative_evidence_root: str | Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        baseline_evidence = self._validate_manifest(
            baseline_manifest,
            Path(baseline_evidence_root),
            "baseline",
            issues,
        )
        administrative_evidence = self._validate_manifest(
            administrative_manifest,
            Path(administrative_evidence_root),
            "administrative",
            issues,
        )
        evidence_results = baseline_evidence + administrative_evidence

        scope = config.get("project", {}).get(
            "authoritative_scope", {}
        )
        expected_scope = {
            "selected_option": "B",
            "extension_width_m": 7.0,
            "extension_depth_m": 10.0,
            "extension_footprint_m2": 70.0,
            "number_of_extension_storeys": 2,
            "gross_extension_area_m2": 140.0,
        }
        for key, expected in expected_scope.items():
            if scope.get(key) != expected:
                issues.append(self._issue(
                    "HBM-VI-SCOPE",
                    "critical",
                    f"Authoritative scope mismatch for {key}.",
                    True,
                    key,
                ))

        verified_facts: list[dict[str, Any]] = []
        pending_inputs: list[dict[str, Any]] = []
        for record in register.get("inputs", []):
            item = dict(record)
            status = str(item.get("status") or "missing")
            if status in {
                "verified",
                "verified_preliminary",
                "accepted_authoritative",
            }:
                verified_facts.append(item)
            else:
                pending_inputs.append(item)
                if bool(item.get("blocking", True)):
                    issues.append(self._issue(
                        "HBM-VI-PENDING",
                        str(item.get("severity") or "error"),
                        str(item["description"]),
                        True,
                        str(item["input_id"]),
                    ))

        invalid_evidence = [
            item
            for item in evidence_results
            if not item["sha256_valid"]
        ]

        downstream = self._downstream_readiness(
            pending_inputs=pending_inputs,
        )

        if invalid_evidence:
            status = "INVALID_EVIDENCE"
        elif any(
            issue["code"] == "HBM-VI-SCOPE"
            for issue in issues
        ):
            status = "INVALID_AUTHORITATIVE_SCOPE"
        elif any(item["blocking"] for item in pending_inputs):
            status = (
                "BLOCKED_PENDING_EXTERNAL_TECHNICAL_EVIDENCE"
            )
        else:
            status = "READY_FOR_FULL_PILOT_GENERATION"

        report = {
            "schema_version": self.SCHEMA_VERSION,
            "engine_version": self.VERSION,
            "pilot_id": config["pilot_id"],
            "project_id": config["project"]["project_id"],
            "project_name": config["project"]["project_name"],
            "project_address": config["project"]["address"],
            "authoritative_scope": dict(scope),
            "status": status,
            "verified_inputs_gate_passed": (
                status == "READY_FOR_FULL_PILOT_GENERATION"
            ),
            "concept_generation_allowed": (
                status
                == "BLOCKED_PENDING_EXTERNAL_TECHNICAL_EVIDENCE"
            ),
            "final_generation_allowed": (
                status == "READY_FOR_FULL_PILOT_GENERATION"
            ),
            "pilot_completed": False,
            "bb36_unlock_allowed": False,
            "baseline_evidence_count": len(baseline_evidence),
            "administrative_evidence_count": len(
                administrative_evidence
            ),
            "evidence_count": len(evidence_results),
            "valid_evidence_count": sum(
                1 for item in evidence_results
                if item["sha256_valid"]
            ),
            "verified_fact_count": len(verified_facts),
            "pending_input_count": len(pending_inputs),
            "blocking_pending_input_count": sum(
                1 for item in pending_inputs
                if item["blocking"]
            ),
            "verified_facts": verified_facts,
            "pending_inputs": pending_inputs,
            "downstream_readiness": downstream,
            "evidence_results": evidence_results,
            "issues": issues,
            "next_gate": (
                "Collect or commission the external technical evidence "
                "listed in the pending-input register. Concept generation "
                "may proceed, but final structural, permit, parking, AERIUS, "
                "cost and specification outputs remain blocked."
            ),
            "metadata": {
                "real_project_evidence": True,
                "synthetic_completion_evidence": False,
                "scope_20m2_superseded": True,
                "professional_verification_required": True,
                "production_release_locked": True,
            },
        }
        report["report_fingerprint_sha256"] = (
            self._fingerprint(report)
        )
        return report

    def _validate_manifest(
        self,
        manifest: Mapping[str, Any],
        root: Path,
        evidence_class: str,
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for record in manifest.get("files", []):
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
            result = {
                "evidence_id": record["evidence_id"],
                "evidence_class": evidence_class,
                "relative_path": relative_path,
                "file_name": path.name,
                "role": record["role"],
                "available": available,
                "sha256_valid": valid,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
            }
            results.append(result)
            if not available:
                issues.append(self._issue(
                    "HBM-VI-EVIDENCE-MISSING",
                    "critical",
                    f"Evidence file is missing: {relative_path}.",
                    True,
                    str(record["evidence_id"]),
                ))
            elif not valid:
                issues.append(self._issue(
                    "HBM-VI-EVIDENCE-HASH",
                    "critical",
                    f"Evidence hash mismatch: {relative_path}.",
                    True,
                    str(record["evidence_id"]),
                ))
        return results

    @staticmethod
    def _downstream_readiness(
        *,
        pending_inputs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        missing_ids = {
            str(item["input_id"])
            for item in pending_inputs
            if item.get("blocking", True)
        }
        requirements = {
            "building_model": {
                "required": {"HBM-VI-101", "HBM-VI-102"},
                "concept_allowed": True,
            },
            "architectural_drawings": {
                "required": {"HBM-VI-101", "HBM-VI-102", "HBM-VI-105"},
                "concept_allowed": True,
            },
            "structural_design": {
                "required": {"HBM-VI-101", "HBM-VI-103", "HBM-VI-104"},
                "concept_allowed": False,
            },
            "permit_and_bopa": {
                "required": {
                    "HBM-VI-101",
                    "HBM-VI-102",
                    "HBM-VI-105",
                    "HBM-VI-106",
                    "HBM-VI-107",
                    "HBM-VI-108",
                },
                "concept_allowed": True,
            },
            "parking_and_traffic": {
                "required": {"HBM-VI-106", "HBM-VI-107"},
                "concept_allowed": True,
            },
            "aerius": {
                "required": {"HBM-VI-107", "HBM-VI-108"},
                "concept_allowed": False,
            },
            "quantity_takeoff": {
                "required": {"HBM-VI-101", "HBM-VI-105"},
                "concept_allowed": True,
            },
            "cost_estimation": {
                "required": {"HBM-VI-101", "HBM-VI-105"},
                "concept_allowed": True,
            },
            "technical_specification": {
                "required": {"HBM-VI-103", "HBM-VI-105"},
                "concept_allowed": False,
            },
            "material_schedules": {
                "required": {"HBM-VI-103", "HBM-VI-105"},
                "concept_allowed": False,
            },
            "site_plan": {
                "required": {"HBM-VI-102"},
                "concept_allowed": True,
            },
        }
        result: list[dict[str, Any]] = []
        for module, rule in requirements.items():
            blockers = sorted(rule["required"] & missing_ids)
            result.append({
                "module": module,
                "final_ready": not blockers,
                "concept_allowed": bool(rule["concept_allowed"]),
                "blocking_input_ids": blockers,
            })
        return sorted(result, key=lambda item: item["module"])

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
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
