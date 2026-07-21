"""Phoenix Structural Solver Contract Adapter â€” Wave 8 v1.0.

Consumes a verified structural-analysis bootstrap artifact and creates a
solver-ready contract. It registers supports, nodal actions and solver policy,
but it does not fabricate solver results or code-verification outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from phoenix.orchestration.runtime import AdapterResult


class StructuralSolverContractError(ValueError):
    """Raised when solver-contract input violates the Wave 8 contract."""


_ALLOWED_DOF = frozenset({"ux", "uy", "uz", "rx", "ry", "rz"})
_ALLOWED_ANALYSIS_TYPES = frozenset(
    {"linear_static", "eigenvalue", "second_order", "nonlinear_static"}
)


@dataclass(frozen=True)
class BoundaryCondition:
    boundary_id: str
    node_id: str
    restrained_dof: tuple[str, ...]
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.boundary_id.strip():
            raise StructuralSolverContractError("boundary_id is required.")
        if not self.node_id.strip():
            raise StructuralSolverContractError("node_id is required.")
        if not self.restrained_dof:
            raise StructuralSolverContractError(
                "At least one restrained degree of freedom is required."
            )
        unknown = set(self.restrained_dof) - _ALLOWED_DOF
        if unknown:
            raise StructuralSolverContractError(
                f"Unsupported restrained degrees of freedom: {sorted(unknown)}"
            )
        if len(set(self.restrained_dof)) != len(self.restrained_dof):
            raise StructuralSolverContractError(
                "restrained_dof values must be unique."
            )


@dataclass(frozen=True)
class NodalAction:
    action_id: str
    load_case_id: str
    node_id: str
    components: Mapping[str, float]
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.action_id.strip():
            raise StructuralSolverContractError("action_id is required.")
        if not self.load_case_id.strip():
            raise StructuralSolverContractError("load_case_id is required.")
        if not self.node_id.strip():
            raise StructuralSolverContractError("node_id is required.")
        if not self.components:
            raise StructuralSolverContractError(
                "Nodal action requires at least one component."
            )
        unknown = set(self.components) - _ALLOWED_DOF
        if unknown:
            raise StructuralSolverContractError(
                f"Unsupported nodal action components: {sorted(unknown)}"
            )
        if any(
            not isinstance(value, (int, float))
            for value in self.components.values()
        ):
            raise StructuralSolverContractError(
                "Nodal action components must be numeric."
            )


@dataclass(frozen=True)
class StructuralSolverContractConfig:
    project_id: str
    structural_bootstrap_artifact: str | Path
    output_directory: str | Path
    boundary_conditions: tuple[BoundaryCondition, ...] = ()
    nodal_actions: tuple[NodalAction, ...] = ()
    analysis_type: str = "linear_static"
    solver_name: str = "unassigned"
    solver_version: str | None = None
    convergence_tolerance: float = 1e-8
    maximum_iterations: int = 100
    assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.project_id.strip():
            raise StructuralSolverContractError("project_id is required.")
        if not Path(self.structural_bootstrap_artifact).is_file():
            raise StructuralSolverContractError(
                "Structural bootstrap artifact does not exist: "
                f"{self.structural_bootstrap_artifact}"
            )
        if self.analysis_type not in _ALLOWED_ANALYSIS_TYPES:
            raise StructuralSolverContractError(
                f"Unsupported analysis_type: {self.analysis_type}"
            )
        if not self.solver_name.strip():
            raise StructuralSolverContractError("solver_name is required.")
        if self.convergence_tolerance <= 0:
            raise StructuralSolverContractError(
                "convergence_tolerance must be positive."
            )
        if self.maximum_iterations <= 0:
            raise StructuralSolverContractError(
                "maximum_iterations must be positive."
            )

        for boundary in self.boundary_conditions:
            boundary.validate()
        boundary_ids = [
            boundary.boundary_id for boundary in self.boundary_conditions
        ]
        if len(set(boundary_ids)) != len(boundary_ids):
            raise StructuralSolverContractError(
                "boundary_id values must be unique."
            )

        for action in self.nodal_actions:
            action.validate()
        action_ids = [action.action_id for action in self.nodal_actions]
        if len(set(action_ids)) != len(action_ids):
            raise StructuralSolverContractError(
                "action_id values must be unique."
            )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _verify_structural_bootstrap(
    path: Path,
    project_id: str,
) -> Mapping[str, Any]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StructuralSolverContractError(
            f"Unable to read structural bootstrap artifact: {path}"
        ) from exc

    expected_hash = artifact.get("artifact_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise StructuralSolverContractError(
            "Structural bootstrap SHA-256 is missing or invalid."
        )

    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual_hash = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual_hash != expected_hash:
        raise StructuralSolverContractError(
            "Structural bootstrap integrity verification failed."
        )

    if artifact.get("project_id") != project_id:
        raise StructuralSolverContractError(
            "Structural bootstrap project_id does not match configuration."
        )

    return artifact


def create_structural_solver_contract_adapter(
    config: StructuralSolverContractConfig,
):
    """Return a PXO-compatible structural solver-contract adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "structural_solver":
            raise StructuralSolverContractError(
                f"Solver-contract adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise StructuralSolverContractError(
                "Runtime project_id does not match solver configuration."
            )
        if not plan_fingerprint.strip():
            raise StructuralSolverContractError(
                "plan_fingerprint is required."
            )

        structural_path = Path(config.structural_bootstrap_artifact)
        structural = _verify_structural_bootstrap(
            structural_path,
            project_id,
        )

        nodes = structural.get("nodes") or {}
        load_cases = structural.get("load_cases") or []
        known_nodes = set(nodes)
        known_load_cases = {
            str(item.get("load_case_id"))
            for item in load_cases
            if item.get("load_case_id")
        }

        for boundary in config.boundary_conditions:
            if boundary.node_id not in known_nodes:
                raise StructuralSolverContractError(
                    f"Boundary {boundary.boundary_id} references unknown node "
                    f"{boundary.node_id}."
                )

        for action in config.nodal_actions:
            if action.node_id not in known_nodes:
                raise StructuralSolverContractError(
                    f"Action {action.action_id} references unknown node "
                    f"{action.node_id}."
                )
            if action.load_case_id not in known_load_cases:
                raise StructuralSolverContractError(
                    f"Action {action.action_id} references unknown load case "
                    f"{action.load_case_id}."
                )

        restrained_pairs = {
            (boundary.node_id, dof)
            for boundary in config.boundary_conditions
            for dof in boundary.restrained_dof
        }
        total_dof = len(nodes) * 6
        restrained_dof_count = len(restrained_pairs)
        free_dof_count = max(total_dof - restrained_dof_count, 0)

        contract_status = (
            "solver_contract_ready"
            if nodes
            and structural.get("elements")
            and config.boundary_conditions
            and config.nodal_actions
            and config.solver_name != "unassigned"
            else "solver_contract_incomplete"
        )

        artifact = {
            "schema": "phoenix-structural-solver-contract-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "structural_bootstrap_artifact": structural_path.as_posix(),
            "structural_bootstrap_artifact_sha256": structural[
                "artifact_sha256"
            ],
            "analysis_type": config.analysis_type,
            "solver": {
                "name": config.solver_name,
                "version": config.solver_version,
                "execution_status": "not_executed",
            },
            "numerical_policy": {
                "convergence_tolerance": config.convergence_tolerance,
                "maximum_iterations": config.maximum_iterations,
            },
            "boundary_conditions": [
                {
                    "boundary_id": item.boundary_id,
                    "node_id": item.node_id,
                    "restrained_dof": list(item.restrained_dof),
                    "source_reference": item.source_reference,
                }
                for item in config.boundary_conditions
            ],
            "nodal_actions": [
                {
                    "action_id": item.action_id,
                    "load_case_id": item.load_case_id,
                    "node_id": item.node_id,
                    "components": dict(item.components),
                    "source_reference": item.source_reference,
                }
                for item in config.nodal_actions
            ],
            "degree_of_freedom_summary": {
                "total_dof": total_dof,
                "restrained_dof": restrained_dof_count,
                "free_dof": free_dof_count,
            },
            "contract_status": contract_status,
            "solver_input_export": None,
            "solver_run_id": None,
            "solver_results": None,
            "convergence_result": None,
            "reactions": None,
            "displacements": None,
            "member_forces": None,
            "eigenvalues": None,
            "assumptions": list(config.assumptions),
            "unresolved_requirements": [
                "solver-specific model exporter",
                "section property matrix verification",
                "element release implementation",
                "distributed load implementation",
                "self-weight generation policy",
                "solver process execution",
                "convergence verification",
                "result import and unit verification",
                "equilibrium and plausibility checks",
                "competent structural engineer approval",
            ],
            "claims_policy": {
                "contract_is_not_solver_execution": True,
                "solver_results_must_not_be_invented": True,
                "convergence_must_not_be_claimed_before_execution": True,
                "equilibrium_must_be_verified_after_execution": True,
                "code_compliance_is_outside_this_adapter": True,
            },
        }

        artifact_hash = sha256(
            _canonical_json(artifact).encode("utf-8")
        ).hexdigest()
        artifact["artifact_sha256"] = artifact_hash

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = (
            output_directory / "structural_solver_contract_v1_0.json"
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
            temporary_path = Path(handle.name)

        temporary_path.replace(destination)

        return AdapterResult(
            outputs=(destination.as_posix(),),
            evidence=(
                f"structural-solver-contract:{artifact_hash}",
                f"solver-contract-status:{contract_status}",
                f"solver-analysis-type:{config.analysis_type}",
            ),
            metadata={
                "adapter": "phoenix_structural_solver_contract_v1_0",
                "artifact_sha256": artifact_hash,
                "solver_executed": False,
                "free_dof_count": free_dof_count,
            },
        )

    return adapter
