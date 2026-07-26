"""BB23 construction documentation assembly and release gating."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from .models import (
    ConstructionDocumentPackage,
    DocumentationIssue,
    DocumentRecord,
    DocumentSection,
    DocumentStatus,
    PackageStatus,
)


_REQUIRED_SOURCES = (
    "building_model",
    "drawing_manifest",
    "structural_report",
    "quantity_report",
    "cost_report",
    "coordination_report",
)


class ConstructionDocumentationEngine:
    """Assemble Phoenix design evidence into a controlled document package."""

    SCHEMA_VERSION = "phoenix.construction-document-package/1.0"
    VERSION = "1.0.0"

    def assemble(
        self,
        project_metadata: Mapping[str, Any] | Any,
        *,
        building_model: Mapping[str, Any] | Any | None = None,
        drawing_manifest: Mapping[str, Any] | Any | None = None,
        structural_report: Mapping[str, Any] | Any | None = None,
        quantity_report: Mapping[str, Any] | Any | None = None,
        cost_report: Mapping[str, Any] | Any | None = None,
        coordination_report: Mapping[str, Any] | Any | None = None,
        revision: str = "P01",
        stage: str = "concept",
        release_requested: bool = False,
    ) -> ConstructionDocumentPackage:
        metadata = self._normalise(project_metadata, "project_metadata")
        revision = self._validate_revision(revision)
        stage = str(stage).strip().lower() or "concept"

        sources: dict[str, dict[str, Any] | None] = {
            "building_model": self._optional_normalise(
                building_model,
                "building_model",
            ),
            "drawing_manifest": self._optional_normalise(
                drawing_manifest,
                "drawing_manifest",
            ),
            "structural_report": self._optional_normalise(
                structural_report,
                "structural_report",
            ),
            "quantity_report": self._optional_normalise(
                quantity_report,
                "quantity_report",
            ),
            "cost_report": self._optional_normalise(
                cost_report,
                "cost_report",
            ),
            "coordination_report": self._optional_normalise(
                coordination_report,
                "coordination_report",
            ),
        }

        project_id = str(
            metadata.get("project_id")
            or self._first_project_id(sources)
            or "PHX-UNSPECIFIED"
        ).strip()
        project_name = str(
            metadata.get("project_name")
            or metadata.get("name")
            or project_id
        ).strip()

        issues: list[DocumentationIssue] = []
        self._check_required_sources(sources, issues)
        self._check_project_identity(project_id, sources, issues)
        self._check_coordination_gate(
            sources["coordination_report"],
            issues,
        )

        blocking = any(issue.blocking for issue in issues)
        if blocking:
            package_status = PackageStatus.BLOCKED
            document_status = DocumentStatus.BLOCKED
        elif release_requested:
            package_status = PackageStatus.RELEASED
            document_status = DocumentStatus.RELEASED
        else:
            package_status = PackageStatus.FOR_REVIEW
            document_status = DocumentStatus.FOR_REVIEW

        source_fingerprints = {
            name: self._fingerprint(value)
            for name, value in sources.items()
            if value is not None
        }
        source_fingerprints["project_metadata"] = self._fingerprint(metadata)

        package_id = self._package_id(project_id, revision, stage)
        sections = self._build_sections(
            project_id=project_id,
            project_name=project_name,
            revision=revision,
            stage=stage,
            metadata=metadata,
            sources=sources,
            issues=issues,
            source_fingerprints=source_fingerprints,
        )
        register = self._build_document_register(
            project_id=project_id,
            revision=revision,
            status=document_status,
        )

        return ConstructionDocumentPackage(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            package_id=package_id,
            project_id=project_id,
            project_name=project_name,
            revision=revision,
            stage=stage,
            status=package_status,
            sections=sections,
            document_register=register,
            issues=issues,
            source_fingerprints_sha256=source_fingerprints,
            metadata={
                "release_requested": bool(release_requested),
                "required_sources": list(_REQUIRED_SOURCES),
                "non_certifying_documentation": True,
                "publication_profile": "BB23-foundation",
            },
        )

    def fingerprint_package(
        self,
        package: ConstructionDocumentPackage,
    ) -> str:
        return self._fingerprint(package.to_dict())

    @staticmethod
    def _normalise(
        value: Mapping[str, Any] | Any,
        label: str,
    ) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            if not isinstance(result, Mapping):
                raise TypeError(f"{label}.to_dict() must return a mapping.")
            return dict(result)
        raise TypeError(f"{label} must be a mapping or expose to_dict().")

    def _optional_normalise(
        self,
        value: Mapping[str, Any] | Any | None,
        label: str,
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return self._normalise(value, label)

    @staticmethod
    def _validate_revision(revision: str) -> str:
        value = str(revision).strip().upper()
        if not re.fullmatch(r"[A-Z][0-9]{2}", value):
            raise ValueError(
                "revision must use Phoenix format: one letter and two digits, "
                "for example P01 or C02."
            )
        return value

    @staticmethod
    def _first_project_id(
        sources: Mapping[str, dict[str, Any] | None],
    ) -> str | None:
        for source in sources.values():
            if source and source.get("project_id"):
                return str(source["project_id"])
        return None

    @staticmethod
    def _check_required_sources(
        sources: Mapping[str, dict[str, Any] | None],
        issues: list[DocumentationIssue],
    ) -> None:
        for source_name in _REQUIRED_SOURCES:
            if sources.get(source_name) is not None:
                continue
            issues.append(
                DocumentationIssue(
                    code="DOC-SOURCE-001",
                    severity="error",
                    message=(
                        f"Required BB23 source is missing: {source_name}."
                    ),
                    source=source_name,
                    blocking=True,
                )
            )

    @staticmethod
    def _check_project_identity(
        project_id: str,
        sources: Mapping[str, dict[str, Any] | None],
        issues: list[DocumentationIssue],
    ) -> None:
        for source_name, source in sources.items():
            if not source or not source.get("project_id"):
                continue
            source_project_id = str(source["project_id"]).strip()
            if source_project_id == project_id:
                continue
            issues.append(
                DocumentationIssue(
                    code="DOC-PROJECT-001",
                    severity="critical",
                    message=(
                        f"{source_name} belongs to project "
                        f"{source_project_id}, not {project_id}."
                    ),
                    source=source_name,
                    blocking=True,
                )
            )

    @staticmethod
    def _check_coordination_gate(
        coordination: Mapping[str, Any] | None,
        issues: list[DocumentationIssue],
    ) -> None:
        if coordination is None:
            return

        if coordination.get("coordination_passed") is False:
            issues.append(
                DocumentationIssue(
                    code="DOC-COORD-001",
                    severity="error",
                    message=(
                        "BB22 coordination has not passed; release is blocked."
                    ),
                    source="coordination_report",
                    blocking=True,
                )
            )
            return

        raw_issues = coordination.get("issues")
        if not isinstance(raw_issues, list):
            return

        blocking_count = 0
        for item in raw_issues:
            if not isinstance(item, Mapping):
                continue
            status = str(item.get("status") or "open").lower()
            severity = str(item.get("severity") or "").lower()
            if status == "open" and severity in {"error", "critical"}:
                blocking_count += 1

        if blocking_count:
            issues.append(
                DocumentationIssue(
                    code="DOC-COORD-002",
                    severity="error",
                    message=(
                        f"BB22 contains {blocking_count} open error or critical "
                        "coordination issues."
                    ),
                    source="coordination_report",
                    blocking=True,
                )
            )

    def _build_sections(
        self,
        *,
        project_id: str,
        project_name: str,
        revision: str,
        stage: str,
        metadata: Mapping[str, Any],
        sources: Mapping[str, dict[str, Any] | None],
        issues: list[DocumentationIssue],
        source_fingerprints: Mapping[str, str],
    ) -> list[DocumentSection]:
        building = sources["building_model"] or {}
        drawings = sources["drawing_manifest"] or {}
        structural = sources["structural_report"] or {}
        quantities = sources["quantity_report"] or {}
        costs = sources["cost_report"] or {}
        coordination = sources["coordination_report"] or {}

        building_elements = self._list_from_keys(
            building,
            ("elements", "components"),
        )
        levels = self._list_from_keys(building, ("levels", "storeys"))
        drawing_items = self._list_from_keys(
            drawings,
            ("drawings", "sheets", "documents", "register"),
        )
        structural_items = self._list_from_keys(
            structural,
            ("structural_elements", "elements", "members"),
        )
        quantity_items = self._list_from_keys(
            quantities,
            ("records", "quantities", "items"),
        )
        cost_items = self._list_from_keys(
            costs,
            ("items", "cost_items", "records", "lines"),
        )
        coordination_issues = self._list_from_keys(
            coordination,
            ("issues",),
        )

        project_entries = [
            {"label": "Project ID", "value": project_id},
            {"label": "Project name", "value": project_name},
            {"label": "Stage", "value": stage},
            {"label": "Revision", "value": revision},
        ]
        for label, key in (
            ("Client", "client"),
            ("Location", "location"),
            ("Jurisdiction", "jurisdiction"),
            ("Author", "author"),
        ):
            if metadata.get(key):
                project_entries.append(
                    {"label": label, "value": str(metadata[key])}
                )

        register_entries = [
            {
                "source": source_name,
                "available": source is not None,
                "project_id": (
                    str(source.get("project_id"))
                    if source and source.get("project_id")
                    else ""
                ),
                "fingerprint_sha256": source_fingerprints.get(
                    source_name,
                    "",
                ),
            }
            for source_name, source in sources.items()
        ]

        drawing_entries = [
            self._drawing_entry(item, index)
            for index, item in enumerate(drawing_items, start=1)
        ]
        if not drawing_entries:
            drawing_entries = [
                {
                    "drawing_id": "NOT-AVAILABLE",
                    "title": "No drawing records supplied",
                    "revision": "",
                    "status": "missing",
                }
            ]

        quantity_totals = quantities.get("totals_by_unit")
        if not isinstance(quantity_totals, Mapping):
            quantity_totals = self._aggregate_quantity_units(
                quantity_items
            )

        cost_total = self._extract_cost_total(costs, cost_items)
        currency = str(
            costs.get("currency")
            or (costs.get("metadata") or {}).get("currency")
            if isinstance(costs.get("metadata"), Mapping)
            else costs.get("currency")
            or ""
        )

        severity_summary = coordination.get("summary_by_severity")
        if not isinstance(severity_summary, Mapping):
            severity_summary = self._aggregate_coordination_severity(
                coordination_issues
            )

        limitation_paragraphs = [
            (
                "This BB23 package is generated from Phoenix source registers "
                "and is non-certifying until reviewed and approved by the "
                "responsible professionals."
            ),
            (
                "The package status is governed by source completeness, project "
                "identity and open BB22 error or critical issues."
            ),
        ]
        if issues:
            limitation_paragraphs.append(
                f"The assembly process recorded {len(issues)} documentation "
                "issue(s), of which "
                f"{sum(1 for issue in issues if issue.blocking)} are blocking."
            )

        return [
            DocumentSection(
                section_id="SEC-01",
                title="Project overview",
                paragraphs=(
                    (
                        f"This construction documentation package covers "
                        f"{project_name} ({project_id}) at the {stage} stage."
                    ),
                ),
                entries=tuple(project_entries),
                source_refs=("project_metadata",),
            ),
            DocumentSection(
                section_id="SEC-02",
                title="Document control and source register",
                paragraphs=(
                    (
                        "Each source is fingerprinted so later publications can "
                        "be traced to the exact model and register content."
                    ),
                ),
                entries=tuple(register_entries),
                source_refs=tuple(sorted(source_fingerprints)),
            ),
            DocumentSection(
                section_id="SEC-03",
                title="Building model summary",
                paragraphs=(
                    (
                        f"The BB16 building model contains "
                        f"{len(levels)} level(s) and "
                        f"{len(building_elements)} element(s)."
                    ),
                ),
                entries=(
                    {
                        "levels": len(levels),
                        "elements": len(building_elements),
                        "schema_version": building.get(
                            "schema_version",
                            "",
                        ),
                    },
                ),
                source_refs=("building_model",),
            ),
            DocumentSection(
                section_id="SEC-04",
                title="Drawing register",
                paragraphs=(
                    (
                        f"The BB18.1 drawing manifest contributes "
                        f"{len(drawing_items)} drawing or sheet record(s)."
                    ),
                ),
                entries=tuple(drawing_entries),
                source_refs=("drawing_manifest",),
            ),
            DocumentSection(
                section_id="SEC-05",
                title="Structural design summary",
                paragraphs=(
                    (
                        f"The BB19 structural source contains "
                        f"{len(structural_items)} structural object or result "
                        "record(s)."
                    ),
                ),
                entries=(
                    {
                        "object_count": len(structural_items),
                        "design_status": structural.get(
                            "status",
                            structural.get("design_status", ""),
                        ),
                        "non_certifying": structural.get(
                            "non_certifying",
                            True,
                        ),
                    },
                ),
                source_refs=("structural_report",),
            ),
            DocumentSection(
                section_id="SEC-06",
                title="Quantity take-off summary",
                paragraphs=(
                    (
                        f"The BB20 register contains "
                        f"{len(quantity_items)} quantity record(s)."
                    ),
                ),
                entries=tuple(
                    {
                        "unit": str(unit),
                        "value": value,
                    }
                    for unit, value in sorted(quantity_totals.items())
                ),
                source_refs=("quantity_report",),
            ),
            DocumentSection(
                section_id="SEC-07",
                title="Cost estimate summary",
                paragraphs=(
                    (
                        f"The BB21 estimate contains {len(cost_items)} cost "
                        "item(s)."
                    ),
                ),
                entries=(
                    {
                        "currency": currency,
                        "total_cost": cost_total,
                        "price_date": costs.get(
                            "price_date",
                            costs.get("base_date", ""),
                        ),
                    },
                ),
                source_refs=("cost_report",),
            ),
            DocumentSection(
                section_id="SEC-08",
                title="BIM coordination status",
                paragraphs=(
                    (
                        f"BB22 reports {len(coordination_issues)} coordination "
                        "issue(s)."
                    ),
                ),
                entries=tuple(
                    {
                        "severity": str(severity),
                        "count": count,
                    }
                    for severity, count in sorted(
                        severity_summary.items()
                    )
                ),
                source_refs=("coordination_report",),
            ),
            DocumentSection(
                section_id="SEC-09",
                title="Documentation issues and limitations",
                paragraphs=tuple(limitation_paragraphs),
                entries=tuple(issue.to_dict() for issue in issues),
                source_refs=tuple(sorted(sources)),
            ),
            DocumentSection(
                section_id="SEC-10",
                title="Evidence fingerprints",
                paragraphs=(
                    (
                        "The SHA-256 values below provide deterministic source "
                        "evidence for this package revision."
                    ),
                ),
                entries=tuple(
                    {
                        "source": name,
                        "sha256": fingerprint,
                    }
                    for name, fingerprint in sorted(
                        source_fingerprints.items()
                    )
                ),
                source_refs=tuple(sorted(source_fingerprints)),
            ),
        ]

    @staticmethod
    def _build_document_register(
        *,
        project_id: str,
        revision: str,
        status: DocumentStatus,
    ) -> list[DocumentRecord]:
        safe_project = re.sub(
            r"[^A-Z0-9]+",
            "-",
            project_id.upper(),
        ).strip("-")
        prefix = safe_project or "PHX-PROJECT"

        definitions = (
            (
                "MANIFEST",
                "Construction documentation manifest",
                "JSON",
                "construction_documentation_manifest.json",
                "project_controls",
            ),
            (
                "REGISTER",
                "Document register",
                "CSV",
                "document_register.csv",
                "project_controls",
            ),
            (
                "REPORT-MD",
                "Technical project report",
                "MARKDOWN",
                "technical_project_report.md",
                "multidiscipline",
            ),
            (
                "REPORT-HTML",
                "Technical project report",
                "HTML",
                "technical_project_report.html",
                "multidiscipline",
            ),
            (
                "REPORT-DOCX",
                "Technical project report",
                "DOCX",
                "technical_project_report.docx",
                "multidiscipline",
            ),
            (
                "REPORT-PDF",
                "Technical project report",
                "PDF",
                "technical_project_report.pdf",
                "multidiscipline",
            ),
            (
                "CHECKSUMS",
                "Publication checksums",
                "SHA256",
                "checksums.sha256",
                "project_controls",
            ),
            (
                "DOSSIER",
                "Construction documentation dossier",
                "ZIP",
                "construction_documentation_dossier.zip",
                "multidiscipline",
            ),
        )

        return [
            DocumentRecord(
                document_id=f"{prefix}-BB23-{suffix}",
                title=title,
                document_type=document_type,
                revision=revision,
                status=status,
                filename=filename,
                discipline=discipline,
                source_refs=tuple(_REQUIRED_SOURCES),
            )
            for (
                suffix,
                title,
                document_type,
                filename,
                discipline,
            ) in definitions
        ]

    @staticmethod
    def _list_from_keys(
        value: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> list[Any]:
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, list):
                return candidate
        return []

    @staticmethod
    def _drawing_entry(
        item: Any,
        index: int,
    ) -> dict[str, Any]:
        if not isinstance(item, Mapping):
            return {
                "drawing_id": f"DRAWING-{index:03d}",
                "title": str(item),
                "revision": "",
                "status": "",
            }
        return {
            "drawing_id": str(
                item.get("drawing_id")
                or item.get("sheet_id")
                or item.get("id")
                or f"DRAWING-{index:03d}"
            ),
            "title": str(
                item.get("title")
                or item.get("name")
                or "Untitled drawing"
            ),
            "revision": str(item.get("revision") or ""),
            "status": str(item.get("status") or ""),
        }

    @staticmethod
    def _aggregate_quantity_units(
        records: list[Any],
    ) -> dict[str, float]:
        totals: dict[str, float] = {}
        for record in records:
            if not isinstance(record, Mapping):
                continue
            unit = str(record.get("unit") or "").strip()
            value = record.get("value")
            if (
                not unit
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
            ):
                continue
            totals[unit] = totals.get(unit, 0.0) + float(value)
        return {
            unit: round(value, 6)
            for unit, value in sorted(totals.items())
        }

    @staticmethod
    def _extract_cost_total(
        costs: Mapping[str, Any],
        items: list[Any],
    ) -> float | None:
        for key in (
            "grand_total",
            "total_cost",
            "project_total",
            "total",
        ):
            value = costs.get(key)
            if isinstance(value, (int, float)) and not isinstance(
                value,
                bool,
            ):
                return round(float(value), 2)

        total = 0.0
        found = False
        for item in items:
            if not isinstance(item, Mapping):
                continue
            for key in ("total_cost", "line_total", "amount"):
                value = item.get(key)
                if isinstance(value, (int, float)) and not isinstance(
                    value,
                    bool,
                ):
                    total += float(value)
                    found = True
                    break
        return round(total, 2) if found else None

    @staticmethod
    def _aggregate_coordination_severity(
        issues: list[Any],
    ) -> dict[str, int]:
        totals: dict[str, int] = {}
        for issue in issues:
            if not isinstance(issue, Mapping):
                continue
            severity = str(
                issue.get("severity") or "unspecified"
            ).lower()
            totals[severity] = totals.get(severity, 0) + 1
        return dict(sorted(totals.items()))

    @staticmethod
    def _package_id(
        project_id: str,
        revision: str,
        stage: str,
    ) -> str:
        payload = f"{project_id}|{revision}|{stage}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()[:16].upper()
        return f"CDP-{digest}"

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
