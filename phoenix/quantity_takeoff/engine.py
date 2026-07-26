"""BB20 Quantity Take-Off Engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .models import (
    MeasurementBasis,
    QuantityIssue,
    QuantityRecord,
    QuantityStatus,
    QuantityTakeoffReport,
    QuantityUnit,
)


_CATEGORY_ALIASES = {
    "site": "site",
    "foundation": "foundation",
    "footing": "foundation",
    "pile": "foundation",
    "column": "column",
    "beam": "beam",
    "wall": "wall",
    "slab": "slab",
    "floor": "slab",
    "roof": "roof",
    "door": "door",
    "window": "window",
    "stair": "stair",
    "mep": "mep",
    "generic": "generic",
}

_WORK_SECTIONS = {
    "site": "01 Site and earthworks",
    "foundation": "02 Foundations",
    "column": "03 Structural frame",
    "beam": "03 Structural frame",
    "wall": "04 Walls and partitions",
    "slab": "05 Floors and slabs",
    "roof": "06 Roofs",
    "door": "07 Doors",
    "window": "08 Windows",
    "stair": "09 Stairs",
    "mep": "10 Building services",
    "generic": "99 General",
}

_STRUCTURAL_CATEGORIES = {"foundation", "column", "beam", "wall", "slab", "roof"}


class QuantityTakeoffEngine:
    """Generate traceable concept quantities from Phoenix models."""

    SCHEMA_VERSION = "phoenix.quantity-takeoff-report/1.0"
    VERSION = "1.0.0"

    def generate(
        self,
        building_model: Mapping[str, Any] | Any,
        *,
        structural_model: Mapping[str, Any] | Any | None = None,
        drawing_manifest: Mapping[str, Any] | Any | None = None,
    ) -> QuantityTakeoffReport:
        building = self._normalise(building_model, "building_model")
        structural = (
            self._normalise(structural_model, "structural_model")
            if structural_model is not None
            else None
        )
        drawings = (
            self._normalise(drawing_manifest, "drawing_manifest")
            if drawing_manifest is not None
            else {}
        )

        project_id = str(
            building.get("project_id")
            or (structural or {}).get("project_id")
            or "PHX-UNSPECIFIED"
        )
        combined_fingerprint = self._fingerprint_inputs(
            building,
            structural,
            drawings,
        )

        records: list[QuantityRecord] = []
        issues: list[QuantityIssue] = []
        seen_record_keys: set[tuple[str, str, str, str]] = set()

        structural_elements = self._elements(structural or {})
        structural_ids = {
            str(item.get("id"))
            for item in structural_elements
            if item.get("id")
        }

        for element in self._elements(building):
            element_id = str(element.get("id") or "")
            category = self._category(element)
            if (
                element_id in structural_ids
                and category in _STRUCTURAL_CATEGORIES
            ):
                issues.append(
                    QuantityIssue(
                        code="QTO-SOURCE-001",
                        severity="info",
                        message=(
                            "Building-model quantity skipped because the same "
                            "structural object is present in the structural model."
                        ),
                        source_object_id=element_id,
                        source_model="building_model",
                    )
                )
                continue
            self._measure_element(
                element,
                source_model="building_model",
                drawing_manifest=drawings,
                records=records,
                issues=issues,
                seen_record_keys=seen_record_keys,
            )

        for element in structural_elements:
            self._measure_element(
                element,
                source_model="structural_model",
                drawing_manifest=drawings,
                records=records,
                issues=issues,
                seen_record_keys=seen_record_keys,
            )

        records.sort(
            key=lambda item: (
                item.work_section,
                item.source_level_id or "",
                item.source_object_id,
                item.quantity_type,
                item.unit.value,
            )
        )
        issues.sort(
            key=lambda item: (
                item.severity,
                item.source_model or "",
                item.source_object_id or "",
                item.code,
            )
        )

        return QuantityTakeoffReport(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=project_id,
            model_fingerprint_sha256=combined_fingerprint,
            records=records,
            issues=issues,
            metadata={
                "building_element_count": len(self._elements(building)),
                "structural_element_count": len(structural_elements),
                "drawing_manifest_supplied": bool(drawings),
                "non_certifying_quantities": True,
                "measurement_precision": "concept",
            },
        )

    def fingerprint_report(self, report: QuantityTakeoffReport) -> str:
        payload = json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

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
        for key in ("elements", "structural_elements", "members", "components"):
            value = model.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, Mapping)]
        return []

    @staticmethod
    def _category(element: Mapping[str, Any]) -> str:
        raw = str(
            element.get("category")
            or element.get("type")
            or element.get("element_type")
            or "generic"
        ).strip().lower()
        return _CATEGORY_ALIASES.get(raw, "generic")

    @staticmethod
    def _fingerprint_inputs(
        building: Mapping[str, Any],
        structural: Mapping[str, Any] | None,
        drawings: Mapping[str, Any],
    ) -> str:
        payload = json.dumps(
            {
                "building_model": building,
                "structural_model": structural,
                "drawing_manifest": drawings,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _measure_element(
        self,
        element: Mapping[str, Any],
        *,
        source_model: str,
        drawing_manifest: Mapping[str, Any],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen_record_keys: set[tuple[str, str, str, str]],
    ) -> None:
        element_id = str(element.get("id") or "").strip()
        if not element_id:
            issues.append(
                QuantityIssue(
                    code="QTO-ID-001",
                    severity="error",
                    message="Element has no identifier and was not measured.",
                    source_model=source_model,
                )
            )
            return

        category = self._category(element)
        work_section = _WORK_SECTIONS[category]
        geometry = self._mapping(element.get("geometry"))
        properties = self._mapping(element.get("properties"))
        material_data = self._mapping(element.get("material"))
        material = self._material_name(material_data, properties)
        level_id = self._optional_text(
            element.get("level_id")
            or element.get("storey_id")
            or element.get("floor_id")
        )
        drawing_refs = self._drawing_refs(element, drawing_manifest)

        invalid_dimensions = self._invalid_dimensions(geometry)
        if invalid_dimensions:
            issues.append(
                QuantityIssue(
                    code="QTO-DIM-001",
                    severity="error",
                    message=(
                        "Element contains non-positive dimensions: "
                        + ", ".join(sorted(invalid_dimensions))
                    ),
                    source_object_id=element_id,
                    source_model=source_model,
                )
            )

        self._add_record(
            records,
            seen_record_keys,
            source_object_id=element_id,
            source_model=source_model,
            source_level_id=level_id,
            category=category,
            work_section=work_section,
            material=material,
            quantity_type="count",
            value=1.0,
            unit=QuantityUnit.EACH,
            basis=MeasurementBasis.COUNTED,
            status=QuantityStatus.COMPLETE,
            formula="1 object",
            inputs={},
            assumptions=(),
            drawing_refs=drawing_refs,
        )

        declared = properties.get("declared_quantities")
        if isinstance(declared, Mapping):
            self._measure_declared_quantities(
                element_id=element_id,
                source_model=source_model,
                level_id=level_id,
                category=category,
                work_section=work_section,
                material=material,
                declared=declared,
                drawing_refs=drawing_refs,
                records=records,
                issues=issues,
                seen_record_keys=seen_record_keys,
            )

        if category == "wall":
            self._measure_wall(
                element_id, source_model, level_id, category, work_section,
                material, geometry, drawing_refs, records, issues, seen_record_keys
            )
        elif category in {"slab", "roof"}:
            self._measure_plate(
                element_id, source_model, level_id, category, work_section,
                material, geometry, drawing_refs, records, issues, seen_record_keys
            )
        elif category in {"beam", "foundation"}:
            self._measure_linear_prism(
                element_id, source_model, level_id, category, work_section,
                material, geometry, drawing_refs, records, issues, seen_record_keys
            )
        elif category == "column":
            self._measure_column(
                element_id, source_model, level_id, category, work_section,
                material, geometry, drawing_refs, records, issues, seen_record_keys
            )
        elif category in {"door", "window"}:
            self._measure_opening(
                element_id, source_model, level_id, category, work_section,
                material, geometry, drawing_refs, records, issues, seen_record_keys
            )
        elif category == "stair":
            self._measure_stair(
                element_id, source_model, level_id, category, work_section,
                material, geometry, drawing_refs, records, issues, seen_record_keys
            )

    def _measure_wall(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        length = self._dimension(geometry, "length_m", "length")
        height = self._dimension(geometry, "height_m", "height")
        thickness = self._dimension(geometry, "thickness_m", "thickness", "width_m")

        if length:
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, "wall_length", length, QuantityUnit.METRE,
                "length_m", {"length_m": length}, drawing_refs
            )
        if length and height:
            area = length * height
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, "gross_wall_area", area,
                QuantityUnit.SQUARE_METRE, "length_m × height_m",
                {"length_m": length, "height_m": height}, drawing_refs
            )
            if thickness:
                volume = area * thickness
                self._add_calculated(
                    records, seen, element_id, source_model, level_id, category,
                    work_section, material, "wall_volume", volume,
                    QuantityUnit.CUBIC_METRE,
                    "length_m × height_m × thickness_m",
                    {
                        "length_m": length,
                        "height_m": height,
                        "thickness_m": thickness,
                    },
                    drawing_refs,
                    assumptions=("Wall treated as a solid orthogonal prism.",),
                )
                self._add_mass_if_possible(
                    element_id, source_model, level_id, category, work_section,
                    material, volume, geometry, drawing_refs, records, seen
                )
        else:
            self._missing_dimensions(
                issues, element_id, source_model, category, ("length_m", "height_m")
            )

    def _measure_plate(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        length = self._dimension(geometry, "length_m", "length")
        width = self._dimension(geometry, "width_m", "width")
        thickness = self._dimension(geometry, "thickness_m", "thickness", "depth_m")

        if length and width:
            area = length * width
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, f"{category}_area", area,
                QuantityUnit.SQUARE_METRE, "length_m × width_m",
                {"length_m": length, "width_m": width}, drawing_refs
            )
            if thickness:
                volume = area * thickness
                self._add_calculated(
                    records, seen, element_id, source_model, level_id, category,
                    work_section, material, f"{category}_volume", volume,
                    QuantityUnit.CUBIC_METRE,
                    "length_m × width_m × thickness_m",
                    {
                        "length_m": length,
                        "width_m": width,
                        "thickness_m": thickness,
                    },
                    drawing_refs,
                    assumptions=(f"{category.title()} treated as a solid rectangular plate.",),
                )
                self._add_mass_if_possible(
                    element_id, source_model, level_id, category, work_section,
                    material, volume, geometry, drawing_refs, records, seen
                )
        else:
            self._missing_dimensions(
                issues, element_id, source_model, category, ("length_m", "width_m")
            )

    def _measure_linear_prism(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        length = self._dimension(geometry, "length_m", "length")
        width = self._dimension(geometry, "width_m", "width", "breadth_m")
        height = self._dimension(
            geometry, "height_m", "height", "depth_m", "thickness_m"
        )

        if length:
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, f"{category}_length", length,
                QuantityUnit.METRE, "length_m",
                {"length_m": length}, drawing_refs
            )
        if length and width and height:
            volume = length * width * height
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, f"{category}_volume", volume,
                QuantityUnit.CUBIC_METRE,
                "length_m × width_m × height_m",
                {
                    "length_m": length,
                    "width_m": width,
                    "height_m": height,
                },
                drawing_refs,
                assumptions=(f"{category.title()} treated as a solid rectangular prism.",),
            )
            self._add_mass_if_possible(
                element_id, source_model, level_id, category, work_section,
                material, volume, geometry, drawing_refs, records, seen
            )
        elif not length:
            self._missing_dimensions(
                issues, element_id, source_model, category, ("length_m",)
            )

    def _measure_column(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        height = self._dimension(geometry, "height_m", "height", "length_m")
        width = self._dimension(geometry, "width_m", "width", "breadth_m")
        depth = self._dimension(
            geometry, "depth_m", "depth", "thickness_m", "height_section_m"
        )

        if height:
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, "column_height", height,
                QuantityUnit.METRE, "height_m",
                {"height_m": height}, drawing_refs
            )
        if height and width and depth:
            volume = height * width * depth
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, "column_volume", volume,
                QuantityUnit.CUBIC_METRE,
                "height_m × width_m × depth_m",
                {
                    "height_m": height,
                    "width_m": width,
                    "depth_m": depth,
                },
                drawing_refs,
                assumptions=("Column treated as a solid rectangular prism.",),
            )
            self._add_mass_if_possible(
                element_id, source_model, level_id, category, work_section,
                material, volume, geometry, drawing_refs, records, seen
            )
        elif not height:
            self._missing_dimensions(
                issues, element_id, source_model, category, ("height_m",)
            )

    def _measure_opening(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        width = self._dimension(geometry, "width_m", "width")
        height = self._dimension(geometry, "height_m", "height")
        if width and height:
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, f"{category}_area", width * height,
                QuantityUnit.SQUARE_METRE,
                "width_m × height_m",
                {"width_m": width, "height_m": height},
                drawing_refs,
            )
        else:
            self._missing_dimensions(
                issues, element_id, source_model, category, ("width_m", "height_m")
            )

    def _measure_stair(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        length = self._dimension(geometry, "length_m", "run_m", "length")
        width = self._dimension(geometry, "width_m", "width")
        if length and width:
            self._add_calculated(
                records, seen, element_id, source_model, level_id, category,
                work_section, material, "stair_plan_area", length * width,
                QuantityUnit.SQUARE_METRE,
                "run_m × width_m",
                {"run_m": length, "width_m": width},
                drawing_refs,
                assumptions=("Stair quantity is a horizontal plan-area estimate.",),
            )
        else:
            self._missing_dimensions(
                issues, element_id, source_model, category, ("run_m", "width_m")
            )

    def _measure_declared_quantities(
        self,
        *,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        declared: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        issues: list[QuantityIssue],
        seen_record_keys: set[tuple[str, str, str, str]],
    ) -> None:
        for quantity_type, payload in sorted(declared.items()):
            if not isinstance(payload, Mapping):
                issues.append(
                    QuantityIssue(
                        code="QTO-DECLARED-001",
                        severity="warning",
                        message=f"Declared quantity {quantity_type!r} is not an object.",
                        source_object_id=element_id,
                        source_model=source_model,
                    )
                )
                continue
            raw_value = payload.get("value")
            raw_unit = payload.get("unit")
            try:
                value = float(raw_value)
                unit = QuantityUnit(str(raw_unit))
            except (TypeError, ValueError):
                issues.append(
                    QuantityIssue(
                        code="QTO-DECLARED-002",
                        severity="warning",
                        message=f"Declared quantity {quantity_type!r} is invalid.",
                        source_object_id=element_id,
                        source_model=source_model,
                    )
                )
                continue
            if value < 0:
                issues.append(
                    QuantityIssue(
                        code="QTO-DECLARED-003",
                        severity="error",
                        message=f"Declared quantity {quantity_type!r} is negative.",
                        source_object_id=element_id,
                        source_model=source_model,
                    )
                )
                continue
            self._add_record(
                records,
                seen_record_keys,
                source_object_id=element_id,
                source_model=source_model,
                source_level_id=level_id,
                category=category,
                work_section=work_section,
                material=material,
                quantity_type=str(quantity_type),
                value=value,
                unit=unit,
                basis=MeasurementBasis.DECLARED,
                status=QuantityStatus.COMPLETE,
                formula="declared source quantity",
                inputs={"declared_value": value},
                assumptions=(),
                drawing_refs=drawing_refs,
            )

    def _add_mass_if_possible(
        self,
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        volume: float,
        geometry: Mapping[str, Any],
        drawing_refs: tuple[str, ...],
        records: list[QuantityRecord],
        seen: set[tuple[str, str, str, str]],
    ) -> None:
        density = self._dimension(
            geometry,
            "density_kg_m3",
            "material_density_kg_m3",
        )
        if not density:
            return
        self._add_calculated(
            records, seen, element_id, source_model, level_id, category,
            work_section, material, f"{category}_mass", volume * density,
            QuantityUnit.KILOGRAM,
            "volume_m3 × density_kg_m3",
            {"volume_m3": volume, "density_kg_m3": density},
            drawing_refs,
        )

    def _add_calculated(
        self,
        records: list[QuantityRecord],
        seen: set[tuple[str, str, str, str]],
        element_id: str,
        source_model: str,
        level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        quantity_type: str,
        value: float,
        unit: QuantityUnit,
        formula: str,
        inputs: dict[str, float],
        drawing_refs: tuple[str, ...],
        assumptions: tuple[str, ...] = (),
    ) -> None:
        self._add_record(
            records,
            seen,
            source_object_id=element_id,
            source_model=source_model,
            source_level_id=level_id,
            category=category,
            work_section=work_section,
            material=material,
            quantity_type=quantity_type,
            value=value,
            unit=unit,
            basis=MeasurementBasis.CALCULATED,
            status=QuantityStatus.ESTIMATED if assumptions else QuantityStatus.COMPLETE,
            formula=formula,
            inputs=inputs,
            assumptions=assumptions,
            drawing_refs=drawing_refs,
        )

    def _add_record(
        self,
        records: list[QuantityRecord],
        seen: set[tuple[str, str, str, str]],
        *,
        source_object_id: str,
        source_model: str,
        source_level_id: str | None,
        category: str,
        work_section: str,
        material: str | None,
        quantity_type: str,
        value: float,
        unit: QuantityUnit,
        basis: MeasurementBasis,
        status: QuantityStatus,
        formula: str,
        inputs: dict[str, float],
        assumptions: tuple[str, ...],
        drawing_refs: tuple[str, ...],
    ) -> None:
        if value < 0:
            return
        key = (source_model, source_object_id, quantity_type, unit.value)
        if key in seen:
            return
        seen.add(key)
        quantity_id = self._quantity_id(
            source_model, source_object_id, quantity_type, unit.value
        )
        records.append(
            QuantityRecord(
                quantity_id=quantity_id,
                source_object_id=source_object_id,
                source_model=source_model,
                source_level_id=source_level_id,
                category=category,
                work_section=work_section,
                material=material,
                quantity_type=quantity_type,
                value=round(float(value), 6),
                unit=unit,
                basis=basis,
                status=status,
                formula=formula,
                inputs={key: round(float(val), 6) for key, val in inputs.items()},
                assumptions=assumptions,
                drawing_refs=drawing_refs,
            )
        )

    @staticmethod
    def _quantity_id(
        source_model: str,
        source_object_id: str,
        quantity_type: str,
        unit: str,
    ) -> str:
        digest = hashlib.sha256(
            f"{source_model}|{source_object_id}|{quantity_type}|{unit}".encode("utf-8")
        ).hexdigest()[:20].upper()
        return f"QTO-{digest}"

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _material_name(
        material: Mapping[str, Any],
        properties: Mapping[str, Any],
    ) -> str | None:
        value = (
            material.get("name")
            or material.get("id")
            or properties.get("material")
        )
        return str(value).strip() if value not in (None, "") else None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return str(value).strip() or None

    @staticmethod
    def _dimension(data: Mapping[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        return None

    @staticmethod
    def _invalid_dimensions(data: Mapping[str, Any]) -> tuple[str, ...]:
        invalid: list[str] = []
        for key, value in data.items():
            if not (
                str(key).endswith("_m")
                or str(key).endswith("_m2")
                or str(key).endswith("_m3")
            ):
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and value <= 0:
                invalid.append(str(key))
        return tuple(invalid)

    @staticmethod
    def _missing_dimensions(
        issues: list[QuantityIssue],
        element_id: str,
        source_model: str,
        category: str,
        dimensions: tuple[str, ...],
    ) -> None:
        issues.append(
            QuantityIssue(
                code="QTO-DIM-002",
                severity="warning",
                message=(
                    f"{category.title()} lacks dimensions required for a complete "
                    f"quantity: {', '.join(dimensions)}."
                ),
                source_object_id=element_id,
                source_model=source_model,
            )
        )

    @staticmethod
    def _drawing_refs(
        element: Mapping[str, Any],
        drawing_manifest: Mapping[str, Any],
    ) -> tuple[str, ...]:
        direct = element.get("drawing_refs")
        refs: list[str] = []
        if isinstance(direct, list):
            refs.extend(str(item) for item in direct if item)

        mappings = drawing_manifest.get("element_drawing_map")
        element_id = str(element.get("id") or "")
        if isinstance(mappings, Mapping):
            mapped = mappings.get(element_id)
            if isinstance(mapped, list):
                refs.extend(str(item) for item in mapped if item)
        return tuple(sorted(set(refs)))
