"""BB31-BB36 commercial product, security, validation and release gates."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


COMMERCIAL_DELIVERABLES = (
    "3d_impression",
    "structural_calculations",
    "structural_report",
    "building_drawings",
    "technical_specification",
    "specification_drawings",
    "cost_calculation",
    "material_schedules",
    "site_plan",
)

DELIVERABLE_ADAPTERS = {
    "3d_impression": "visualization_adapter",
    "structural_calculations": "structural_adapter",
    "structural_report": "structural_adapter",
    "building_drawings": "drawing_adapter",
    "technical_specification": "specification_adapter",
    "specification_drawings": "drawing_adapter",
    "cost_calculation": "cost_adapter",
    "material_schedules": "quantity_adapter",
    "site_plan": "drawing_adapter",
}


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class CommercialProductShellEngine:
    """BB31 product intake and commercial dashboard contract."""

    VERSION = "1.0.0"

    def create_project(
        self,
        project_metadata: Mapping[str, Any],
        *,
        requested_deliverables: Sequence[str] = COMMERCIAL_DELIVERABLES,
    ) -> dict[str, Any]:
        project_id = str(project_metadata.get("project_id") or "").strip()
        project_name = str(
            project_metadata.get("project_name")
            or project_metadata.get("name")
            or ""
        ).strip()
        issues = []
        if not project_id:
            issues.append(self._issue("BB31-PROJECT-ID", "Project ID is required."))
        if not project_name:
            issues.append(self._issue("BB31-PROJECT-NAME", "Project name is required."))

        requested = []
        for item in requested_deliverables:
            value = str(item).strip()
            if value not in COMMERCIAL_DELIVERABLES:
                issues.append(self._issue(
                    "BB31-DELIVERABLE",
                    f"Unsupported commercial deliverable: {value}.",
                ))
            elif value not in requested:
                requested.append(value)

        if not requested:
            issues.append(self._issue(
                "BB31-EMPTY-SCOPE",
                "At least one commercial deliverable is required.",
            ))

        project = {
            "schema_version": "phoenix.commercial-product-project/1.0",
            "engine_version": self.VERSION,
            "project_id": project_id or "PHX-UNSPECIFIED",
            "project_name": project_name or "Unnamed Project",
            "project_type": str(
                project_metadata.get("project_type") or "building"
            ),
            "location": str(project_metadata.get("location") or ""),
            "jurisdiction": str(project_metadata.get("jurisdiction") or ""),
            "currency": str(project_metadata.get("currency") or "USD").upper(),
            "requested_deliverables": requested,
            "workflow_command": "GENERATE_FULL_BUILDING_DESIGN_PACKAGE",
            "dashboard_sections": [
                "project_intake",
                "design_progress",
                "deliverables",
                "quality_gates",
                "release_readiness",
            ],
            "issues": issues,
            "blocking_issue_count": len(issues),
            "project_shell_passed": not issues,
        }
        project["project_fingerprint_sha256"] = _fingerprint(project)
        return project

    @staticmethod
    def _issue(code: str, message: str) -> dict[str, Any]:
        return {
            "code": code,
            "severity": "error",
            "message": message,
            "blocking": True,
        }


class AutonomousBuildingPackageEngine:
    """BB32 adapter-based autonomous commercial package generator."""

    VERSION = "1.0.0"

    def create_execution_plan(
        self,
        project: Mapping[str, Any],
        *,
        available_inputs: Sequence[str],
    ) -> dict[str, Any]:
        requested = list(project.get("requested_deliverables") or [])
        available = {str(item) for item in available_inputs}
        required_inputs = {"project_brief", "site_information"}
        missing_inputs = sorted(required_inputs - available)

        steps = []
        for index, deliverable in enumerate(requested, start=1):
            adapter = DELIVERABLE_ADAPTERS.get(deliverable)
            steps.append({
                "step_id": f"STEP-{index:02d}",
                "deliverable_type": deliverable,
                "adapter": adapter,
                "status": "planned" if adapter else "blocked",
            })

        issues = []
        if missing_inputs:
            issues.append({
                "code": "BB32-INPUT-MISSING",
                "severity": "error",
                "message": (
                    "Missing required inputs: " + ", ".join(missing_inputs)
                ),
                "blocking": True,
            })
        if any(step["adapter"] is None for step in steps):
            issues.append({
                "code": "BB32-ADAPTER-MISSING",
                "severity": "error",
                "message": "One or more deliverables have no engine adapter.",
                "blocking": True,
            })

        plan = {
            "schema_version": "phoenix.autonomous-building-plan/1.0",
            "engine_version": self.VERSION,
            "project_id": project.get("project_id"),
            "workflow_command": project.get(
                "workflow_command",
                "GENERATE_FULL_BUILDING_DESIGN_PACKAGE",
            ),
            "available_inputs": sorted(available),
            "missing_inputs": missing_inputs,
            "steps": steps,
            "issues": issues,
            "blocking_issue_count": len(issues),
            "execution_plan_passed": not issues,
        }
        plan["plan_fingerprint_sha256"] = _fingerprint(plan)
        return plan

    def execute(
        self,
        plan: Mapping[str, Any],
        *,
        adapters: Mapping[str, Callable[[dict[str, Any]], Any]],
    ) -> dict[str, Any]:
        results = []
        issues = list(plan.get("issues") or [])
        if issues:
            return {
                "project_id": plan.get("project_id"),
                "execution_passed": False,
                "results": [],
                "issues": issues,
            }

        cache = {}
        for step in plan.get("steps", []):
            adapter_name = str(step["adapter"])
            adapter = adapters.get(adapter_name)
            if adapter is None:
                issues.append({
                    "code": "BB32-RUNTIME-ADAPTER",
                    "severity": "error",
                    "message": f"Runtime adapter unavailable: {adapter_name}.",
                    "blocking": True,
                })
                continue

            deliverable = str(step["deliverable_type"])
            cache_key = (adapter_name, deliverable)
            output = adapter({
                "project_id": plan.get("project_id"),
                "deliverable_type": deliverable,
            })
            if output is None:
                issues.append({
                    "code": "BB32-EMPTY-OUTPUT",
                    "severity": "error",
                    "message": f"Adapter returned no output for {deliverable}.",
                    "blocking": True,
                })
                continue
            result = {
                "step_id": step["step_id"],
                "deliverable_type": deliverable,
                "adapter": adapter_name,
                "status": "generated",
                "output": output,
                "output_sha256": _fingerprint(output),
            }
            results.append(result)
            cache[cache_key] = result

        execution = {
            "schema_version": "phoenix.autonomous-building-execution/1.0",
            "engine_version": self.VERSION,
            "project_id": plan.get("project_id"),
            "result_count": len(results),
            "results": results,
            "issues": issues,
            "execution_passed": (
                not any(item.get("blocking") for item in issues)
                and len(results) == len(plan.get("steps", []))
            ),
        }
        execution["execution_fingerprint_sha256"] = _fingerprint(execution)
        return execution


class SecurityDataProtectionEngine:
    """BB33 roles, permissions, integrity evidence and chained audit events."""

    VERSION = "1.0.0"

    ROLE_PERMISSIONS = {
        "administrator": {
            "project:create", "project:read", "project:update", "project:delete",
            "design:run", "design:review", "release:approve", "security:manage",
        },
        "project_manager": {
            "project:create", "project:read", "project:update",
            "design:run", "design:review", "release:approve",
        },
        "designer": {
            "project:read", "project:update", "design:run",
        },
        "engineer": {
            "project:read", "project:update", "design:run", "design:review",
        },
        "estimator": {
            "project:read", "project:update", "design:run",
        },
        "reviewer": {
            "project:read", "design:review",
        },
        "viewer": {
            "project:read",
        },
    }

    def authorize(self, role: str, permission: str) -> bool:
        return permission in self.ROLE_PERMISSIONS.get(role, set())

    def create_integrity_manifest(
        self,
        files: Mapping[str, bytes | str],
    ) -> dict[str, Any]:
        entries = []
        for name, value in sorted(files.items()):
            data = value.encode("utf-8") if isinstance(value, str) else value
            entries.append({
                "file_name": name,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
        manifest = {
            "schema_version": "phoenix.integrity-manifest/1.0",
            "engine_version": self.VERSION,
            "entries": entries,
            "file_count": len(entries),
        }
        manifest["manifest_sha256"] = _fingerprint(manifest)
        return manifest

    def append_audit_event(
        self,
        chain: Sequence[Mapping[str, Any]],
        *,
        actor: str,
        action: str,
        target: str,
        timestamp: str | None = None,
    ) -> list[dict[str, Any]]:
        previous_hash = (
            str(chain[-1]["event_hash"]) if chain else "GENESIS"
        )
        event = {
            "event_index": len(chain) + 1,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target": target,
            "previous_hash": previous_hash,
        }
        event["event_hash"] = _fingerprint(event)
        return [dict(item) for item in chain] + [event]

    @staticmethod
    def verify_audit_chain(chain: Sequence[Mapping[str, Any]]) -> bool:
        previous = "GENESIS"
        for index, event in enumerate(chain, start=1):
            candidate = dict(event)
            event_hash = candidate.pop("event_hash", None)
            if candidate.get("event_index") != index:
                return False
            if candidate.get("previous_hash") != previous:
                return False
            if _fingerprint(candidate) != event_hash:
                return False
            previous = str(event_hash)
        return True

    def create_security_report(
        self,
        *,
        audit_chain: Sequence[Mapping[str, Any]],
        integrity_manifest: Mapping[str, Any],
        backup_tested: bool,
        restore_tested: bool,
    ) -> dict[str, Any]:
        audit_ok = self.verify_audit_chain(audit_chain)
        integrity_ok = bool(
            integrity_manifest.get("file_count", 0) >= 1
            and integrity_manifest.get("manifest_sha256")
        )
        issues = []
        for code, passed, message in (
            ("BB33-AUDIT", audit_ok, "Audit chain verification failed."),
            ("BB33-INTEGRITY", integrity_ok, "Integrity manifest is incomplete."),
            ("BB33-BACKUP", backup_tested, "Backup procedure is not tested."),
            ("BB33-RESTORE", restore_tested, "Restore procedure is not tested."),
        ):
            if not passed:
                issues.append({
                    "code": code,
                    "severity": "critical",
                    "message": message,
                    "blocking": True,
                })
        report = {
            "schema_version": "phoenix.security-readiness/1.0",
            "engine_version": self.VERSION,
            "audit_chain_valid": audit_ok,
            "integrity_manifest_valid": integrity_ok,
            "backup_tested": bool(backup_tested),
            "restore_tested": bool(restore_tested),
            "role_count": len(self.ROLE_PERMISSIONS),
            "issues": issues,
            "blocking_issue_count": len(issues),
            "security_passed": not issues,
        }
        report["report_fingerprint_sha256"] = _fingerprint(report)
        return report


class ReleaseCandidateEngine:
    """BB34 release-candidate and installer/update/rollback readiness gate."""

    VERSION = "1.0.0"

    def create_release_candidate(
        self,
        *,
        version: str,
        component_status: Mapping[str, bool],
        regression_passed: bool,
        clean_install_tested: bool,
        update_tested: bool,
        migration_tested: bool,
        rollback_tested: bool,
        license_policy_present: bool,
        user_guide_present: bool,
    ) -> dict[str, Any]:
        valid_version = bool(re.fullmatch(r"\d+\.\d+\.\d+(?:-rc\.\d+)?", version))
        required_components = {
            "commercial_product_shell",
            "autonomous_building_package",
            "security_data_protection",
            "commercial_delivery_orchestrator",
        }
        missing_components = sorted(
            name for name in required_components
            if not component_status.get(name, False)
        )
        checks = {
            "valid_version": valid_version,
            "regression_passed": bool(regression_passed),
            "clean_install_tested": bool(clean_install_tested),
            "update_tested": bool(update_tested),
            "migration_tested": bool(migration_tested),
            "rollback_tested": bool(rollback_tested),
            "license_policy_present": bool(license_policy_present),
            "user_guide_present": bool(user_guide_present),
            "required_components_passed": not missing_components,
        }
        issues = [
            {
                "code": f"BB34-{name.upper()}",
                "severity": "error",
                "message": f"Release-candidate check failed: {name}.",
                "blocking": True,
            }
            for name, passed in checks.items()
            if not passed
        ]
        report = {
            "schema_version": "phoenix.release-candidate/1.0",
            "engine_version": self.VERSION,
            "version": version,
            "checks": checks,
            "missing_components": missing_components,
            "installer_profile": "windows-powershell-foundation",
            "update_channel": "release-candidate",
            "issues": issues,
            "blocking_issue_count": len(issues),
            "release_candidate_passed": not issues,
        }
        report["report_fingerprint_sha256"] = _fingerprint(report)
        return report


class RealProjectValidationEngine:
    """BB35 evidence gate for real external pilot projects."""

    VERSION = "1.0.0"

    def validate(
        self,
        pilots: Sequence[Mapping[str, Any]],
        *,
        minimum_pilots: int = 2,
    ) -> dict[str, Any]:
        accepted = []
        rejected = []
        for pilot in pilots:
            project_id = str(pilot.get("project_id") or "")
            reasons = []
            if not bool(pilot.get("real_project")):
                reasons.append("not marked as a real project")
            if not str(pilot.get("independent_reviewer") or "").strip():
                reasons.append("independent reviewer missing")
            if not bool(pilot.get("clean_install_tested")):
                reasons.append("clean installation not tested")
            if not bool(pilot.get("reproducibility_passed")):
                reasons.append("reproducibility not passed")
            if not bool(pilot.get("end_to_end_run_passed")):
                reasons.append("end-to-end run not passed")

            deliverables = pilot.get("deliverables")
            if not isinstance(deliverables, Mapping):
                reasons.append("deliverable evidence missing")
            else:
                missing = [
                    name for name in COMMERCIAL_DELIVERABLES
                    if not (
                        isinstance(deliverables.get(name), Mapping)
                        and deliverables[name].get("professional_review_passed")
                        and float(deliverables[name].get("quality_score", 0)) >= 80
                    )
                ]
                if missing:
                    reasons.append(
                        "unapproved/low-score deliverables: " + ", ".join(missing)
                    )

            record = {
                "project_id": project_id or "UNSPECIFIED",
                "accepted": not reasons,
                "reasons": reasons,
            }
            (accepted if not reasons else rejected).append(record)

        passed = len(accepted) >= minimum_pilots
        issues = []
        if not passed:
            issues.append({
                "code": "BB35-PILOTS",
                "severity": "critical",
                "message": (
                    f"Only {len(accepted)} validated real pilot(s); "
                    f"{minimum_pilots} required."
                ),
                "blocking": True,
            })
        report = {
            "schema_version": "phoenix.real-project-validation/1.0",
            "engine_version": self.VERSION,
            "minimum_pilots": minimum_pilots,
            "submitted_pilot_count": len(pilots),
            "accepted_pilot_count": len(accepted),
            "rejected_pilot_count": len(rejected),
            "accepted_pilots": accepted,
            "rejected_pilots": rejected,
            "issues": issues,
            "blocking_issue_count": len(issues),
            "real_project_validation_passed": passed,
        }
        report["report_fingerprint_sha256"] = _fingerprint(report)
        return report


class CommercialReleaseEngine:
    """BB36 production-release gate; never bypasses BB35 evidence."""

    VERSION = "1.0.0"

    def create_release(
        self,
        *,
        version: str,
        release_candidate_report: Mapping[str, Any],
        validation_report: Mapping[str, Any],
        security_report: Mapping[str, Any],
        documentation_available: bool,
        support_plan_available: bool,
        release_requested: bool,
    ) -> dict[str, Any]:
        checks = {
            "release_candidate_passed": bool(
                release_candidate_report.get("release_candidate_passed")
            ),
            "real_project_validation_passed": bool(
                validation_report.get("real_project_validation_passed")
            ),
            "security_passed": bool(security_report.get("security_passed")),
            "documentation_available": bool(documentation_available),
            "support_plan_available": bool(support_plan_available),
            "release_requested": bool(release_requested),
            "production_version": bool(re.fullmatch(r"\d+\.\d+\.\d+", version)),
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            status = "production_release_locked"
        else:
            status = "commercial_production_released"

        report = {
            "schema_version": "phoenix.commercial-production-release/1.0",
            "engine_version": self.VERSION,
            "version": version,
            "status": status,
            "checks": checks,
            "failed_checks": failed,
            "production_release_ready": not failed,
            "tag_name": f"v{version}" if not failed else None,
            "issues": [
                {
                    "code": f"BB36-{name.upper()}",
                    "severity": "critical",
                    "message": f"Production release gate failed: {name}.",
                    "blocking": True,
                }
                for name in failed
            ],
            "blocking_issue_count": len(failed),
        }
        report["release_fingerprint_sha256"] = _fingerprint(report)
        return report


class MasterpackOrchestrator:
    """Integrates BB31-BB36 without falsely completing the real pilot gate."""

    VERSION = "1.0.0"

    def create_framework_report(
        self,
        *,
        shell_report: Mapping[str, Any],
        execution_report: Mapping[str, Any],
        security_report: Mapping[str, Any],
        release_candidate_report: Mapping[str, Any],
        validation_report: Mapping[str, Any],
        production_release_report: Mapping[str, Any],
    ) -> dict[str, Any]:
        blocks = {
            "BB31": bool(shell_report.get("project_shell_passed")),
            "BB32": bool(execution_report.get("execution_passed")),
            "BB33": bool(security_report.get("security_passed")),
            "BB34": bool(release_candidate_report.get("release_candidate_passed")),
            "BB35": bool(validation_report.get("real_project_validation_passed")),
            "BB36": bool(production_release_report.get("production_release_ready")),
        }
        framework_installed = all(blocks[name] for name in ("BB31", "BB32", "BB33", "BB34"))
        report = {
            "schema_version": "phoenix.commercial-release-masterpack/1.0",
            "engine_version": self.VERSION,
            "block_status": blocks,
            "framework_installed": framework_installed,
            "pilot_validation_pending": not blocks["BB35"],
            "production_release_locked": not blocks["BB36"],
            "next_required_action": (
                "Run BB35 with at least two independently reviewed real projects."
                if not blocks["BB35"]
                else "Review and activate BB36 production release."
            ),
            "reports": {
                "bb31": dict(shell_report),
                "bb32": dict(execution_report),
                "bb33": dict(security_report),
                "bb34": dict(release_candidate_report),
                "bb35": dict(validation_report),
                "bb36": dict(production_release_report),
            },
        }
        report["masterpack_fingerprint_sha256"] = _fingerprint(report)
        return report
