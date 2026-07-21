"""Phoenix BIM / IFC Synchronization Engine â€” Wave 13 v1.0.

Creates a deterministic BIM synchronization artifact from verified Phoenix
structural and design artifacts. This wave does not write a binary IFC file;
it produces an auditable, IFC-oriented exchange model and synchronization map.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from phoenix.orchestration.runtime import AdapterResult


class BIMIFCSynchronizationError(ValueError):
    """Raised when BIM synchronization input is invalid or inconsistent."""


@dataclass(frozen=True)
class BIMIFCSynchronizationConfig:
    project_id: str
    structural_artifact: str | Path
    output_directory: str | Path
    design_artifacts: tuple[str | Path, ...] = ()
    ifc_schema_target: str = "IFC4"
    coordinate_reference_system: str | None = None

    def validate(self) -> None:
        if not self.project_id.strip():
            raise BIMIFCSynchronizationError("project_id is required.")
        if not Path(self.structural_artifact).is_file():
            raise BIMIFCSynchronizationError(
                f"Structural artifact does not exist: {self.structural_artifact}"
            )
        for path in self.design_artifacts:
            if not Path(path).is_file():
                raise BIMIFCSynchronizationError(
                    f"Design artifact does not exist: {path}"
                )
        if self.ifc_schema_target not in {"IFC4", "IFC4X3"}:
            raise BIMIFCSynchronizationError(
                f"Unsupported IFC schema target: {self.ifc_schema_target}"
            )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _read_verified(path: Path, project_id: str) -> Mapping[str, Any]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BIMIFCSynchronizationError(f"Unable to read artifact: {path}") from exc

    if artifact.get("project_id") != project_id:
        raise BIMIFCSynchronizationError(f"project_id mismatch in {path}.")

    expected = artifact.get("artifact_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise BIMIFCSynchronizationError(f"Missing or invalid SHA-256 in {path}.")

    unsigned = dict(artifact)
    unsigned.pop("artifact_sha256", None)
    actual = sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()
    if actual != expected:
        raise BIMIFCSynchronizationError(f"Artifact integrity failed: {path}.")
    return artifact


def _design_index(artifacts: list[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        schema = artifact.get("schema")
        for member in artifact.get("member_results") or []:
            element_id = member.get("element_id")
            if not element_id:
                continue
            index.setdefault(element_id, []).append(
                {
                    "source_schema": schema,
                    "artifact_sha256": artifact["artifact_sha256"],
                    "summary": {
                        "material_system": member.get("material_system"),
                        "action_mode": member.get("action_mode"),
                        "utilization": member.get("utilization"),
                        "checks": member.get("checks"),
                        "required_bar_count": member.get("required_bar_count"),
                        "provided_steel_area_m2": member.get("provided_steel_area_m2"),
                    },
                }
            )
    return index


def create_bim_ifc_synchronization_adapter(config: BIMIFCSynchronizationConfig):
    """Return a PXO-compatible Wave 13 BIM synchronization adapter."""
    config.validate()

    def adapter(*, project_id: str, engine_id: str, plan_fingerprint: str) -> AdapterResult:
        if engine_id != "bim_ifc_synchronization":
            raise BIMIFCSynchronizationError(
                f"BIM adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise BIMIFCSynchronizationError("Runtime project_id mismatch.")
        if not plan_fingerprint.strip():
            raise BIMIFCSynchronizationError("plan_fingerprint is required.")

        structural_path = Path(config.structural_artifact)
        structural = _read_verified(structural_path, project_id)
        if structural.get("schema") != "phoenix-structural-analysis-bootstrap-v1.0":
            raise BIMIFCSynchronizationError(
                "Wave 13 requires phoenix-structural-analysis-bootstrap-v1.0."
            )

        design_artifacts = [
            _read_verified(Path(path), project_id) for path in config.design_artifacts
        ]
        allowed_design_schemas = {
            "phoenix-concrete-axial-design-results-v1.0",
            "phoenix-steel-axial-design-results-v1.0",
            "phoenix-timber-masonry-axial-design-results-v1.0",
        }
        for artifact in design_artifacts:
            if artifact.get("schema") not in allowed_design_schemas:
                raise BIMIFCSynchronizationError(
                    f"Unsupported design artifact schema: {artifact.get('schema')}"
                )

        nodes = structural.get("nodes") or {}
        materials = {
            item["material_id"]: item for item in structural.get("materials") or []
        }
        elements = structural.get("elements") or []
        design_by_element = _design_index(design_artifacts)

        bim_nodes = []
        for node_id in sorted(nodes):
            coordinates = nodes[node_id]
            bim_nodes.append(
                {
                    "phoenix_id": node_id,
                    "ifc_entity": "IfcCartesianPoint",
                    "global_id_seed": f"{project_id}:node:{node_id}",
                    "coordinates_m": [float(value) for value in coordinates],
                }
            )

        bim_elements = []
        unresolved_design_references = []
        for element in sorted(elements, key=lambda item: item["element_id"]):
            element_id = element["element_id"]
            material = materials.get(element["material_id"])
            if not material:
                raise BIMIFCSynchronizationError(
                    f"Element {element_id} references unknown material."
                )
            ifc_entity = {
                "truss": "IfcMember",
                "beam": "IfcBeam",
                "column": "IfcColumn",
                "slab": "IfcSlab",
            }.get(element.get("element_type"), "IfcBuildingElementProxy")
            linked_design = design_by_element.get(element_id, [])
            bim_elements.append(
                {
                    "phoenix_id": element_id,
                    "ifc_entity": ifc_entity,
                    "global_id_seed": f"{project_id}:element:{element_id}",
                    "node_ids": list(element.get("node_ids") or []),
                    "material": {
                        "phoenix_material_id": material["material_id"],
                        "material_type": material.get("material_type"),
                        "grade": material.get("grade"),
                    },
                    "property_sets": {
                        "Pset_PhoenixIdentity": {
                            "ProjectId": project_id,
                            "ElementId": element_id,
                            "SourceArtifactSHA256": structural["artifact_sha256"],
                        },
                        "Pset_PhoenixDesignEvidence": linked_design,
                    },
                }
            )

        structural_element_ids = {item["element_id"] for item in elements}
        for element_id in design_by_element:
            if element_id not in structural_element_ids:
                unresolved_design_references.append(element_id)

        if unresolved_design_references:
            raise BIMIFCSynchronizationError(
                "Design artifacts contain unresolved structural elements: "
                f"{sorted(unresolved_design_references)}"
            )

        artifact = {
            "schema": "phoenix-bim-ifc-synchronization-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "ifc_exchange": {
                "target_schema": config.ifc_schema_target,
                "representation": "ifc_oriented_json_exchange_model",
                "binary_ifc_written": False,
                "coordinate_reference_system": config.coordinate_reference_system,
            },
            "source_chain": {
                "structural_artifact": structural_path.as_posix(),
                "structural_artifact_sha256": structural["artifact_sha256"],
                "design_artifacts": [
                    {
                        "path": Path(path).as_posix(),
                        "schema": artifact["schema"],
                        "artifact_sha256": artifact["artifact_sha256"],
                    }
                    for path, artifact in zip(config.design_artifacts, design_artifacts)
                ],
            },
            "spatial_structure": {
                "project": project_id,
                "site": f"{project_id}-SITE",
                "building": f"{project_id}-BUILDING",
                "storey": f"{project_id}-STOREY-00",
            },
            "nodes": bim_nodes,
            "elements": bim_elements,
            "synchronization_summary": {
                "node_count": len(bim_nodes),
                "element_count": len(bim_elements),
                "design_artifact_count": len(design_artifacts),
                "design_link_count": sum(len(value) for value in design_by_element.values()),
                "unresolved_reference_count": 0,
                "synchronization_status": "ready_for_ifc_serialization",
            },
            "claims_policy": {
                "binary_ifc_not_written": True,
                "ifc_schema_validation_not_performed": True,
                "geometry_solid_generation_not_performed": True,
                "authoring_tool_roundtrip_not_verified": True,
                "competent_bim_coordinator_review_required": True,
            },
        }

        artifact_hash = sha256(_canonical_json(artifact).encode("utf-8")).hexdigest()
        artifact["artifact_sha256"] = artifact_hash

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = output_directory / "bim_ifc_synchronization_v1_0.json"
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
                f"bim-ifc-synchronization:{artifact_hash}",
                f"bim-elements:{len(bim_elements)}",
                "bim-status:ready-for-ifc-serialization",
            ),
            metadata={
                "adapter": "phoenix_bim_ifc_synchronization_v1_0",
                "artifact_sha256": artifact_hash,
                "element_count": len(bim_elements),
                "binary_ifc_written": False,
            },
        )

    return adapter
