"""Deterministic architectural drawing-package generation."""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any, Mapping

from .models import DrawingPackage, DrawingSheet, DrawingType


class ArchitecturalDrawingEngine:
    SCHEMA_VERSION = "phoenix.architectural-drawing-package/1.0"
    VERSION = "1.0.0"

    def create_package(
        self,
        model: Mapping[str, Any] | Any,
        *,
        plan_scale: int = 100,
        elevation_scale: int = 100,
        section_scale: int = 100,
    ) -> DrawingPackage:
        for name, scale in {
            "plan_scale": plan_scale,
            "elevation_scale": elevation_scale,
            "section_scale": section_scale,
        }.items():
            if not isinstance(scale, int) or isinstance(scale, bool) or scale <= 0:
                raise ValueError(f"{name} must be a positive integer.")

        data = self._normalise_model(model)
        project_id = str(data.get("project_id") or "PHX-PROJECT-UNSPECIFIED")
        project_name = str(data.get("name") or project_id)
        levels = list(data.get("levels") or [])
        elements = list(data.get("elements") or [])
        spaces = list(data.get("spaces") or [])

        sheets: list[DrawingSheet] = [
            DrawingSheet(
                id="SHEET-A000",
                number="A000",
                title="Site and drawing index",
                drawing_type=DrawingType.SITE,
                scale_denominator=500,
                model_object_ids=tuple(
                    str(item.get("id"))
                    for item in elements
                    if isinstance(item, Mapping) and item.get("category") == "site"
                ),
            )
        ]

        for index, level in enumerate(sorted(levels, key=self._level_sort_key), start=1):
            level_id = str(level.get("id") or f"LVL-{index:02d}")
            ids = tuple(
                str(item.get("id"))
                for item in elements + spaces
                if isinstance(item, Mapping) and item.get("level_id") == level_id and item.get("id")
            )
            sheets.append(
                DrawingSheet(
                    id=f"SHEET-A1{index:02d}",
                    number=f"A1{index:02d}",
                    title=f"Floor plan — {level.get('name') or level_id}",
                    drawing_type=DrawingType.PLAN,
                    scale_denominator=plan_scale,
                    level_id=level_id,
                    model_object_ids=ids,
                )
            )

        for index, direction in enumerate(("north", "east", "south", "west"), start=1):
            sheets.append(
                DrawingSheet(
                    id=f"SHEET-A2{index:02d}",
                    number=f"A2{index:02d}",
                    title=f"Elevation — {direction.title()}",
                    drawing_type=DrawingType.ELEVATION,
                    scale_denominator=elevation_scale,
                    view_direction=direction,
                    model_object_ids=tuple(
                        str(item.get("id"))
                        for item in elements
                        if isinstance(item, Mapping) and item.get("id")
                    ),
                )
            )

        for index, section_name in enumerate(("A-A", "B-B"), start=1):
            sheets.append(
                DrawingSheet(
                    id=f"SHEET-A3{index:02d}",
                    number=f"A3{index:02d}",
                    title=f"Building section — {section_name}",
                    drawing_type=DrawingType.SECTION,
                    scale_denominator=section_scale,
                    view_direction=section_name,
                    model_object_ids=tuple(
                        str(item.get("id"))
                        for item in elements
                        if isinstance(item, Mapping) and item.get("id")
                    ),
                )
            )

        sheets.append(
            DrawingSheet(
                id="SHEET-A401",
                number="A401",
                title="Door, window and room schedules",
                drawing_type=DrawingType.SCHEDULE,
                scale_denominator=1,
                model_object_ids=tuple(
                    str(item.get("id"))
                    for item in elements + spaces
                    if isinstance(item, Mapping) and item.get("id")
                ),
            )
        )

        package = DrawingPackage(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=project_id,
            project_name=project_name,
            sheets=sheets,
            metadata={
                "model_fingerprint_sha256": self.fingerprint_model(data),
                "drawing_status": "concept-coordination",
                "certified_for_permit_submission": False,
                "sheet_count": len(sheets),
            },
        )
        package.metadata["package_fingerprint_sha256"] = self.fingerprint_package(package)
        return package

    def export_manifest(self, package: DrawingPackage, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(package.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def export_plan_svg(
        self,
        model: Mapping[str, Any] | Any,
        level_id: str,
        output_path: str | Path,
    ) -> Path:
        data = self._normalise_model(model)
        elements = [
            item
            for item in list(data.get("elements") or [])
            if isinstance(item, Mapping) and item.get("level_id") == level_id
        ]
        scale = 40.0
        margin = 60.0
        width = 1120
        height = 760
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect x="0" y="0" width="1120" height="760" fill="white"/>',
            '<g fill="none" stroke="black" stroke-width="2">',
        ]
        fallback_x = 0.0
        for item in elements:
            geometry = item.get("geometry") if isinstance(item.get("geometry"), Mapping) else {}
            x = float(geometry.get("x_m", fallback_x))
            y = float(geometry.get("y_m", 0.0))
            length = max(float(geometry.get("length_m", geometry.get("width_m", 2.0))), 0.1)
            depth = max(float(geometry.get("depth_m", geometry.get("thickness_m", 0.2))), 0.1)
            fallback_x += length + 0.5
            sx = margin + x * scale
            sy = margin + y * scale
            sw = length * scale
            sh = depth * scale
            label = html.escape(str(item.get("id") or "element"))
            lines.append(f'<rect x="{sx:.2f}" y="{sy:.2f}" width="{sw:.2f}" height="{sh:.2f}"/>')
            lines.append(f'<text x="{sx:.2f}" y="{max(sy - 5, 15):.2f}" fill="black" stroke="none" font-size="12">{label}</text>')
        lines.extend([
            '</g>',
            f'<text x="60" y="730" fill="black" font-size="18">Concept plan — {html.escape(level_id)}</text>',
            '</svg>',
        ])
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    @staticmethod
    def _normalise_model(model: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(model, Mapping):
            return dict(model)
        to_dict = getattr(model, "to_dict", None)
        if callable(to_dict):
            data = to_dict()
            if isinstance(data, Mapping):
                return dict(data)
        raise TypeError("model must be a mapping or expose to_dict().")

    @staticmethod
    def _level_sort_key(level: Any) -> tuple[float, str]:
        if not isinstance(level, Mapping):
            return (0.0, "")
        try:
            elevation = float(level.get("elevation_m", 0.0))
        except (TypeError, ValueError):
            elevation = 0.0
        return (elevation, str(level.get("id") or ""))

    @staticmethod
    def fingerprint_model(data: Mapping[str, Any]) -> str:
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def fingerprint_package(package: DrawingPackage) -> str:
        data = package.to_dict()
        data.get("metadata", {}).pop("package_fingerprint_sha256", None)
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
