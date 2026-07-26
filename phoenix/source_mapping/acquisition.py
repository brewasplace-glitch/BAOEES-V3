"""Controlled acquisition-plan generation for BB17.3.

This module deliberately does not perform network downloads. It produces
reviewable tasks that a later controlled connector or installer can execute.
"""

from __future__ import annotations

import hashlib

from .models import (
    AcquisitionAction,
    AcquisitionTask,
    RightsClass,
    SourceCatalog,
    SourceStatus,
)


class SourceAcquisitionPlanner:
    VERSION = "1.0.0"

    def create_plan(
        self,
        catalog: SourceCatalog,
    ) -> tuple[AcquisitionTask, ...]:
        tasks: list[AcquisitionTask] = []
        for source in catalog.sources:
            if source.status in (
                SourceStatus.SUPERSEDED,
                SourceStatus.WITHDRAWN,
            ):
                continue

            if source.status == SourceStatus.DISCOVERED:
                action = AcquisitionAction.VERIFY_METADATA
                reason = "Source metadata and authority must be verified."
                priority = "high" if source.required else "normal"
            elif source.rights_class == RightsClass.PUBLIC_TEXT:
                action = AcquisitionAction.CHANGE_CHECK
                reason = "Verified public source requires change detection."
                priority = "normal"
            elif source.rights_class == RightsClass.RESTRICTED:
                action = AcquisitionAction.MANUAL_REVIEW
                reason = "Restricted source requires licensed manual review."
                priority = "normal"
            else:
                action = AcquisitionAction.CHANGE_CHECK
                reason = "Metadata-only source requires metadata change detection."
                priority = "normal"

            tasks.append(
                AcquisitionTask(
                    id=self._task_id(catalog.id, source.id, action.value),
                    jurisdiction_id=catalog.jurisdiction_id,
                    source_id=source.id,
                    action=action,
                    priority=priority,
                    automatic_execution=False,
                    reason=reason,
                    canonical_uri=source.canonical_uri,
                )
            )

            if (
                source.status == SourceStatus.VERIFIED
                and source.rights_class == RightsClass.PUBLIC_TEXT
                and source.content_storage_policy == "public_snapshot_after_review"
                and not source.snapshot_sha256
            ):
                tasks.append(
                    AcquisitionTask(
                        id=self._task_id(
                            catalog.id,
                            source.id,
                            AcquisitionAction.SNAPSHOT_PUBLIC_DOCUMENT.value,
                        ),
                        jurisdiction_id=catalog.jurisdiction_id,
                        source_id=source.id,
                        action=AcquisitionAction.SNAPSHOT_PUBLIC_DOCUMENT,
                        priority="normal",
                        automatic_execution=False,
                        reason=(
                            "A reviewed public source may receive a checksum-locked "
                            "snapshot after explicit approval."
                        ),
                        canonical_uri=source.canonical_uri,
                    )
                )

        return tuple(tasks)

    @staticmethod
    def _task_id(catalog_id: str, source_id: str, action: str) -> str:
        digest = hashlib.sha256(
            f"{catalog_id}|{source_id}|{action}".encode("utf-8")
        ).hexdigest()[:20].upper()
        return f"SRC-TASK-{digest}"
