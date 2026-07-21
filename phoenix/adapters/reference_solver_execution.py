"""Phoenix Reference Solver Execution Engine â€” Wave 9 v1.0.

Executes a narrowly scoped, auditable linear-elastic axial-bar analysis from a
verified Wave 8 solver contract and its Wave 7 structural model.

Scope:
- truss elements aligned with the global X axis;
- translational UX degree of freedom only;
- nodal UX actions;
- linear static analysis;
- prescribed zero UX supports;
- SI units.

The engine rejects unsupported models instead of fabricating results.
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


class ReferenceSolverExecutionError(ValueError):
    """Raised when input or analysis falls outside the verified scope."""


@dataclass(frozen=True)
class ReferenceSolverExecutionConfig:
    project_id: str
    solver_contract_artifact: str | Path
    output_directory: str | Path
    section_areas_m2: Mapping[str, float]
    zero_tolerance: float = 1e-12
    equilibrium_tolerance_n: float = 1e-6

    def validate(self) -> None:
        if not self.project_id.strip():
            raise ReferenceSolverExecutionError("project_id is required.")
        if not Path(self.solver_contract_artifact).is_file():
            raise ReferenceSolverExecutionError(
                f"Solver contract does not exist: {self.solver_contract_artifact}"
            )
        if not self.section_areas_m2:
            raise ReferenceSolverExecutionError(
                "section_areas_m2 is required for every analyzed element."
            )
        if any(
            not element_id.strip() or not isinstance(area, (int, float)) or area <= 0
            for element_id, area in self.section_areas_m2.items()
        ):
            raise ReferenceSolverExecutionError(
                "Section areas must use nonblank element IDs and positive values."
            )
        if self.zero_tolerance <= 0:
            raise ReferenceSolverExecutionError("zero_tolerance must be positive.")
        if self.equilibrium_tolerance_n <= 0:
            raise ReferenceSolverExecutionError(
                "equilibrium_tolerance_n must be positive."
            )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _read_verified_artifact(path: Path, schema: str, project_id: str) -> Mapping[str, Any]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReferenceSolverExecutionError(f"Unable to read artifact: {path}") from exc

    if artifact.get("schema") != schema:
        raise ReferenceSolverExecutionError(
            f"Expected schema {schema}, received {artifact.get('schema')}."
        )
    if artifact.get("project_id") != project_id:
        raise ReferenceSolverExecutionError("Artifact project_id mismatch.")

    expected = artifact.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ReferenceSolverExecutionError("Artifact SHA-256 is missing or invalid.")

    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ReferenceSolverExecutionError("Artifact integrity verification failed.")
    return artifact


def _solve_dense(matrix: list[list[float]], vector: list[float], tolerance: float) -> list[float]:
    n = len(vector)
    augmented = [row[:] + [vector[i]] for i, row in enumerate(matrix)]

    for pivot_index in range(n):
        pivot_row = max(
            range(pivot_index, n),
            key=lambda row_index: abs(augmented[row_index][pivot_index]),
        )
        pivot = augmented[pivot_row][pivot_index]
        if abs(pivot) <= tolerance:
            raise ReferenceSolverExecutionError(
                "Global stiffness matrix is singular or insufficiently restrained."
            )
        augmented[pivot_index], augmented[pivot_row] = (
            augmented[pivot_row],
            augmented[pivot_index],
        )

        pivot = augmented[pivot_index][pivot_index]
        for column in range(pivot_index, n + 1):
            augmented[pivot_index][column] /= pivot

        for row_index in range(n):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            if abs(factor) <= tolerance:
                continue
            for column in range(pivot_index, n + 1):
                augmented[row_index][column] -= (
                    factor * augmented[pivot_index][column]
                )

    return [augmented[index][n] for index in range(n)]


def create_reference_solver_execution_adapter(
    config: ReferenceSolverExecutionConfig,
):
    """Return a PXO-compatible Wave 9 reference solver adapter."""
    config.validate()

    def adapter(*, project_id: str, engine_id: str, plan_fingerprint: str) -> AdapterResult:
        if engine_id != "reference_solver":
            raise ReferenceSolverExecutionError(
                f"Reference solver cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise ReferenceSolverExecutionError("Runtime project_id mismatch.")
        if not plan_fingerprint.strip():
            raise ReferenceSolverExecutionError("plan_fingerprint is required.")

        contract_path = Path(config.solver_contract_artifact)
        contract = _read_verified_artifact(
            contract_path,
            "phoenix-structural-solver-contract-v1.0",
            project_id,
        )
        if contract.get("analysis_type") != "linear_static":
            raise ReferenceSolverExecutionError(
                "Reference solver supports linear_static only."
            )

        structural_path = Path(contract["structural_bootstrap_artifact"])
        structural = _read_verified_artifact(
            structural_path,
            "phoenix-structural-analysis-bootstrap-v1.0",
            project_id,
        )
        if structural["artifact_sha256"] != contract[
            "structural_bootstrap_artifact_sha256"
        ]:
            raise ReferenceSolverExecutionError(
                "Wave 8 contract does not match the current Wave 7 artifact."
            )

        nodes = structural.get("nodes") or {}
        materials = {
            item["material_id"]: item for item in structural.get("materials") or []
        }
        elements = structural.get("elements") or []
        load_cases = {
            item["load_case_id"] for item in structural.get("load_cases") or []
        }

        if not nodes or not elements:
            raise ReferenceSolverExecutionError("Structural model is empty.")

        node_ids = sorted(nodes)
        node_index = {node_id: index for index, node_id in enumerate(node_ids)}
        size = len(node_ids)
        stiffness = [[0.0 for _ in range(size)] for _ in range(size)]
        load = [0.0 for _ in range(size)]
        element_data: list[dict[str, Any]] = []

        for element in elements:
            element_id = element["element_id"]
            if element.get("element_type") != "truss":
                raise ReferenceSolverExecutionError(
                    f"Element {element_id} is not a supported truss element."
                )
            node_pair = element.get("node_ids") or []
            if len(node_pair) != 2:
                raise ReferenceSolverExecutionError(
                    f"Element {element_id} requires exactly two nodes."
                )
            n1, n2 = node_pair
            x1, y1, z1 = [float(v) for v in nodes[n1]]
            x2, y2, z2 = [float(v) for v in nodes[n2]]
            if abs(y2 - y1) > config.zero_tolerance or abs(z2 - z1) > config.zero_tolerance:
                raise ReferenceSolverExecutionError(
                    f"Element {element_id} is not aligned with global X."
                )
            length = abs(x2 - x1)
            if length <= config.zero_tolerance:
                raise ReferenceSolverExecutionError(
                    f"Element {element_id} has zero length."
                )

            material = materials.get(element["material_id"])
            if not material:
                raise ReferenceSolverExecutionError(
                    f"Element {element_id} references an unknown material."
                )
            modulus = material.get("elastic_modulus_pa")
            if not isinstance(modulus, (int, float)) or modulus <= 0:
                raise ReferenceSolverExecutionError(
                    f"Material for {element_id} requires positive elastic_modulus_pa."
                )
            area = config.section_areas_m2.get(element_id)
            if area is None:
                raise ReferenceSolverExecutionError(
                    f"Missing section area for element {element_id}."
                )

            axial_stiffness = float(modulus) * float(area) / length
            i = node_index[n1]
            j = node_index[n2]
            stiffness[i][i] += axial_stiffness
            stiffness[i][j] -= axial_stiffness
            stiffness[j][i] -= axial_stiffness
            stiffness[j][j] += axial_stiffness
            element_data.append(
                {
                    "element_id": element_id,
                    "node_1": n1,
                    "node_2": n2,
                    "length_m": length,
                    "elastic_modulus_pa": float(modulus),
                    "area_m2": float(area),
                    "axial_stiffness_n_m": axial_stiffness,
                }
            )

        analyzed_load_cases = set()
        for action in contract.get("nodal_actions") or []:
            components = action.get("components") or {}
            unsupported = {
                dof for dof, value in components.items()
                if dof != "ux" and abs(float(value)) > config.zero_tolerance
            }
            if unsupported:
                raise ReferenceSolverExecutionError(
                    f"Action {action['action_id']} contains unsupported components: "
                    f"{sorted(unsupported)}"
                )
            load_case_id = action["load_case_id"]
            if load_case_id not in load_cases:
                raise ReferenceSolverExecutionError(
                    f"Unknown load case: {load_case_id}"
                )
            analyzed_load_cases.add(load_case_id)
            load[node_index[action["node_id"]]] += float(components.get("ux", 0.0))

        if len(analyzed_load_cases) != 1:
            raise ReferenceSolverExecutionError(
                "Reference solver requires exactly one active load case."
            )

        restrained_nodes = set()
        for boundary in contract.get("boundary_conditions") or []:
            restrained = set(boundary.get("restrained_dof") or [])
            if restrained - {"ux", "uy", "uz", "rx", "ry", "rz"}:
                raise ReferenceSolverExecutionError("Unknown boundary-condition DOF.")
            if "ux" in restrained:
                restrained_nodes.add(boundary["node_id"])

        if not restrained_nodes:
            raise ReferenceSolverExecutionError(
                "At least one UX restraint is required."
            )

        free_indices = [
            index for node_id, index in node_index.items()
            if node_id not in restrained_nodes
        ]
        if not free_indices:
            raise ReferenceSolverExecutionError(
                "At least one free UX degree of freedom is required."
            )

        reduced_k = [
            [stiffness[i][j] for j in free_indices] for i in free_indices
        ]
        reduced_f = [load[i] for i in free_indices]
        reduced_u = _solve_dense(reduced_k, reduced_f, config.zero_tolerance)

        displacement = [0.0 for _ in range(size)]
        for local_index, global_index in enumerate(free_indices):
            displacement[global_index] = reduced_u[local_index]

        internal = [
            sum(stiffness[i][j] * displacement[j] for j in range(size))
            for i in range(size)
        ]
        reaction = [internal[i] - load[i] for i in range(size)]
        equilibrium_residual = abs(sum(reaction) + sum(load))
        equilibrium_ok = equilibrium_residual <= config.equilibrium_tolerance_n
        if not equilibrium_ok:
            raise ReferenceSolverExecutionError(
                "Global equilibrium verification failed."
            )

        element_results = []
        strain_energy = 0.0
        for item in element_data:
            i = node_index[item["node_1"]]
            j = node_index[item["node_2"]]
            extension = displacement[j] - displacement[i]
            strain = extension / item["length_m"]
            stress = item["elastic_modulus_pa"] * strain
            axial_force = stress * item["area_m2"]
            strain_energy += 0.5 * axial_force * extension
            element_results.append(
                {
                    "element_id": item["element_id"],
                    "extension_m": extension,
                    "axial_strain": strain,
                    "axial_stress_pa": stress,
                    "axial_force_n": axial_force,
                }
            )

        artifact = {
            "schema": "phoenix-reference-solver-results-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "solver_contract_artifact": contract_path.as_posix(),
            "solver_contract_artifact_sha256": contract["artifact_sha256"],
            "structural_bootstrap_artifact": structural_path.as_posix(),
            "structural_bootstrap_artifact_sha256": structural["artifact_sha256"],
            "solver": {
                "name": "Phoenix Reference Axial Solver",
                "version": "1.0",
                "execution_status": "completed",
                "analysis_type": "linear_static",
                "scope": "global_x_axial_truss_only",
            },
            "active_load_case": next(iter(analyzed_load_cases)),
            "nodal_displacements_m": {
                node_id: {"ux": displacement[index]}
                for node_id, index in node_index.items()
            },
            "nodal_reactions_n": {
                node_id: {"fx": reaction[index]}
                for node_id, index in node_index.items()
                if node_id in restrained_nodes
            },
            "element_results": element_results,
            "verification": {
                "global_equilibrium_residual_n": equilibrium_residual,
                "global_equilibrium_passed": equilibrium_ok,
                "strain_energy_j": strain_energy,
                "finite_results": all(
                    math.isfinite(value)
                    for value in displacement + reaction
                ),
            },
            "claims_policy": {
                "results_apply_only_to_supported_reference_scope": True,
                "code_compliance_not_verified": True,
                "member_capacity_not_verified": True,
                "buckling_not_verified": True,
                "second_order_effects_not_verified": True,
                "competent_engineer_review_required": True,
            },
        }
        artifact_hash = sha256(
            _canonical_json(artifact).encode("utf-8")
        ).hexdigest()
        artifact["artifact_sha256"] = artifact_hash

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = output_directory / "reference_solver_results_v1_0.json"
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
                f"reference-solver-results:{artifact_hash}",
                "reference-solver-execution:completed",
                f"equilibrium-residual-n:{equilibrium_residual:.12g}",
            ),
            metadata={
                "adapter": "phoenix_reference_solver_execution_v1_0",
                "artifact_sha256": artifact_hash,
                "solver_executed": True,
                "equilibrium_verified": True,
            },
        )

    return adapter
