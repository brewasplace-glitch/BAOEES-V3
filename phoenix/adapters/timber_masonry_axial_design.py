"""Phoenix Timber & Masonry Axial Design Engine â€” Wave 12 v1.0.

Consumes a verified Wave 9 reference-solver artifact and performs narrowly
scoped, transparent axial resistance checks for timber and masonry members.

The checks are generic and policy-based. They do not claim compliance with a
named design standard.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Literal, Mapping

from phoenix.orchestration.runtime import AdapterResult


class TimberMasonryAxialDesignError(ValueError):
    """Raised when a request falls outside the verified Wave 12 scope."""


MaterialSystem = Literal["timber", "masonry"]


@dataclass(frozen=True)
class TimberMasonryMemberDesignInput:
    element_id: str
    material_system: MaterialSystem
    gross_area_m2: float
    characteristic_compressive_strength_pa: float
    characteristic_tensile_strength_pa: float
    compression_resistance_factor: float = 0.60
    tension_resistance_factor: float = 0.60
    design_action_factor: float = 1.00
    modification_factor: float = 1.00
    effective_length_m: float | None = None
    least_dimension_m: float | None = None
    slenderness_limit: float | None = None
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.element_id.strip():
            raise TimberMasonryAxialDesignError("element_id is required.")
        if self.material_system not in {"timber", "masonry"}:
            raise TimberMasonryAxialDesignError(
                f"Unsupported material_system: {self.material_system}"
            )
        for name, value in {
            "gross_area_m2": self.gross_area_m2,
            "characteristic_compressive_strength_pa": (
                self.characteristic_compressive_strength_pa
            ),
            "characteristic_tensile_strength_pa": (
                self.characteristic_tensile_strength_pa
            ),
            "compression_resistance_factor": self.compression_resistance_factor,
            "tension_resistance_factor": self.tension_resistance_factor,
            "design_action_factor": self.design_action_factor,
            "modification_factor": self.modification_factor,
        }.items():
            if not isinstance(value, (int, float)) or value <= 0:
                raise TimberMasonryAxialDesignError(f"{name} must be positive.")

        slenderness_values = (
            self.effective_length_m,
            self.least_dimension_m,
            self.slenderness_limit,
        )
        if any(value is not None for value in slenderness_values):
            if any(value is None for value in slenderness_values):
                raise TimberMasonryAxialDesignError(
                    "effective_length_m, least_dimension_m and "
                    "slenderness_limit must be supplied together."
                )
            if any(
                not isinstance(value, (int, float)) or value <= 0
                for value in slenderness_values
            ):
                raise TimberMasonryAxialDesignError(
                    "Slenderness inputs must be positive."
                )


@dataclass(frozen=True)
class TimberMasonryAxialDesignConfig:
    project_id: str
    solver_results_artifact: str | Path
    output_directory: str | Path
    members: tuple[TimberMasonryMemberDesignInput, ...]
    force_zero_tolerance_n: float = 1e-6

    def validate(self) -> None:
        if not self.project_id.strip():
            raise TimberMasonryAxialDesignError("project_id is required.")
        if not Path(self.solver_results_artifact).is_file():
            raise TimberMasonryAxialDesignError(
                f"Solver result artifact does not exist: "
                f"{self.solver_results_artifact}"
            )
        if not self.members:
            raise TimberMasonryAxialDesignError(
                "At least one member design input is required."
            )
        if self.force_zero_tolerance_n <= 0:
            raise TimberMasonryAxialDesignError(
                "force_zero_tolerance_n must be positive."
            )
        for member in self.members:
            member.validate()
        ids = [member.element_id for member in self.members]
        if len(set(ids)) != len(ids):
            raise TimberMasonryAxialDesignError(
                "Member element_id values must be unique."
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
        raise TimberMasonryAxialDesignError(
            f"Unable to read solver result artifact: {path}"
        ) from exc

    if artifact.get("schema") != "phoenix-reference-solver-results-v1.0":
        raise TimberMasonryAxialDesignError(
            "Wave 12 requires phoenix-reference-solver-results-v1.0."
        )
    if artifact.get("project_id") != project_id:
        raise TimberMasonryAxialDesignError(
            "Solver result project_id mismatch."
        )

    expected = artifact.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise TimberMasonryAxialDesignError(
            "Solver result SHA-256 is missing or invalid."
        )
    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual != expected:
        raise TimberMasonryAxialDesignError(
            "Solver result integrity verification failed."
        )

    solver = artifact.get("solver") or {}
    verification = artifact.get("verification") or {}
    if solver.get("execution_status") != "completed":
        raise TimberMasonryAxialDesignError(
            "Solver execution must be completed before design."
        )
    if not verification.get("global_equilibrium_passed"):
        raise TimberMasonryAxialDesignError(
            "Global equilibrium must pass before design."
        )
    if not verification.get("finite_results"):
        raise TimberMasonryAxialDesignError(
            "Solver results must be finite before design."
        )
    return artifact


def create_timber_masonry_axial_design_adapter(
    config: TimberMasonryAxialDesignConfig,
):
    """Return a PXO-compatible Wave 12 timber/masonry design adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "timber_masonry_axial_design":
            raise TimberMasonryAxialDesignError(
                f"Wave 12 adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise TimberMasonryAxialDesignError(
                "Runtime project_id mismatch."
            )
        if not plan_fingerprint.strip():
            raise TimberMasonryAxialDesignError(
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
                raise TimberMasonryAxialDesignError(
                    f"No solver result found for element {member.element_id}."
                )

            axial_force_n = float(solver_member["axial_force_n"])
            if not math.isfinite(axial_force_n):
                raise TimberMasonryAxialDesignError(
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

            compression_resistance_n = (
                member.gross_area_m2
                * member.characteristic_compressive_strength_pa
                * member.compression_resistance_factor
                * member.modification_factor
            )
            tension_resistance_n = (
                member.gross_area_m2
                * member.characteristic_tensile_strength_pa
                * member.tension_resistance_factor
                * member.modification_factor
            )

            governing_resistance_n = (
                compression_resistance_n
                if action_mode == "compression"
                else tension_resistance_n
                if action_mode == "tension"
                else min(compression_resistance_n, tension_resistance_n)
            )

            slenderness = None
            slenderness_passed = None
            stability_resistance_verified = False
            if member.effective_length_m is not None:
                slenderness = (
                    member.effective_length_m / member.least_dimension_m
                )
                slenderness_passed = (
                    slenderness <= member.slenderness_limit
                )

            utilization = (
                design_force_n / governing_resistance_n
                if governing_resistance_n > 0
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
                    "material_system": member.material_system,
                    "source_reference": member.source_reference,
                    "action_mode": action_mode,
                    "characteristic_axial_force_n": axial_force_n,
                    "design_axial_force_n": design_force_n,
                    "gross_area_m2": member.gross_area_m2,
                    "characteristic_compressive_strength_pa": (
                        member.characteristic_compressive_strength_pa
                    ),
                    "characteristic_tensile_strength_pa": (
                        member.characteristic_tensile_strength_pa
                    ),
                    "modification_factor": member.modification_factor,
                    "compression_resistance_n": compression_resistance_n,
                    "tension_resistance_n": tension_resistance_n,
                    "governing_axial_resistance_n": governing_resistance_n,
                    "utilization": utilization,
                    "slenderness": {
                        "effective_length_m": member.effective_length_m,
                        "least_dimension_m": member.least_dimension_m,
                        "limit": member.slenderness_limit,
                        "value": slenderness,
                        "passed": slenderness_passed,
                        "stability_resistance_verified": (
                            stability_resistance_verified
                        ),
                    },
                    "checks": {
                        "axial_strength_passed": strength_passed,
                        "slenderness_screen_passed": slenderness_passed,
                        "member_passed": member_passed,
                    },
                }
            )

        artifact = {
            "schema": (
                "phoenix-timber-masonry-axial-design-results-v1.0"
            ),
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "solver_results_artifact": results_path.as_posix(),
            "solver_results_artifact_sha256": solver_results[
                "artifact_sha256"
            ],
            "design_basis": {
                "type": (
                    "generic_policy_based_timber_masonry_axial_check"
                ),
                "named_code_compliance": None,
                "units": "SI",
                "scope": (
                    "gross-section axial resistance plus optional "
                    "geometric slenderness screening"
                ),
            },
            "member_results": member_results,
            "summary": {
                "member_count": len(member_results),
                "timber_member_count": sum(
                    1 for item in member_results
                    if item["material_system"] == "timber"
                ),
                "masonry_member_count": sum(
                    1 for item in member_results
                    if item["material_system"] == "masonry"
                ),
                "passed_member_count": sum(
                    1 for item in member_results
                    if item["checks"]["member_passed"]
                ),
                "failed_member_count": sum(
                    1 for item in member_results
                    if not item["checks"]["member_passed"]
                ),
                "all_members_passed": all_passed,
            },
            "claims_policy": {
                "named_code_compliance_not_claimed": True,
                "timber_buckling_not_verified": True,
                "timber_connections_not_verified": True,
                "timber_duration_and_moisture_model_not_verified": True,
                "masonry_eccentricity_not_verified": True,
                "masonry_lateral_stability_not_verified": True,
                "masonry_bond_and_unit_interaction_not_verified": True,
                "fire_resistance_not_verified": True,
                "durability_not_verified": True,
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
            output_directory
            / "timber_masonry_axial_design_results_v1_0.json"
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
                f"timber-masonry-design-results:{artifact_hash}",
                f"timber-masonry-members:{len(member_results)}",
                f"timber-masonry-all-passed:{str(all_passed).lower()}",
            ),
            metadata={
                "adapter": (
                    "phoenix_timber_masonry_axial_design_v1_0"
                ),
                "artifact_sha256": artifact_hash,
                "member_count": len(member_results),
                "all_members_passed": all_passed,
                "named_code_compliance": False,
            },
        )

    return adapter
