"""Preliminary structural-model generation and solver handoffs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .models import (
    AnalysisHandoff,
    LoadCase,
    LoadCombination,
    StructuralMember,
    StructuralModel,
    StructuralValidationIssue,
)


class StructuralDesignEngine:
    SCHEMA_VERSION = "phoenix.structural-model/1.0"
    VERSION = "1.0.0"
    STRUCTURAL_CATEGORIES = {
        "foundation",
        "column",
        "beam",
        "wall",
        "slab",
        "roof",
        "stair",
    }
    SUPPORTED_ENGINES = {"openseespy", "calculix", "scia"}

    def create_model(self, building_model: Mapping[str, Any] | Any) -> StructuralModel:
        data = self._normalise_model(building_model)
        members: list[StructuralMember] = []
        supports: list[dict[str, Any]] = []
        for item in list(data.get("elements") or []):
            if not isinstance(item, Mapping):
                continue
            category = str(item.get("category") or "generic").lower()
            if category not in self.STRUCTURAL_CATEGORIES:
                continue
            source_id = str(item.get("id") or "")
            if not source_id:
                continue
            geometry = item.get("geometry") if isinstance(item.get("geometry"), Mapping) else {}
            material = item.get("material") if isinstance(item.get("material"), Mapping) else {}
            properties = item.get("properties") if isinstance(item.get("properties"), Mapping) else {}
            length_value = geometry.get("length_m")
            length = float(length_value) if isinstance(length_value, (int, float)) and not isinstance(length_value, bool) else None
            material_name = str(material.get("name") or self._default_material(category))
            member = StructuralMember(
                id=f"STR-{source_id}",
                source_element_id=source_id,
                member_type=category,
                level_id=str(item.get("level_id")) if item.get("level_id") else None,
                material_name=material_name,
                length_m=length,
                section=dict(properties.get("section") or {}) if isinstance(properties.get("section"), Mapping) else {},
                properties={
                    "geometry": dict(geometry),
                    "source_properties": dict(properties),
                },
            )
            members.append(member)
            if category == "foundation":
                supports.append({
                    "id": f"SUP-{source_id}",
                    "member_id": member.id,
                    "type": "foundation_interface",
                    "restraints": ["UX", "UY", "UZ"],
                    "requires_geotechnical_validation": True,
                })

        load_cases = [
            LoadCase("LC-G", "Permanent actions", "permanent"),
            LoadCase("LC-Q", "Imposed actions", "variable"),
            LoadCase("LC-W", "Wind actions", "environmental"),
        ]
        combinations = [
            LoadCombination(
                "COMB-ULS-CONCEPT",
                "Concept ultimate combination",
                "ULS",
                {"LC-G": 1.0, "LC-Q": 1.0, "LC-W": 1.0},
                True,
            ),
            LoadCombination(
                "COMB-SLS-CONCEPT",
                "Concept serviceability combination",
                "SLS",
                {"LC-G": 1.0, "LC-Q": 1.0, "LC-W": 1.0},
                True,
            ),
        ]
        model = StructuralModel(
            schema_version=self.SCHEMA_VERSION,
            engine_version=self.VERSION,
            project_id=str(data.get("project_id") or "PHX-PROJECT-UNSPECIFIED"),
            members=members,
            load_cases=load_cases,
            combinations=combinations,
            supports=supports,
            metadata={
                "design_status": "preliminary-non-certifying",
                "jurisdiction_factors_applied": False,
                "professional_review_required": True,
                "source_model_fingerprint_sha256": self.fingerprint(data),
            },
        )
        model.metadata["structural_model_fingerprint_sha256"] = self.fingerprint(model.to_dict())
        return model

    def validate(self, model: StructuralModel) -> list[StructuralValidationIssue]:
        issues: list[StructuralValidationIssue] = []
        ids = [member.id for member in model.members]
        if not model.members:
            issues.append(
                StructuralValidationIssue(
                    "SDE-MEMBER-001",
                    "error",
                    "No structural members were derived from the building model.",
                    model.project_id,
                )
            )
        if len(ids) != len(set(ids)):
            issues.append(
                StructuralValidationIssue(
                    "SDE-MEMBER-002",
                    "critical",
                    "Structural member identifiers are not unique.",
                    model.project_id,
                )
            )
        for member in model.members:
            if member.length_m is not None and member.length_m <= 0:
                issues.append(
                    StructuralValidationIssue(
                        "SDE-GEOMETRY-001",
                        "error",
                        "Structural member length must be greater than zero.",
                        member.id,
                    )
                )
            if not member.material_name.strip():
                issues.append(
                    StructuralValidationIssue(
                        "SDE-MATERIAL-001",
                        "error",
                        "Structural member has no material assignment.",
                        member.id,
                    )
                )
        if not model.supports:
            issues.append(
                StructuralValidationIssue(
                    "SDE-SUPPORT-001",
                    "warning",
                    "No foundation interface supports are present.",
                    model.project_id,
                )
            )
        if not model.metadata.get("jurisdiction_factors_applied"):
            issues.append(
                StructuralValidationIssue(
                    "SDE-CODE-001",
                    "warning",
                    "Load factors are placeholders until a jurisdiction rulepack is selected.",
                    model.project_id,
                )
            )
        return issues

    def create_handoff(
        self,
        model: StructuralModel,
        engine: str,
        structural_model_path: str | Path,
    ) -> AnalysisHandoff:
        engine_key = engine.lower().strip()
        if engine_key not in self.SUPPORTED_ENGINES:
            raise ValueError(f"Unsupported structural analysis engine: {engine}")
        config = {
            "openseespy": (
                ("generate_node_member_script", "run_linear_static_analysis"),
                ("analysis_results.json", "member_forces.csv"),
                ("OpenSeesPy",),
            ),
            "calculix": (
                ("generate_inp_model", "run_solver"),
                ("results.frd", "solver_log.txt"),
                ("CalculiX ccx",),
            ),
            "scia": (
                ("generate_exchange_manifest", "open_controlled_handoff"),
                ("scia_result_manifest.json",),
                ("SCIA Engineer",),
            ),
        }[engine_key]
        return AnalysisHandoff(
            schema_version="phoenix.structural-analysis-handoff/1.0",
            engine=engine_key,
            project_id=model.project_id,
            structural_model_path=str(Path(structural_model_path)),
            requested_actions=tuple(config[0]),
            expected_outputs=tuple(config[1]),
            prerequisites=tuple(config[2]),
            non_certifying=True,
        )

    def export_model(self, model: StructuralModel, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = model.to_dict()
        data["validation_issues"] = [issue.to_dict() for issue in self.validate(model)]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def export_handoff(self, handoff: AnalysisHandoff, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(handoff.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
        raise TypeError("building_model must be a mapping or expose to_dict().")

    @staticmethod
    def _default_material(category: str) -> str:
        return {
            "foundation": "concrete",
            "column": "steel",
            "beam": "steel",
            "wall": "masonry",
            "slab": "concrete",
            "roof": "steel",
            "stair": "concrete",
        }.get(category, "unspecified")

    @staticmethod
    def fingerprint(data: Mapping[str, Any]) -> str:
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
