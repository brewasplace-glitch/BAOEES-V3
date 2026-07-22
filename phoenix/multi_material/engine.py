"""Multi-material structural alternative generator for Project Phoenix.

Wave 15.2 converts supplied material/system candidates into deterministic
engineering-review variants. It does not replace code-specific member design.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ENGINE_ID = "phoenix.multi_material_design.wave15_2"
ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"


class MultiMaterialError(ValueError):
    """Raised when Wave 15.2 input is invalid."""


@dataclass(frozen=True)
class MaterialCandidate:
    material_id: str
    family: str
    density_kg_m3: float
    embodied_carbon_kgco2e_kg: float
    cost_per_kg: float
    strength_mpa: float
    durability_score: float = 0.5
    constructability_score: float = 0.5
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.material_id.strip():
            raise MultiMaterialError("material_id must not be empty.")
        if self.family not in {"concrete", "steel", "timber", "masonry", "other"}:
            raise MultiMaterialError(f"Unsupported material family: {self.family}")
        numeric_positive = {
            "density_kg_m3": self.density_kg_m3,
            "strength_mpa": self.strength_mpa,
        }
        numeric_nonnegative = {
            "embodied_carbon_kgco2e_kg": self.embodied_carbon_kgco2e_kg,
            "cost_per_kg": self.cost_per_kg,
        }
        for name, value in numeric_positive.items():
            if not math.isfinite(value) or value <= 0:
                raise MultiMaterialError(f"{name} must be finite and positive.")
        for name, value in numeric_nonnegative.items():
            if not math.isfinite(value) or value < 0:
                raise MultiMaterialError(f"{name} must be finite and non-negative.")
        for name, value in {
            "durability_score": self.durability_score,
            "constructability_score": self.constructability_score,
        }.items():
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise MultiMaterialError(f"{name} must be between 0 and 1.")


@dataclass(frozen=True)
class SystemCandidate:
    system_id: str
    required_family: str
    volume_m3: float
    design_resistance_kn: float
    span_m: float
    element_count: int = 1
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.system_id.strip():
            raise MultiMaterialError("system_id must not be empty.")
        if self.required_family not in {
            "concrete", "steel", "timber", "masonry", "any"
        }:
            raise MultiMaterialError(
                f"Unsupported required_family: {self.required_family}"
            )
        for name, value in {
            "volume_m3": self.volume_m3,
            "design_resistance_kn": self.design_resistance_kn,
            "span_m": self.span_m,
        }.items():
            if not math.isfinite(value) or value <= 0:
                raise MultiMaterialError(f"{name} must be finite and positive.")
        if self.element_count <= 0:
            raise MultiMaterialError("element_count must be positive.")


@dataclass(frozen=True)
class DesignContext:
    project_id: str
    design_action_kn: float
    maximum_utilization: float = 1.0
    permitted_families: Sequence[str] = (
        "concrete", "steel", "timber", "masonry", "other"
    )

    def validate(self) -> None:
        if not self.project_id.strip():
            raise MultiMaterialError("project_id must not be empty.")
        if not math.isfinite(self.design_action_kn) or self.design_action_kn <= 0:
            raise MultiMaterialError("design_action_kn must be finite and positive.")
        if (
            not math.isfinite(self.maximum_utilization)
            or self.maximum_utilization <= 0
        ):
            raise MultiMaterialError(
                "maximum_utilization must be finite and positive."
            )


class MultiMaterialDesignEngine:
    """Generate comparable structural alternatives from supplied candidates."""

    @staticmethod
    def _canonical_json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def _digest(cls, value: Any) -> str:
        return sha256(cls._canonical_json(value).encode("utf-8")).hexdigest()

    def generate(
        self,
        *,
        context: DesignContext,
        materials: Iterable[MaterialCandidate],
        systems: Iterable[SystemCandidate],
    ) -> dict[str, Any]:
        context.validate()
        material_list = sorted(list(materials), key=lambda x: x.material_id)
        system_list = sorted(list(systems), key=lambda x: x.system_id)
        if not material_list or not system_list:
            raise MultiMaterialError(
                "At least one material and one system candidate are required."
            )

        material_ids: set[str] = set()
        for material in material_list:
            material.validate()
            if material.material_id in material_ids:
                raise MultiMaterialError(
                    f"Duplicate material_id: {material.material_id}"
                )
            material_ids.add(material.material_id)

        system_ids: set[str] = set()
        for system in system_list:
            system.validate()
            if system.system_id in system_ids:
                raise MultiMaterialError(f"Duplicate system_id: {system.system_id}")
            system_ids.add(system.system_id)

        variants: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []

        for system, material in itertools.product(system_list, material_list):
            variant_id = f"{system.system_id}__{material.material_id}"
            reasons: list[str] = []
            if material.family not in set(context.permitted_families):
                reasons.append("family_not_permitted")
            if (
                system.required_family != "any"
                and material.family != system.required_family
            ):
                reasons.append("family_incompatible")

            mass_kg = system.volume_m3 * material.density_kg_m3 * system.element_count
            utilization = context.design_action_kn / system.design_resistance_kn
            if utilization > context.maximum_utilization:
                reasons.append("utilization_exceeded")

            record = {
                "variant_id": variant_id,
                "system_id": system.system_id,
                "material_id": material.material_id,
                "material_family": material.family,
                "design_action_kn": context.design_action_kn,
                "design_resistance_kn": system.design_resistance_kn,
                "utilization": round(utilization, 9),
                "mass_kg": round(mass_kg, 6),
                "cost": round(mass_kg * material.cost_per_kg, 6),
                "carbon_kgco2e": round(
                    mass_kg * material.embodied_carbon_kgco2e_kg, 6
                ),
                "strength_mpa": material.strength_mpa,
                "durability_score": material.durability_score,
                "constructability_score": material.constructability_score,
                "span_m": system.span_m,
                "element_count": system.element_count,
                "attributes": {
                    "material": dict(material.attributes),
                    "system": dict(system.attributes),
                },
            }
            if reasons:
                record["rejection_reasons"] = reasons
                rejected.append(record)
            else:
                variants.append(record)

        variants.sort(key=lambda x: x["variant_id"])
        rejected.sort(key=lambda x: x["variant_id"])
        if not variants:
            raise MultiMaterialError("No feasible multi-material variants generated.")

        family_summary: dict[str, int] = {}
        for variant in variants:
            family = variant["material_family"]
            family_summary[family] = family_summary.get(family, 0) + 1

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION},
            "project_id": context.project_id,
            "status": "multi_material_variants_generated",
            "context": asdict(context),
            "feasible_variant_count": len(variants),
            "rejected_variant_count": len(rejected),
            "family_summary": dict(sorted(family_summary.items())),
            "variants": variants,
            "rejected_variants": rejected,
            "optimization_contract": {
                "target_engine": "phoenix.optimization_core.wave15_1",
                "metric_mapping": {
                    "cost": "cost",
                    "carbon": "carbon_kgco2e",
                    "mass": "mass_kg",
                    "safety": "inverse utilization; downstream policy required",
                },
            },
            "limitations": [
                "Uses supplied design resistance and material factors.",
                "Does not perform code-specific member sizing or connection design.",
                "Does not certify structural safety or regulatory compliance.",
                "Cost and carbon factors require project-specific source verification.",
                "Generated variants require review by qualified engineers.",
            ],
        }
        payload["evidence"] = {
            "algorithm": "sha256",
            "payload_sha256": self._digest(payload),
        }
        return payload

    def write_result(
        self,
        *,
        context: DesignContext,
        materials: Iterable[MaterialCandidate],
        systems: Iterable[SystemCandidate],
        destination: str | Path,
    ) -> Path:
        result = self.generate(
            context=context,
            materials=materials,
            systems=systems,
        )
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path
