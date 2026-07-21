"""Phoenix Steel Axial Design Engine â€” Wave 11 v1.0.

Consumes a verified Wave 9 reference-solver artifact and performs a narrowly
scoped, transparent axial steel resistance check.

The engine is generic and policy-based. It does not claim compliance with a
named structural design standard.
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


class SteelAxialDesignError(ValueError):
    """Raised when input falls outside the verified Wave 11 scope."""


@dataclass(frozen=True)
class SteelMemberDesignInput:
    element_id: str
    gross_area_m2: float
    yield_strength_pa: float
    ultimate_strength_pa: float
    resistance_factor_yield: float = 0.90
    resistance_factor_ultimate: float = 0.75
    design_action_factor: float = 1.00
    effective_length_m: float | None = None
    radius_of_gyration_m: float | None = None
    slenderness_limit: float | None = None
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.element_id.strip():
            raise SteelAxialDesignError("element_id is required.")
        for name, value in {
            "gross_area_m2": self.gross_area_m2,
            "yield_strength_pa": self.yield_strength_pa,
            "ultimate_strength_pa": self.ultimate_strength_pa,
            "resistance_factor_yield": self.resistance_factor_yield,
            "resistance_factor_ultimate": self.resistance_factor_ultimate,
            "design_action_factor": self.design_action_factor,
        }.items():
            if not isinstance(value, (int, float)) or value <= 0:
                raise SteelAxialDesignError(f"{name} must be positive.")

        slenderness_values = (
            self.effective_length_m,
            self.radius_of_gyration_m,
            self.slenderness_limit,
        )
        if any(value is not None for value in slenderness_values):
            if any(value is None for value in slenderness_values):
                raise SteelAxialDesignError(
                    "effective_length_m, radius_of_gyration_m and "
                    "slenderness_limit must be supplied together."
                )
            if any(not isinstance(value, (int, float)) or value <= 0
                   for value in slenderness_values):
                raise SteelAxialDesignError(
                    "Slenderness inputs must be positive."
                )


@dataclass(frozen=True)
class SteelAxialDesignConfig:
    project_id: str
    solver_results_artifact: str | Path
    output_directory: str | Path
    members: tuple[SteelMemberDesignInput, ...]
    force_zero_tolerance_n: float = 1e-6

    def validate(self) -> None:
        if not self.project_id.strip():
            raise SteelAxialDesignError("project_id is required.")
        if not Path(self.solver_results_artifact).is_file():
            raise SteelAxialDesignError(
                f"Solver result artifact does not exist: "
                f"{self.solver_results_artifact}"
            )
        if not self.members:
            raise SteelAxialDesignError(
                "At least one steel member design input is required."
            )
        if self.force_zero_tolerance_n <= 0:
            raise SteelAxialDesignError(
                "force_zero_tolerance_n must be positive."
            )
        for member in self.members:
            member.validate()
        ids = [member.element_id for member in self.members]
        if len(set(ids)) != len(ids):
            raise SteelAxialDesignError(
                "Steel member element_id values must be unique."
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
        raise SteelAxialDesignError(
            f"Unable to read solver result artifact: {path}"
        ) from exc

    if artifact.get("schema") != "phoenix-reference-solver-results-v1.0":
        raise SteelAxialDesignError(
            "Wave 11 requires phoenix-reference-solver-results-v1.0."
        )
    if artifact.get("project_id") != project_id:
        raise SteelAxialDesignError("Solver result project_id mismatch.")

    expected = artifact.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise SteelAxialDesignError(
            "Solver result SHA-256 is missing or invalid."
        )
    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual != expected:
        raise SteelAxialDesignError(
            "Solver result integrity verification failed."
        )

    solver = artifact.get("solver") or {}
    verification = artifact.get("verification") or {}
    if solver.get("execution_status") != "completed":
        raise SteelAxialDesignError(
            "Solver execution must be completed before steel design."
        )
    if not verification.get("global_equilibrium_passed"):
        raise SteelAxialDesignError(
            "Global equilibrium must pass before steel design."
        )
    if not verification.get("finite_results"):
        raise SteelAxialDesignError(
            "Solver results must be finite before steel design."
        )
    return artifact


def create_steel_axial_design_adapter(config: SteelAxialDesignConfig):
    """Return a PXO-compatible Wave 11 steel axial design adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "steel_axial_design":
            raise SteelAxialDesignError(
                f"Steel axial adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise SteelAxialDesignError("Runtime project_id mismatch.")
        if not plan_fingerprint.strip():
            raise SteelAxialDesignError("plan_fingerprint is required.")

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
                raise SteelAxialDesignError(
                    f"No solver result found for element {member.element_id}."
                )

            axial_force_n = float(solver_member["axial_force_n"])
            if not math.isfinite(axial_force_n):
                raise SteelAxialDesignError(
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

            yield_resistance_n = (
                member.resistance_factor_yield
                * member.gross_area_m2
                * member.yield_strength_pa
            )
            ultimate_resistance_n = (
                member.resistance_factor_ultimate
                * member.gross_area_m2
                * member.ultimate_strength_pa
            )
            axial_resistance_n = min(
                yield_resistance_n,
                ultimate_resistance_n,
            )

            slenderness = None
            slenderness_passed = None
            buckling_verified = False
            if member.effective_length_m is not None:
                slenderness = (
                    member.effective_length_m
                    / member.radius_of_gyration_m
                )
                slenderness_passed = (
                    slenderness <= member.slenderness_limit
                )

            utilization = (
                design_force_n / axial_resistance_n
                if axial_resistance_n > 0
                else math.inf
            )
            strength_passed = utilization <= 1.0 + 1e-12
            member_passed = strength_passed and (
                slenderness_passed is not False
            )
            all_passed = all_passed and member_passed

            member_results.append(
                {
                    "element_id": member.element_id,
                    "source_reference": member.source_reference,
                    "action_mode": action_mode,
                    "characteristic_axial_force_n": axial_force_n,
                    "design_axial_force_n": design_force_n,
                    "gross_area_m2": member.gross_area_m2,
                    "yield_strength_pa": member.yield_strength_pa,
                    "ultimate_strength_pa": member.ultimate_strength_pa,
                    "yield_resistance_n": yield_resistance_n,
                    "ultimate_resistance_n": ultimate_resistance_n,
                    "governing_axial_resistance_n": axial_resistance_n,
                    "utilization": utilization,
                    "slenderness": {
                        "effective_length_m": member.effective_length_m,
                        "radius_of_gyration_m": member.radius_of_gyration_m,
                        "limit": member.slenderness_limit,
                        "value": slenderness,
                        "passed": slenderness_passed,
                        "buckling_resistance_verified": buckling_verified,
                    },
                    "checks": {
                        "axial_strength_passed": strength_passed,
                        "slenderness_screen_passed": slenderness_passed,
                        "member_passed": member_passed,
                    },
                }
            )

        artifact = {
            "schema": "phoenix-steel-axial-design-results-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "solver_results_artifact": results_path.as_posix(),
            "solver_results_artifact_sha256": solver_results[
                "artifact_sha256"
            ],
            "design_basis": {
                "type": "generic_policy_based_axial_steel_check",
                "named_code_compliance": None,
                "units": "SI",
                "scope": (
                    "gross-section axial strength plus optional slenderness "
                    "screen; no buckling resistance model"
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
                "buckling_resistance_not_verified": True,
                "local_buckling_not_verified": True,
                "lateral_torsional_buckling_not_verified": True,
                "connection_design_not_verified": True,
                "fatigue_not_verified": True,
                "fire_resistance_not_verified": True,
                "fracture_not_verified": True,
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
            output_directory / "steel_axial_design_results_v1_0.json"
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
                f"steel-axial-design-results:{artifact_hash}",
                f"steel-members:{len(member_results)}",
                f"steel-design-all-passed:{str(all_passed).lower()}",
            ),
            metadata={
                "adapter": "phoenix_steel_axial_design_v1_0",
                "artifact_sha256": artifact_hash,
                "member_count": len(member_results),
                "all_members_passed": all_passed,
                "named_code_compliance": False,
            },
        )

    return adapter
