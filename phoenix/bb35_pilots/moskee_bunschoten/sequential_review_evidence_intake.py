"""Integrated validation after sequential review and evidence intake."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SequentialReviewEvidenceIntakeValidator:
    VERSION = "1.4.2"

    def validate(self, repository_root: str | Path) -> dict[str, Any]:
        root = Path(repository_root)

        required = {
            "project_config": (
                root
                / "configs/projects/"
                "moskee_bunschoten_bb35_pilot_1.json"
            ),
            "concept_manifest": (
                root
                / "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "concept_generation_v1_3_3/"
                "concept_package_manifest.json"
            ),
            "review_summary": (
                root
                / "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "concept_review_evidence_acquisition_v1_4_0/"
                "01_concept_review_summary.json"
            ),
            "intake_report": (
                root
                / "artifacts/bb35/pilot_1_moskee_bunschoten/"
                "uploaded_evidence_intake_v1_4_1/"
                "01_uploaded_evidence_intake_report.json"
            ),
        }

        missing = [
            key for key, path in required.items() if not path.is_file()
        ]
        if missing:
            return {
                "schema_version": (
                    "phoenix.bb35.sequential-review-intake/1.0"
                ),
                "validator_version": self.VERSION,
                "status": "FAILED_MISSING_COMPONENTS",
                "missing": missing,
                "final_generation_allowed": False,
                "bb36_unlock_allowed": False,
            }

        config = json.loads(
            required["project_config"].read_text(encoding="utf-8")
        )
        concept = json.loads(
            required["concept_manifest"].read_text(encoding="utf-8")
        )
        review = json.loads(
            required["review_summary"].read_text(encoding="utf-8")
        )
        intake = json.loads(
            required["intake_report"].read_text(encoding="utf-8")
        )

        scope = config["project"]["authoritative_scope"]
        checks = {
            "scope_option_b": scope.get("selected_option") == "B",
            "scope_7_by_10": (
                float(scope.get("extension_width_m", 0)) == 7.0
                and float(scope.get("extension_depth_m", 0)) == 10.0
            ),
            "scope_two_storeys": (
                int(scope.get("number_of_extension_storeys", 0)) == 2
            ),
            "scope_140m2": (
                float(scope.get("gross_extension_area_m2", 0))
                == 140.0
            ),
            "concept_v1_3_3": (
                concept.get("generator_version") == "1.3.3"
            ),
            "review_complete": bool(
                review.get("concept_review_complete")
            ),
            "review_accepted_with_conditions": bool(
                review.get(
                    "concept_package_accepted_with_conditions"
                )
            ),
            "review_eight_requests": (
                int(review.get("evidence_request_count", 0)) == 8
            ),
            "intake_six_valid": (
                int(intake.get("valid_file_count", 0)) == 6
            ),
            "intake_one_closed": (
                int(intake.get("closed_request_count", 0)) == 1
            ),
            "intake_two_partial": (
                int(intake.get("partial_request_count", 0)) == 2
            ),
            "intake_five_open": (
                int(intake.get("open_request_count", 0)) == 5
            ),
            "seven_blockers_remain": (
                int(
                    intake.get(
                        "remaining_blocking_input_count",
                        0,
                    )
                )
                == 7
            ),
            "final_generation_blocked": (
                not bool(intake.get("final_generation_allowed"))
            ),
            "bb36_locked": (
                not bool(intake.get("bb36_unlock_allowed"))
            ),
        }

        passed = all(checks.values())
        result = {
            "schema_version": (
                "phoenix.bb35.sequential-review-intake/1.0"
            ),
            "validator_version": self.VERSION,
            "status": (
                "REVIEW_COMPLETE_EVIDENCE_INTAKE_PARTIALLY_SATISFIED"
                if passed
                else "FAILED_INTEGRATED_VALIDATION"
            ),
            "checks": checks,
            "authoritative_scope": {
                "width_m": 7.0,
                "depth_m": 10.0,
                "storeys": 2,
                "gross_extension_area_m2": 140.0,
            },
            "review_status": review.get("status"),
            "intake_status": intake.get("status"),
            "valid_uploaded_evidence_count": int(
                intake.get("valid_file_count", 0)
            ),
            "evidence_requests": {
                "closed": int(intake.get("closed_request_count", 0)),
                "partial": int(intake.get("partial_request_count", 0)),
                "open": int(intake.get("open_request_count", 0)),
            },
            "remaining_blocking_input_count": int(
                intake.get("remaining_blocking_input_count", 0)
            ),
            "final_generation_allowed": False,
            "bb36_unlock_allowed": False,
        }
        result["fingerprint_sha256"] = self._fingerprint(result)
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
