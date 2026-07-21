"""Phoenix Structural Analysis Bootstrap Adapter â€” Wave 7 v1.0.

Consumes a verified Phoenix foundation concept and creates a traceable
structural-analysis bootstrap model. The artifact registers materials,
elements, load cases and load combinations, but does not claim that a finite
element analysis or code verification has been completed.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from phoenix.orchestration.runtime import AdapterResult


class StructuralBootstrapError(ValueError):
    """Raised when structural bootstrap input violates the contract."""


_ALLOWED_ELEMENT_TYPES = frozenset(
    {"beam", "column", "brace", "slab", "wall", "truss", "spring"}
)
_ALLOWED_MATERIAL_TYPES = frozenset(
    {"concrete", "steel", "timber", "masonry", "soil_spring", "other"}
)
_ALLOWED_LOAD_TYPES = frozenset(
    {"dead", "imposed", "wind", "snow", "seismic", "temperature", "other"}
)


@dataclass(frozen=True)
class StructuralMaterial:
    material_id: str
    material_type: str
    grade: str
    elastic_modulus_pa: float | None = None
    density_kg_m3: float | None = None
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.material_id.strip():
            raise StructuralBootstrapError("material_id is required.")
        if self.material_type not in _ALLOWED_MATERIAL_TYPES:
            raise StructuralBootstrapError(
                f"Unsupported material type: {self.material_type}"
            )
        if not self.grade.strip():
            raise StructuralBootstrapError("material grade is required.")
        if self.elastic_modulus_pa is not None and self.elastic_modulus_pa <= 0:
            raise StructuralBootstrapError(
                "elastic_modulus_pa must be positive when supplied."
            )
        if self.density_kg_m3 is not None and self.density_kg_m3 <= 0:
            raise StructuralBootstrapError(
                "density_kg_m3 must be positive when supplied."
            )


@dataclass(frozen=True)
class StructuralElement:
    element_id: str
    element_type: str
    material_id: str
    node_ids: tuple[str, ...]
    section_reference: str | None = None
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.element_id.strip():
            raise StructuralBootstrapError("element_id is required.")
        if self.element_type not in _ALLOWED_ELEMENT_TYPES:
            raise StructuralBootstrapError(
                f"Unsupported element type: {self.element_type}"
            )
        if not self.material_id.strip():
            raise StructuralBootstrapError("material_id is required.")
        if len(self.node_ids) < 2:
            raise StructuralBootstrapError(
                "Each structural element requires at least two node_ids."
            )
        if any(not node_id.strip() for node_id in self.node_ids):
            raise StructuralBootstrapError("node_ids may not be blank.")


@dataclass(frozen=True)
class StructuralLoadCase:
    load_case_id: str
    load_type: str
    description: str
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.load_case_id.strip():
            raise StructuralBootstrapError("load_case_id is required.")
        if self.load_type not in _ALLOWED_LOAD_TYPES:
            raise StructuralBootstrapError(
                f"Unsupported load type: {self.load_type}"
            )
        if not self.description.strip():
            raise StructuralBootstrapError(
                "Load case description is required."
            )


@dataclass(frozen=True)
class StructuralLoadCombination:
    combination_id: str
    factors: Mapping[str, float]
    design_situation: str
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.combination_id.strip():
            raise StructuralBootstrapError("combination_id is required.")
        if not self.factors:
            raise StructuralBootstrapError(
                "A load combination requires at least one factor."
            )
        if any(not load_case_id.strip() for load_case_id in self.factors):
            raise StructuralBootstrapError(
                "Load combination case identifiers may not be blank."
            )
        if any(not isinstance(factor, (int, float)) for factor in self.factors.values()):
            raise StructuralBootstrapError(
                "Load combination factors must be numeric."
            )
        if not self.design_situation.strip():
            raise StructuralBootstrapError(
                "design_situation is required."
            )


@dataclass(frozen=True)
class StructuralBootstrapConfig:
    project_id: str
    foundation_artifact: str | Path
    output_directory: str | Path
    nodes: Mapping[str, Sequence[float]] | None = None
    materials: tuple[StructuralMaterial, ...] = ()
    elements: tuple[StructuralElement, ...] = ()
    load_cases: tuple[StructuralLoadCase, ...] = ()
    load_combinations: tuple[StructuralLoadCombination, ...] = ()
    assumptions: tuple[str, ...] = ()
    analysis_engine: str = "unassigned"

    def validate(self) -> None:
        if not self.project_id.strip():
            raise StructuralBootstrapError("project_id is required.")
        if not Path(self.foundation_artifact).is_file():
            raise StructuralBootstrapError(
                f"Foundation artifact does not exist: {self.foundation_artifact}"
            )
        if not self.analysis_engine.strip():
            raise StructuralBootstrapError("analysis_engine is required.")

        nodes = self.nodes or {}
        for node_id, coordinates in nodes.items():
            if not str(node_id).strip():
                raise StructuralBootstrapError("node_id may not be blank.")
            if len(coordinates) != 3:
                raise StructuralBootstrapError(
                    f"Node {node_id} requires exactly three coordinates."
                )
            if any(not isinstance(value, (int, float)) for value in coordinates):
                raise StructuralBootstrapError(
                    f"Node {node_id} coordinates must be numeric."
                )

        for material in self.materials:
            material.validate()
        material_ids = [material.material_id for material in self.materials]
        if len(set(material_ids)) != len(material_ids):
            raise StructuralBootstrapError("material_id values must be unique.")

        for element in self.elements:
            element.validate()
            if element.material_id not in set(material_ids):
                raise StructuralBootstrapError(
                    f"Element {element.element_id} references unknown material "
                    f"{element.material_id}."
                )
            unknown_nodes = [
                node_id for node_id in element.node_ids if node_id not in nodes
            ]
            if unknown_nodes:
                raise StructuralBootstrapError(
                    f"Element {element.element_id} references unknown nodes: "
                    + ", ".join(unknown_nodes)
                )
        element_ids = [element.element_id for element in self.elements]
        if len(set(element_ids)) != len(element_ids):
            raise StructuralBootstrapError("element_id values must be unique.")

        for load_case in self.load_cases:
            load_case.validate()
        load_case_ids = [load_case.load_case_id for load_case in self.load_cases]
        if len(set(load_case_ids)) != len(load_case_ids):
            raise StructuralBootstrapError("load_case_id values must be unique.")

        known_load_cases = set(load_case_ids)
        for combination in self.load_combinations:
            combination.validate()
            unknown_cases = set(combination.factors) - known_load_cases
            if unknown_cases:
                raise StructuralBootstrapError(
                    f"Combination {combination.combination_id} references unknown "
                    f"load cases: {sorted(unknown_cases)}"
                )
        combination_ids = [
            combination.combination_id for combination in self.load_combinations
        ]
        if len(set(combination_ids)) != len(combination_ids):
            raise StructuralBootstrapError(
                "combination_id values must be unique."
            )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _verify_foundation_artifact(
    path: Path,
    project_id: str,
) -> Mapping[str, Any]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StructuralBootstrapError(
            f"Unable to read foundation artifact: {path}"
        ) from exc

    expected_hash = artifact.get("artifact_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise StructuralBootstrapError(
            "Foundation artifact SHA-256 is missing or invalid."
        )

    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual_hash = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual_hash != expected_hash:
        raise StructuralBootstrapError(
            "Foundation artifact integrity verification failed."
        )

    if artifact.get("project_id") != project_id:
        raise StructuralBootstrapError(
            "Foundation artifact project_id does not match configuration."
        )

    return artifact


def create_structural_analysis_bootstrap_adapter(
    config: StructuralBootstrapConfig,
):
    """Return a PXO-compatible structural analysis bootstrap adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "structural":
            raise StructuralBootstrapError(
                f"Structural adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise StructuralBootstrapError(
                "Runtime project_id does not match structural configuration."
            )
        if not plan_fingerprint.strip():
            raise StructuralBootstrapError("plan_fingerprint is required.")

        foundation_path = Path(config.foundation_artifact)
        foundation = _verify_foundation_artifact(
            foundation_path,
            project_id,
        )
        nodes = config.nodes or {}

        global_dof_count = len(nodes) * 6
        model_status = (
            "registered_model_ready_for_solver_adapter"
            if nodes and config.elements
            else "bootstrap_model_incomplete"
        )
        load_status = (
            "registered_load_model"
            if config.load_cases and config.load_combinations
            else "load_model_incomplete"
        )

        artifact = {
            "schema": "phoenix-structural-analysis-bootstrap-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "foundation_artifact": foundation_path.as_posix(),
            "foundation_artifact_sha256": foundation["artifact_sha256"],
            "foundation_type": foundation.get("foundation_type"),
            "analysis_engine": config.analysis_engine,
            "nodes": {
                node_id: [float(value) for value in coordinates]
                for node_id, coordinates in nodes.items()
            },
            "materials": [
                {
                    "material_id": item.material_id,
                    "material_type": item.material_type,
                    "grade": item.grade,
                    "elastic_modulus_pa": item.elastic_modulus_pa,
                    "density_kg_m3": item.density_kg_m3,
                    "source_reference": item.source_reference,
                }
                for item in config.materials
            ],
            "elements": [
                {
                    "element_id": item.element_id,
                    "element_type": item.element_type,
                    "material_id": item.material_id,
                    "node_ids": list(item.node_ids),
                    "section_reference": item.section_reference,
                    "source_reference": item.source_reference,
                }
                for item in config.elements
            ],
            "load_cases": [
                {
                    "load_case_id": item.load_case_id,
                    "load_type": item.load_type,
                    "description": item.description,
                    "source_reference": item.source_reference,
                }
                for item in config.load_cases
            ],
            "load_combinations": [
                {
                    "combination_id": item.combination_id,
                    "factors": dict(item.factors),
                    "design_situation": item.design_situation,
                    "source_reference": item.source_reference,
                }
                for item in config.load_combinations
            ],
            "analysis_graph": {
                "node_count": len(nodes),
                "element_count": len(config.elements),
                "global_dof_count_assuming_6_per_node": global_dof_count,
                "model_status": model_status,
                "load_status": load_status,
            },
            "solver_results": None,
            "member_forces": None,
            "reactions": None,
            "displacements": None,
            "stability_verification": None,
            "code_verification": None,
            "assumptions": list(config.assumptions),
            "unresolved_requirements": [
                "boundary condition registry",
                "element release registry",
                "section property verification",
                "load magnitude and application registry",
                "solver adapter execution",
                "result convergence verification",
                "second-order and stability assessment",
                "code-specific load combinations",
                "member design verification",
                "competent structural engineer approval",
            ],
            "claims_policy": {
                "bootstrap_is_not_completed_structural_analysis": True,
                "registered_elements_are_not_verified_members": True,
                "load_combinations_require_code_verification": True,
                "solver_results_must_not_be_invented": True,
                "member_capacity_must_not_be_invented": True,
            },
        }

        artifact_hash = sha256(
            _canonical_json(artifact).encode("utf-8")
        ).hexdigest()
        artifact["artifact_sha256"] = artifact_hash

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = (
            output_directory / "structural_analysis_bootstrap_v1_0.json"
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
                f"structural-bootstrap-artifact:{artifact_hash}",
                f"structural-model-status:{model_status}",
                f"structural-load-status:{load_status}",
            ),
            metadata={
                "adapter": "phoenix_structural_analysis_bootstrap_v1_0",
                "artifact_sha256": artifact_hash,
                "completed_structural_analysis": False,
                "global_dof_count": global_dof_count,
            },
        )

    return adapter
