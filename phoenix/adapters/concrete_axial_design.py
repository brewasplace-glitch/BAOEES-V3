"""Phoenix Concrete Axial Design Engine â€” Wave 10 v1.0.1.

Consumes a verified Wave 9 reference-solver result and performs a deliberately
limited, transparent axial reinforced-concrete sizing check.

This engine is policy-based and is not presented as compliance with any named
structural code. Unsupported or incomplete design situations are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Mapping

from phoenix.orchestration.runtime import AdapterResult


class ConcreteAxialDesignError(ValueError):
    """Raised when a design request violates the verified Wave 10 scope."""


@dataclass(frozen=True)
class ConcreteMemberDesignInput:
    element_id: str
    gross_area_m2: float
    concrete_strength_pa: float
    reinforcement_yield_strength_pa: float
    minimum_reinforcement_ratio: float = 0.002
    maximum_reinforcement_ratio: float = 0.04
    concrete_resistance_factor: float = 0.60
    steel_resistance_factor: float = 0.87
    design_action_factor: float = 1.00
    bar_diameter_m: float = 0.016
    minimum_bar_count: int = 4
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.element_id.strip():
            raise ConcreteAxialDesignError("element_id is required.")
        positive_values = {
            "gross_area_m2": self.gross_area_m2,
            "concrete_strength_pa": self.concrete_strength_pa,
            "reinforcement_yield_strength_pa": self.reinforcement_yield_strength_pa,
            "concrete_resistance_factor": self.concrete_resistance_factor,
            "steel_resistance_factor": self.steel_resistance_factor,
            "design_action_factor": self.design_action_factor,
            "bar_diameter_m": self.bar_diameter_m,
        }
        for name, value in positive_values.items():
            if not isinstance(value, (int, float)) or value <= 0:
                raise ConcreteAxialDesignError(f"{name} must be positive.")

        if not 0 <= self.minimum_reinforcement_ratio < 1:
            raise ConcreteAxialDesignError(
                "minimum_reinforcement_ratio must be in [0, 1)."
            )
        if not 0 < self.maximum_reinforcement_ratio < 1:
            raise ConcreteAxialDesignError(
                "maximum_reinforcement_ratio must be in (0, 1)."
            )
        if self.minimum_reinforcement_ratio > self.maximum_reinforcement_ratio:
            raise ConcreteAxialDesignError(
                "minimum_reinforcement_ratio cannot exceed maximum."
            )
        if self.minimum_bar_count <= 0:
            raise ConcreteAxialDesignError("minimum_bar_count must be positive.")


@dataclass(frozen=True)
class ConcreteAxialDesignConfig:
    project_id: str
    solver_results_artifact: str | Path
    output_directory: str | Path
    members: tuple[ConcreteMemberDesignInput, ...]
    force_zero_tolerance_n: float = 1e-6

    def validate(self) -> None:
        if not self.project_id.strip():
            raise ConcreteAxialDesignError("project_id is required.")
        if not Path(self.solver_results_artifact).is_file():
            raise ConcreteAxialDesignError(
                f"Solver result artifact does not exist: "
                f"{self.solver_results_artifact}"
            )
        if not self.members:
            raise ConcreteAxialDesignError(
                "At least one concrete member design input is required."
            )
        if self.force_zero_tolerance_n <= 0:
            raise ConcreteAxialDesignError(
                "force_zero_tolerance_n must be positive."
            )
        for member in self.members:
            member.validate()
        element_ids = [member.element_id for member in self.members]
        if len(set(element_ids)) != len(element_ids):
            raise ConcreteAxialDesignError(
                "Concrete member element_id values must be unique."
            )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _read_verified_results(path: Path, project_id: str) -> Mapping[str, Any]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConcreteAxialDesignError(
            f"Unable to read solver result artifact: {path}"
        ) from exc

    if artifact.get("schema") != "phoenix-reference-solver-results-v1.0":
        raise ConcreteAxialDesignError(
            "Wave 10 requires phoenix-reference-solver-results-v1.0."
        )
    if artifact.get("project_id") != project_id:
        raise ConcreteAxialDesignError("Solver result project_id mismatch.")

    expected = artifact.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ConcreteAxialDesignError(
            "Solver result SHA-256 is missing or invalid."
        )
    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ConcreteAxialDesignError(
            "Solver result integrity verification failed."
        )

    solver = artifact.get("solver") or {}
    if solver.get("execution_status") != "completed":
        raise ConcreteAxialDesignError(
            "Solver execution must be completed before concrete design."
        )
    verification = artifact.get("verification") or {}
    if not verification.get("global_equilibrium_passed"):
        raise ConcreteAxialDesignError(
            "Global equilibrium must pass before concrete design."
        )
    if not verification.get("finite_results"):
        raise ConcreteAxialDesignError(
            "Solver results must be finite before concrete design."
        )

    return artifact


def _ceil_to_increment(value: float, increment: float) -> float:
    return math.ceil((value - 1e-15) / increment) * increment


def create_concrete_axial_design_adapter(
    config: ConcreteAxialDesignConfig,
):
    """Return a PXO-compatible Wave 10 concrete axial design adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "concrete_axial_design":
            raise ConcreteAxialDesignError(
                f"Concrete axial adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise ConcreteAxialDesignError("Runtime project_id mismatch.")
        if not plan_fingerprint.strip():
            raise ConcreteAxialDesignError(
                "plan_fingerprint is required."
            )

        results_path = Path(config.solver_results_artifact)
        solver_results = _read_verified_results(results_path, project_id)

        result_by_element = {
            item["element_id"]: item
            for item in solver_results.get("element_results") or []
        }

        member_results: list[dict[str, Any]] = []
        all_passed = True

        for member in config.members:
            solver_member = result_by_element.get(member.element_id)
            if not solver_member:
                raise ConcreteAxialDesignError(
                    f"No solver result found for element {member.element_id}."
                )

            axial_force_n = float(solver_member["axial_force_n"])
            if not math.isfinite(axial_force_n):
                raise ConcreteAxialDesignError(
                    f"Non-finite axial force for {member.element_id}."
                )

            design_force_n = abs(axial_force_n) * member.design_action_factor
            action_mode = (
                "compression"
                if axial_force_n < -config.force_zero_tolerance_n
                else "tension"
                if axial_force_n > config.force_zero_tolerance_n
                else "near_zero"
            )

            bar_area_m2 = math.pi * member.bar_diameter_m**2 / 4.0
            minimum_steel_area_m2 = (
                member.minimum_reinforcement_ratio * member.gross_area_m2
            )
            maximum_steel_area_m2 = (
                member.maximum_reinforcement_ratio * member.gross_area_m2
            )

            design_concrete_resistance_pa = (
                member.concrete_resistance_factor
                * member.concrete_strength_pa
            )
            design_steel_resistance_pa = (
                member.steel_resistance_factor
                * member.reinforcement_yield_strength_pa
            )

            if action_mode == "compression":
                concrete_capacity_n = (
                    design_concrete_resistance_pa * member.gross_area_m2
                )
                steel_area_from_action_m2 = max(
                    0.0,
                    (design_force_n - concrete_capacity_n)
                    / design_steel_resistance_pa,
                )
            elif action_mode == "tension":
                concrete_capacity_n = 0.0
                steel_area_from_action_m2 = (
                    design_force_n / design_steel_resistance_pa
                )
            else:
                concrete_capacity_n = (
                    design_concrete_resistance_pa * member.gross_area_m2
                )
                steel_area_from_action_m2 = 0.0

            required_steel_area_m2 = max(
                minimum_steel_area_m2,
                steel_area_from_action_m2,
            )
            required_bar_count = max(
                member.minimum_bar_count,
                math.ceil(required_steel_area_m2 / bar_area_m2),
            )
            provided_steel_area_m2 = required_bar_count * bar_area_m2
            provided_ratio = (
                provided_steel_area_m2 / member.gross_area_m2
            )
            maximum_ratio_passed = (
                provided_steel_area_m2 <= maximum_steel_area_m2 + 1e-15
            )

            if action_mode == "compression":
                nominal_capacity_n = (
                    concrete_capacity_n
                    + design_steel_resistance_pa * provided_steel_area_m2
                )
            elif action_mode == "tension":
                nominal_capacity_n = (
                    design_steel_resistance_pa * provided_steel_area_m2
                )
            else:
                nominal_capacity_n = (
                    concrete_capacity_n
                    + design_steel_resistance_pa * provided_steel_area_m2
                )

            utilization = (
                design_force_n / nominal_capacity_n
                if nominal_capacity_n > 0
                else math.inf
            )
            capacity_passed = utilization <= 1.0 + 1e-12
            member_passed = maximum_ratio_passed and capacity_passed
            all_passed = all_passed and member_passed

            member_results.append(
                {
                    "element_id": member.element_id,
                    "source_reference": member.source_reference,
                    "action_mode": action_mode,
                    "characteristic_axial_force_n": axial_force_n,
                    "design_axial_force_n": design_force_n,
                    "gross_area_m2": member.gross_area_m2,
                    "concrete_strength_pa": member.concrete_strength_pa,
                    "reinforcement_yield_strength_pa": (
                        member.reinforcement_yield_strength_pa
                    ),
                    "design_concrete_resistance_pa": (
                        design_concrete_resistance_pa
                    ),
                    "design_steel_resistance_pa": (
                        design_steel_resistance_pa
                    ),
                    "minimum_steel_area_m2": minimum_steel_area_m2,
                    "steel_area_from_action_m2": (
                        steel_area_from_action_m2
                    ),
                    "required_steel_area_m2": required_steel_area_m2,
                    "bar_diameter_m": member.bar_diameter_m,
                    "required_bar_count": required_bar_count,
                    "provided_steel_area_m2": provided_steel_area_m2,
                    "provided_reinforcement_ratio": provided_ratio,
                    "maximum_steel_area_m2": maximum_steel_area_m2,
                    "nominal_axial_capacity_n": nominal_capacity_n,
                    "utilization": utilization,
                    "checks": {
                        "capacity_passed": capacity_passed,
                        "maximum_reinforcement_ratio_passed": (
                            maximum_ratio_passed
                        ),
                        "member_passed": member_passed,
                    },
                }
            )

        artifact = {
            "schema": "phoenix-concrete-axial-design-results-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "solver_results_artifact": results_path.as_posix(),
            "solver_results_artifact_sha256": solver_results[
                "artifact_sha256"
            ],
            "design_basis": {
                "type": "generic_policy_based_axial_rc_sizing",
                "named_code_compliance": None,
                "units": "SI",
                "scope": (
                    "axial force only; no bending, shear, slenderness, "
                    "buckling, second-order effects, detailing or durability"
                ),
            },
            "member_results": member_results,
            "summary": {
                "member_count": len(member_results),
                "passed_member_count": sum(
                    1
                    for result in member_results
                    if result["checks"]["member_passed"]
                ),
                "failed_member_count": sum(
                    1
                    for result in member_results
                    if not result["checks"]["member_passed"]
                ),
                "all_members_passed": all_passed,
            },
            "claims_policy": {
                "named_code_compliance_not_claimed": True,
                "bending_not_verified": True,
                "shear_not_verified": True,
                "slenderness_not_verified": True,
                "buckling_not_verified": True,
                "second_order_effects_not_verified": True,
                "crack_control_not_verified": True,
                "detailing_not_verified": True,
                "durability_not_verified": True,
                "fire_resistance_not_verified": True,
                "competent_structural_engineer_review_required": True,
            },
        }

        artifact_hash = sha256(
            _canonical_json(artifact).encode("utf-8")
        ).hexdigest()
        artifact["artifact_sha256"] = artifact_hash

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = (
            output_directory / "concrete_axial_design_results_v1_0.json"
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_directory,
            delete=False,
            suffix=".tmp",
        ) as handle:
            json.dump(artifact, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(destination)

        return AdapterResult(
            outputs=(destination.as_posix(),),
            evidence=(
                f"concrete-axial-design-results:{artifact_hash}",
                f"concrete-members:{len(member_results)}",
                f"concrete-design-all-passed:{str(all_passed).lower()}",
            ),
            metadata={
                "adapter": "phoenix_concrete_axial_design_v1_0_1",
                "artifact_sha256": artifact_hash,
                "member_count": len(member_results),
                "all_members_passed": all_passed,
                "named_code_compliance": False,
            },
        )

    return adapter
