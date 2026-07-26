"""BB22 model, quantity and cost coordination logic."""

from __future__ import annotations

import hashlib
import itertools
import json
from collections.abc import Mapping
from typing import Any

from .models import (
    CoordinationIssue,
    CoordinationReport,
    IssueSeverity,
    IssueStatus,
)


_CATEGORY_ALIASES = {
    "floor": "slab",
    "footing": "foundation",
    "pile": "foundation",
    "partition": "wall",
    "duct": "mep",
    "pipe": "mep",
    "cabletray": "mep",
    "cable_tray": "mep",
}

_OPENINGS = {"door", "window"}
_STRUCTURAL = {"foundation", "column", "beam", "wall", "slab", "roof"}
_HARD_CLASH_PAIRS = {
    frozenset(("door", "column")),
    frozenset(("door", "beam")),
    frozenset(("door", "slab")),
    frozenset(("door", "foundation")),
    frozenset(("window", "column")),
    frozenset(("window", "beam")),
    frozenset(("window", "slab")),
    frozenset(("window", "foundation")),
    frozenset(("mep", "column")),
    frozenset(("mep", "beam")),
    frozenset(("mep", "slab")),
    frozenset(("mep", "foundation")),
    frozenset(("stair", "beam")),
    frozenset(("stair", "slab")),
}


class BimCoordinationEngine:
    """Coordinate discipline models and their downstream registers."""

    SCHEMA_VERSION = "phoenix.bim-coordination-report/1.0"
    VERSION = "1.0.0"

    def coordinate(
        self,
        models: Mapping[str, Mapping[str, Any] | Any],
        *,
        quantity_report: Mapping[str, Any] | Any | None = None,
        cost_report: Mapping[str, Any] | Any | None = None,
        tolerance_m: float = 0.001,
    ) -> CoordinationReport:
        if tolerance_m < 0:
            raise ValueError("tolerance_m must not be negative.")
        if not models:
            raise ValueError("At least one discipline model is required.")

        normalised_models = {
            str(name): self._normalise(model, f"model:{name}")
            for name, model in models.items()
        }
        quantity = (
            self._normalise(quantity_report, "quantity_report")
            if quantity_report is not None
            else None
        )
        cost = (
            self._normalise(cost_report, "cost_report")
            if cost_report is not None
            else None
        )

        project_ids = [
            str(model.get("project_id"))
            for model in normalised_models.values()
            if model.get("project_id")
        ]
        project_id = project_ids[0] if project_ids else "PHX-UNSPECIFIED"

        issues: list[CoordinationIssue] = []
        indexes: dict[str, dict[str, dict[str, Any]]] = {}
        elements_by_model: dict[str, list[dict[str, Any]]] = {}

        if len(set(project_ids)) > 1:
            issues.append(
                self._issue(
                    issue_type="project_identity_conflict",
                    title="Project identifiers differ between discipline models",
                    description=(
                        "The supplied discipline models do not identify the same project."
                    ),
                    severity=IssueSeverity.CRITICAL,
                    discipline="coordination",
                    evidence=(
                        {"project_ids": sorted(set(project_ids))},
                    ),
                )
            )

        for model_name, model in normalised_models.items():
            elements = self._elements(model)
            elements_by_model[model_name] = elements
            indexes[model_name] = self._index_model(
                model_name,
                elements,
                issues,
            )

        self._check_shared_object_identity(indexes, issues, tolerance_m)
        self._check_geometric_clashes(elements_by_model, issues, tolerance_m)

        known_objects = {
            object_id
            for index in indexes.values()
            for object_id in index
        }
        quantity_ids: set[str] = set()
        quantity_object_ids: set[str] = set()

        if quantity is not None:
            quantity_ids, quantity_object_ids = self._check_quantities(
                quantity,
                known_objects,
                issues,
            )
            self._check_missing_quantities(
                elements_by_model,
                quantity_object_ids,
                issues,
            )

        if cost is not None:
            self._check_costs(
                cost,
                quantity_ids,
                issues,
            )

        issues.sort(
            key=lambda issue: (
                self._severity_rank(issue.severity),
                issue.issue_type,
                issue.source_model or "",
                issue.source_object_id or "",
                issue.target_model or "",
                issue.target_object_id or "",
                issue.issue_id,
            )
        )

        fingerprints = {
            name: self._fingerprint(model)
            for name, model in normalised_models.items()
        }
        if quantity is not None:
            fingerprints["quantity_report"] = self._fingerprint(quantity)
        if cost is not None:
            fingerprints["cost_report"] = self._fingerprint(cost)

        return CoordinationReport(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=project_id,
            model_fingerprints_sha256=fingerprints,
            issues=issues,
            metadata={
                "discipline_models": sorted(normalised_models),
                "model_count": len(normalised_models),
                "quantity_report_supplied": quantity is not None,
                "cost_report_supplied": cost is not None,
                "geometric_tolerance_m": tolerance_m,
                "bcf_export_profile": "foundation",
                "non_certifying_coordination": True,
            },
        )

    def fingerprint_report(self, report: CoordinationReport) -> str:
        return self._fingerprint(report.to_dict())

    @staticmethod
    def _normalise(value: Mapping[str, Any] | Any, label: str) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            data = to_dict()
            if not isinstance(data, Mapping):
                raise TypeError(f"{label}.to_dict() must return a mapping.")
            return dict(data)
        raise TypeError(f"{label} must be a mapping or expose to_dict().")

    @staticmethod
    def _elements(model: Mapping[str, Any]) -> list[dict[str, Any]]:
        for key in (
            "elements",
            "structural_elements",
            "members",
            "components",
        ):
            value = model.get(key)
            if isinstance(value, list):
                return [
                    dict(item)
                    for item in value
                    if isinstance(item, Mapping)
                ]
        return []

    def _index_model(
        self,
        model_name: str,
        elements: list[dict[str, Any]],
        issues: list[CoordinationIssue],
    ) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for position, element in enumerate(elements):
            object_id = str(element.get("id") or "").strip()
            if not object_id:
                issues.append(
                    self._issue(
                        issue_type="missing_object_id",
                        title="Model object has no stable identifier",
                        description=(
                            f"Object position {position} in {model_name} cannot be "
                            "coordinated without an ID."
                        ),
                        severity=IssueSeverity.ERROR,
                        discipline=model_name,
                        source_model=model_name,
                        evidence=({"position": position},),
                    )
                )
                continue
            if object_id in index:
                issues.append(
                    self._issue(
                        issue_type="duplicate_object_id",
                        title="Duplicate object identifier",
                        description=(
                            f"Object ID {object_id} occurs more than once in "
                            f"{model_name}."
                        ),
                        severity=IssueSeverity.ERROR,
                        discipline=model_name,
                        source_model=model_name,
                        source_object_id=object_id,
                    )
                )
                continue
            index[object_id] = element
        return index

    def _check_shared_object_identity(
        self,
        indexes: Mapping[str, Mapping[str, dict[str, Any]]],
        issues: list[CoordinationIssue],
        tolerance_m: float,
    ) -> None:
        model_names = sorted(indexes)
        for left_name, right_name in itertools.combinations(model_names, 2):
            shared_ids = sorted(
                set(indexes[left_name]) & set(indexes[right_name])
            )
            for object_id in shared_ids:
                left = indexes[left_name][object_id]
                right = indexes[right_name][object_id]
                left_category = self._category(left)
                right_category = self._category(right)

                if left_category != right_category:
                    issues.append(
                        self._issue(
                            issue_type="semantic_category_conflict",
                            title="Shared object has different categories",
                            description=(
                                f"{object_id} is {left_category} in {left_name} "
                                f"and {right_category} in {right_name}."
                            ),
                            severity=IssueSeverity.ERROR,
                            discipline="coordination",
                            source_model=left_name,
                            source_object_id=object_id,
                            target_model=right_name,
                            target_object_id=object_id,
                            evidence=(
                                {"model": left_name, "category": left_category},
                                {"model": right_name, "category": right_category},
                            ),
                        )
                    )

                left_level = self._level_id(left)
                right_level = self._level_id(right)
                if (
                    left_level
                    and right_level
                    and left_level != right_level
                ):
                    issues.append(
                        self._issue(
                            issue_type="level_assignment_conflict",
                            title="Shared object is assigned to different levels",
                            description=(
                                f"{object_id} is assigned to {left_level} in "
                                f"{left_name} and {right_level} in {right_name}."
                            ),
                            severity=IssueSeverity.ERROR,
                            discipline="coordination",
                            source_model=left_name,
                            source_object_id=object_id,
                            target_model=right_name,
                            target_object_id=object_id,
                            level_id=left_level,
                            evidence=(
                                {"model": left_name, "level_id": left_level},
                                {"model": right_name, "level_id": right_level},
                            ),
                        )
                    )

                left_bbox = self._bbox(left)
                right_bbox = self._bbox(right)
                if left_bbox and right_bbox:
                    drift = max(
                        abs(a - b)
                        for a, b in zip(left_bbox, right_bbox)
                    )
                    if drift > tolerance_m:
                        issues.append(
                            self._issue(
                                issue_type="shared_geometry_drift",
                                title="Shared object geometry is not synchronized",
                                description=(
                                    f"{object_id} differs by up to {drift:.6f} m "
                                    f"between {left_name} and {right_name}."
                                ),
                                severity=IssueSeverity.WARNING,
                                discipline="coordination",
                                source_model=left_name,
                                source_object_id=object_id,
                                target_model=right_name,
                                target_object_id=object_id,
                                level_id=left_level or right_level,
                                location=self._bbox_center(left_bbox),
                                evidence=(
                                    {"model": left_name, "bbox": list(left_bbox)},
                                    {"model": right_name, "bbox": list(right_bbox)},
                                    {"maximum_drift_m": round(drift, 6)},
                                ),
                            )
                        )

    def _check_geometric_clashes(
        self,
        elements_by_model: Mapping[str, list[dict[str, Any]]],
        issues: list[CoordinationIssue],
        tolerance_m: float,
    ) -> None:
        model_names = sorted(elements_by_model)
        for left_name, right_name in itertools.combinations(model_names, 2):
            for left in elements_by_model[left_name]:
                left_id = str(left.get("id") or "").strip()
                left_bbox = self._bbox(left)
                if not left_id or left_bbox is None:
                    continue
                left_category = self._category(left)

                for right in elements_by_model[right_name]:
                    right_id = str(right.get("id") or "").strip()
                    if not right_id or right_id == left_id:
                        continue
                    right_bbox = self._bbox(right)
                    if right_bbox is None:
                        continue
                    right_category = self._category(right)

                    if frozenset((left_category, right_category)) not in _HARD_CLASH_PAIRS:
                        continue
                    left_level = self._level_id(left)
                    right_level = self._level_id(right)
                    if (
                        left_level
                        and right_level
                        and left_level != right_level
                    ):
                        continue

                    overlap = self._bbox_overlap(
                        left_bbox,
                        right_bbox,
                        tolerance_m,
                    )
                    if overlap is None:
                        continue
                    overlap_bbox, overlap_volume = overlap
                    issues.append(
                        self._issue(
                            issue_type="hard_geometric_clash",
                            title="Hard geometric clash",
                            description=(
                                f"{left_id} ({left_category}) from {left_name} "
                                f"overlaps {right_id} ({right_category}) from "
                                f"{right_name}."
                            ),
                            severity=IssueSeverity.ERROR,
                            discipline="coordination",
                            source_model=left_name,
                            source_object_id=left_id,
                            target_model=right_name,
                            target_object_id=right_id,
                            level_id=left_level or right_level,
                            location=self._bbox_center(overlap_bbox),
                            evidence=(
                                {"source_bbox": list(left_bbox)},
                                {"target_bbox": list(right_bbox)},
                                {
                                    "overlap_bbox": list(overlap_bbox),
                                    "overlap_volume_m3": round(
                                        overlap_volume,
                                        9,
                                    ),
                                },
                            ),
                        )
                    )

    def _check_quantities(
        self,
        quantity_report: Mapping[str, Any],
        known_objects: set[str],
        issues: list[CoordinationIssue],
    ) -> tuple[set[str], set[str]]:
        records = quantity_report.get("records")
        if not isinstance(records, list):
            issues.append(
                self._issue(
                    issue_type="quantity_register_missing",
                    title="Quantity report has no usable records",
                    description=(
                        "BB20 quantity records are missing or not a list."
                    ),
                    severity=IssueSeverity.ERROR,
                    discipline="quantity_takeoff",
                )
            )
            return set(), set()

        quantity_ids: set[str] = set()
        object_ids: set[str] = set()
        for position, record in enumerate(records):
            if not isinstance(record, Mapping):
                continue
            quantity_id = str(record.get("quantity_id") or "").strip()
            object_id = str(record.get("source_object_id") or "").strip()

            if not quantity_id:
                issues.append(
                    self._issue(
                        issue_type="missing_quantity_id",
                        title="Quantity record has no stable identifier",
                        description=f"Quantity record position {position} has no ID.",
                        severity=IssueSeverity.ERROR,
                        discipline="quantity_takeoff",
                        evidence=({"position": position},),
                    )
                )
            elif quantity_id in quantity_ids:
                issues.append(
                    self._issue(
                        issue_type="duplicate_quantity_id",
                        title="Duplicate quantity identifier",
                        description=(
                            f"Quantity ID {quantity_id} occurs more than once."
                        ),
                        severity=IssueSeverity.ERROR,
                        discipline="quantity_takeoff",
                        source_object_id=object_id or None,
                        evidence=({"quantity_id": quantity_id},),
                    )
                )
            else:
                quantity_ids.add(quantity_id)

            if not object_id:
                issues.append(
                    self._issue(
                        issue_type="quantity_without_model_object",
                        title="Quantity is not linked to a model object",
                        description=(
                            f"Quantity {quantity_id or position} has no "
                            "source_object_id."
                        ),
                        severity=IssueSeverity.ERROR,
                        discipline="quantity_takeoff",
                        evidence=(
                            {"quantity_id": quantity_id or None},
                            {"position": position},
                        ),
                    )
                )
            else:
                object_ids.add(object_id)
                if object_id not in known_objects:
                    issues.append(
                        self._issue(
                            issue_type="orphan_quantity",
                            title="Quantity references an unknown model object",
                            description=(
                                f"Quantity {quantity_id or position} references "
                                f"{object_id}, which is absent from all supplied models."
                            ),
                            severity=IssueSeverity.ERROR,
                            discipline="quantity_takeoff",
                            source_object_id=object_id,
                            evidence=(
                                {"quantity_id": quantity_id or None},
                            ),
                        )
                    )
        return quantity_ids, object_ids

    def _check_missing_quantities(
        self,
        elements_by_model: Mapping[str, list[dict[str, Any]]],
        quantity_object_ids: set[str],
        issues: list[CoordinationIssue],
    ) -> None:
        candidates: dict[str, tuple[str, dict[str, Any]]] = {}
        for model_name, elements in elements_by_model.items():
            for element in elements:
                object_id = str(element.get("id") or "").strip()
                if not object_id:
                    continue
                category = self._category(element)
                if category in {"site", "space", "generic"}:
                    continue
                candidates.setdefault(object_id, (model_name, element))

        for object_id, (model_name, element) in sorted(candidates.items()):
            if object_id in quantity_object_ids:
                continue
            issues.append(
                self._issue(
                    issue_type="model_object_without_quantity",
                    title="Measurable model object has no BB20 quantity",
                    description=(
                        f"{object_id} from {model_name} has no linked quantity record."
                    ),
                    severity=IssueSeverity.WARNING,
                    discipline="quantity_takeoff",
                    source_model=model_name,
                    source_object_id=object_id,
                    level_id=self._level_id(element),
                    evidence=(
                        {"category": self._category(element)},
                    ),
                )
            )

    def _check_costs(
        self,
        cost_report: Mapping[str, Any],
        quantity_ids: set[str],
        issues: list[CoordinationIssue],
    ) -> None:
        items = None
        for key in ("items", "cost_items", "records", "lines"):
            value = cost_report.get(key)
            if isinstance(value, list):
                items = value
                break

        if items is None:
            issues.append(
                self._issue(
                    issue_type="cost_register_missing",
                    title="Cost report has no usable cost items",
                    description=(
                        "BB21 cost items are missing or not a list."
                    ),
                    severity=IssueSeverity.ERROR,
                    discipline="cost_estimation",
                )
            )
            return

        seen_cost_ids: set[str] = set()
        linked_quantity_ids: set[str] = set()

        for position, item in enumerate(items):
            if not isinstance(item, Mapping):
                continue
            cost_id = str(
                item.get("cost_item_id")
                or item.get("line_id")
                or item.get("id")
                or ""
            ).strip()
            quantity_id = str(item.get("quantity_id") or "").strip()

            if cost_id:
                if cost_id in seen_cost_ids:
                    issues.append(
                        self._issue(
                            issue_type="duplicate_cost_item_id",
                            title="Duplicate cost item identifier",
                            description=(
                                f"Cost item ID {cost_id} occurs more than once."
                            ),
                            severity=IssueSeverity.ERROR,
                            discipline="cost_estimation",
                            evidence=({"cost_item_id": cost_id},),
                        )
                    )
                seen_cost_ids.add(cost_id)

            if not quantity_id:
                issues.append(
                    self._issue(
                        issue_type="cost_without_quantity",
                        title="Cost item is not linked to a BB20 quantity",
                        description=(
                            f"Cost item {cost_id or position} has no quantity_id."
                        ),
                        severity=IssueSeverity.ERROR,
                        discipline="cost_estimation",
                        evidence=(
                            {"cost_item_id": cost_id or None},
                            {"position": position},
                        ),
                    )
                )
                continue

            linked_quantity_ids.add(quantity_id)
            if quantity_ids and quantity_id not in quantity_ids:
                issues.append(
                    self._issue(
                        issue_type="orphan_cost_item",
                        title="Cost item references an unknown quantity",
                        description=(
                            f"Cost item {cost_id or position} references "
                            f"{quantity_id}, which is absent from the BB20 report."
                        ),
                        severity=IssueSeverity.ERROR,
                        discipline="cost_estimation",
                        evidence=(
                            {"cost_item_id": cost_id or None},
                            {"quantity_id": quantity_id},
                        ),
                    )
                )

        if quantity_ids:
            for quantity_id in sorted(quantity_ids - linked_quantity_ids):
                issues.append(
                    self._issue(
                        issue_type="quantity_without_cost",
                        title="BB20 quantity has no BB21 cost item",
                        description=(
                            f"Quantity {quantity_id} is not represented in the "
                            "supplied cost report."
                        ),
                        severity=IssueSeverity.WARNING,
                        discipline="cost_estimation",
                        evidence=({"quantity_id": quantity_id},),
                    )
                )

    @staticmethod
    def _category(element: Mapping[str, Any]) -> str:
        raw = str(
            element.get("category")
            or element.get("type")
            or element.get("element_type")
            or "generic"
        ).strip().lower()
        return _CATEGORY_ALIASES.get(raw, raw)

    @staticmethod
    def _level_id(element: Mapping[str, Any]) -> str | None:
        value = (
            element.get("level_id")
            or element.get("storey_id")
            or element.get("floor_id")
        )
        if value in (None, ""):
            return None
        return str(value).strip() or None

    @classmethod
    def _bbox(
        cls,
        element: Mapping[str, Any],
    ) -> tuple[float, float, float, float, float, float] | None:
        geometry = element.get("geometry")
        if not isinstance(geometry, Mapping):
            return None

        bbox = geometry.get("bbox")
        if isinstance(bbox, Mapping):
            keys = (
                "min_x",
                "min_y",
                "min_z",
                "max_x",
                "max_y",
                "max_z",
            )
            values = [bbox.get(key) for key in keys]
            if all(cls._number(value) for value in values):
                result = tuple(float(value) for value in values)
                return result if cls._valid_bbox(result) else None

        if isinstance(bbox, list) and len(bbox) == 6:
            if all(cls._number(value) for value in bbox):
                result = tuple(float(value) for value in bbox)
                return result if cls._valid_bbox(result) else None

        x = cls._first_number(geometry, "x_m", "x", "origin_x_m")
        y = cls._first_number(geometry, "y_m", "y", "origin_y_m")
        z = cls._first_number(geometry, "z_m", "z", "origin_z_m")
        length = cls._positive_number(geometry, "length_m", "length", "width_m")
        width = cls._positive_number(geometry, "width_m", "width", "depth_m")
        height = cls._positive_number(
            geometry,
            "height_m",
            "height",
            "thickness_m",
            "depth_m",
        )
        if x is None or y is None or z is None:
            return None
        if length is None or width is None or height is None:
            return None
        return (
            x,
            y,
            z,
            x + length,
            y + width,
            z + height,
        )

    @staticmethod
    def _number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @classmethod
    def _first_number(
        cls,
        data: Mapping[str, Any],
        *keys: str,
    ) -> float | None:
        for key in keys:
            value = data.get(key)
            if cls._number(value):
                return float(value)
        return None

    @classmethod
    def _positive_number(
        cls,
        data: Mapping[str, Any],
        *keys: str,
    ) -> float | None:
        for key in keys:
            value = data.get(key)
            if cls._number(value) and float(value) > 0:
                return float(value)
        return None

    @staticmethod
    def _valid_bbox(
        bbox: tuple[float, float, float, float, float, float],
    ) -> bool:
        return (
            bbox[3] > bbox[0]
            and bbox[4] > bbox[1]
            and bbox[5] > bbox[2]
        )

    @staticmethod
    def _bbox_overlap(
        left: tuple[float, float, float, float, float, float],
        right: tuple[float, float, float, float, float, float],
        tolerance_m: float,
    ) -> tuple[
        tuple[float, float, float, float, float, float],
        float,
    ] | None:
        min_x = max(left[0], right[0])
        min_y = max(left[1], right[1])
        min_z = max(left[2], right[2])
        max_x = min(left[3], right[3])
        max_y = min(left[4], right[4])
        max_z = min(left[5], right[5])

        dx = max_x - min_x
        dy = max_y - min_y
        dz = max_z - min_z
        if dx <= tolerance_m or dy <= tolerance_m or dz <= tolerance_m:
            return None
        overlap = (min_x, min_y, min_z, max_x, max_y, max_z)
        return overlap, dx * dy * dz

    @staticmethod
    def _bbox_center(
        bbox: tuple[float, float, float, float, float, float],
    ) -> dict[str, float]:
        return {
            "x_m": round((bbox[0] + bbox[3]) / 2.0, 6),
            "y_m": round((bbox[1] + bbox[4]) / 2.0, 6),
            "z_m": round((bbox[2] + bbox[5]) / 2.0, 6),
        }

    def _issue(
        self,
        *,
        issue_type: str,
        title: str,
        description: str,
        severity: IssueSeverity,
        discipline: str,
        source_model: str | None = None,
        source_object_id: str | None = None,
        target_model: str | None = None,
        target_object_id: str | None = None,
        level_id: str | None = None,
        location: dict[str, float] | None = None,
        evidence: tuple[dict[str, Any], ...] = (),
    ) -> CoordinationIssue:
        issue_id = self._issue_id(
            issue_type,
            source_model,
            source_object_id,
            target_model,
            target_object_id,
            evidence,
        )
        return CoordinationIssue(
            issue_id=issue_id,
            issue_type=issue_type,
            title=title,
            description=description,
            severity=severity,
            status=IssueStatus.OPEN,
            discipline=discipline,
            source_model=source_model,
            source_object_id=source_object_id,
            target_model=target_model,
            target_object_id=target_object_id,
            level_id=level_id,
            location=dict(location or {}),
            evidence=evidence,
        )

    @staticmethod
    def _issue_id(
        issue_type: str,
        source_model: str | None,
        source_object_id: str | None,
        target_model: str | None,
        target_object_id: str | None,
        evidence: tuple[dict[str, Any], ...],
    ) -> str:
        payload = json.dumps(
            {
                "issue_type": issue_type,
                "source_model": source_model,
                "source_object_id": source_object_id,
                "target_model": target_model,
                "target_object_id": target_object_id,
                "evidence": list(evidence),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"BCI-{hashlib.sha256(payload).hexdigest()[:24].upper()}"

    @staticmethod
    def _fingerprint(value: Any) -> str:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _severity_rank(severity: IssueSeverity) -> int:
        return {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.ERROR: 1,
            IssueSeverity.WARNING: 2,
            IssueSeverity.INFO: 3,
        }[severity]
