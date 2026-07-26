"""Governance decisions for Phoenix codepacks."""

from __future__ import annotations

from datetime import date, datetime, timezone

from .models import (
    ActivationDecision,
    ActivationState,
    CodepackManifest,
    ReviewStatus,
    SourceStatus,
)


class CodepackGovernanceEngine:
    VERSION = "1.0.0"

    def activation_decision(
        self,
        manifest: CodepackManifest,
        *,
        as_of_date: str | None = None,
    ) -> ActivationDecision:
        evaluation_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
        reasons: list[str] = []

        if manifest.review_status != ReviewStatus.VALIDATED:
            reasons.append("Codepack review status is not validated.")
        if not manifest.reviewed_by or not manifest.reviewed_at:
            reasons.append("Independent review evidence is incomplete.")
        if manifest.activation_state in (
            ActivationState.SUPERSEDED,
            ActivationState.WITHDRAWN,
        ):
            reasons.append(
                f"Codepack activation state is {manifest.activation_state.value}."
            )
        if manifest.regulatory_claim and not manifest.sources:
            reasons.append("Regulatory codepack has no official source metadata.")

        for source in manifest.sources:
            if manifest.regulatory_claim and source.source_status != SourceStatus.VERIFIED:
                reasons.append(f"Source {source.id} is not verified.")
            if source.effective_from:
                start = date.fromisoformat(source.effective_from)
                if evaluation_date < start:
                    reasons.append(
                        f"Source {source.id} is not yet effective on {evaluation_date}."
                    )
            if source.effective_until:
                end = date.fromisoformat(source.effective_until)
                if evaluation_date > end:
                    reasons.append(f"Source {source.id} expired on {end}.")

        return ActivationDecision(
            codepack_id=manifest.id,
            eligible=not reasons,
            reasons=tuple(reasons),
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            as_of_date=evaluation_date.isoformat(),
        )

    def ensure_single_active(
        self,
        manifests: tuple[CodepackManifest, ...],
    ) -> None:
        active_keys: set[tuple[str, str]] = set()
        for manifest in manifests:
            if manifest.activation_state != ActivationState.ACTIVE:
                continue
            key = (manifest.jurisdiction, manifest.name)
            if key in active_keys:
                raise ValueError(
                    "Multiple active codepacks found for "
                    f"{manifest.jurisdiction} / {manifest.name}."
                )
            active_keys.add(key)

    def rollback_candidate(
        self,
        current: CodepackManifest,
        manifests: tuple[CodepackManifest, ...],
    ) -> CodepackManifest | None:
        candidates = [
            item
            for item in manifests
            if item.id in current.supersedes
            and item.review_status == ReviewStatus.VALIDATED
            and item.activation_state not in (
                ActivationState.WITHDRAWN,
                ActivationState.SUPERSEDED,
            )
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item.version, reverse=True)[0]
