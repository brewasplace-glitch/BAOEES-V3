"""Operational IfcOpenShell BIM integration adapter for Phoenix Core v2.0 BB5."""

from __future__ import annotations

from hashlib import sha256
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

from phoenix.osif import ApplicationDescriptor, Capability
from .base import AdapterError, OSIFAdapter
from .contracts import (
    AdapterExecutionRequest,
    AdapterExecutionResult,
    AdapterHealth,
)


class IfcOpenShellIntegrationError(AdapterError):
    """Raised when an IFC request is invalid or execution fails."""


class IfcOpenShellAdapter(OSIFAdapter):
    APPLICATION_ID = "ifcopenshell"
    ADAPTER_ID = "phoenix.osif.adapter.ifcopenshell"

    SUPPORTED_CAPABILITIES = {
        "ifc.read",
        "ifc.write",
        "ifc.validate",
        "ifc.query",
        "ifc.pset.read",
        "ifc.structure.read",
        "ifc.digital_twin.export",
    }

    def __init__(self, *, module_loader=importlib.import_module) -> None:
        super().__init__()
        self._module_loader = module_loader

    def descriptor(self) -> ApplicationDescriptor:
        return ApplicationDescriptor(
            application_id=self.APPLICATION_ID,
            name="IfcOpenShell",
            adapter_id=self.ADAPTER_ID,
            execution_mode="python",
            capabilities=(
                Capability("ifc.read", "Read IFC model", ("ifc",), ("json",)),
                Capability("ifc.write", "Write IFC model", ("json",), ("ifc",)),
                Capability("ifc.validate", "Validate IFC model", ("ifc",), ("json",)),
                Capability("ifc.query", "Query IFC entities", ("ifc", "json"), ("json",)),
                Capability("ifc.pset.read", "Read IFC property sets", ("ifc",), ("json",)),
                Capability("ifc.structure.read", "Read IFC spatial structure", ("ifc",), ("json",)),
                Capability(
                    "ifc.digital_twin.export",
                    "Export normalized IFC data for Phoenix Digital Twin",
                    ("ifc",),
                    ("json",),
                ),
            ),
            enabled=True,
            metadata={
                "bb5_status": "operational",
                "python_module": "ifcopenshell",
                "license_id": "LGPL-3.0-or-later",
                "schema_support": ["IFC2X3", "IFC4", "IFC4X3"],
            },
        )

    def _load_module(self):
        try:
            return self._module_loader("ifcopenshell")
        except Exception as exc:
            raise IfcOpenShellIntegrationError(
                f"IfcOpenShell is unavailable: {exc}"
            ) from exc

    def health_check(self) -> AdapterHealth:
        try:
            module = self._load_module()
        except IfcOpenShellIntegrationError as exc:
            return AdapterHealth("unavailable", str(exc), {})

        version = str(getattr(module, "version", getattr(module, "__version__", "")))
        return AdapterHealth(
            "available",
            "IfcOpenShell Python module is available.",
            {"python_module": "ifcopenshell", "version": version},
        )

    @staticmethod
    def _required_path(inputs: Mapping[str, Any], key: str) -> Path:
        value = str(inputs.get(key, "")).strip()
        if not value:
            raise IfcOpenShellIntegrationError(f"Missing required input: {key}")
        return Path(value).expanduser().resolve()

    @staticmethod
    def _write_json(path: Path, value: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path

    @staticmethod
    def _entity_info(entity) -> dict[str, Any]:
        info = entity.get_info(recursive=False)
        normalized = {}
        for key, value in info.items():
            if hasattr(value, "id") and callable(value.id):
                normalized[key] = {"id": value.id(), "type": value.is_a()}
            elif isinstance(value, tuple):
                normalized[key] = [
                    {"id": item.id(), "type": item.is_a()}
                    if hasattr(item, "id") and callable(item.id)
                    else item
                    for item in value
                ]
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def _entity_name(entity) -> str:
        return str(getattr(entity, "Name", "") or "")

    @staticmethod
    def _entity_global_id(entity) -> str:
        return str(getattr(entity, "GlobalId", "") or "")

    def validate_request(self, request: AdapterExecutionRequest) -> None:
        if request.capability_id not in self.SUPPORTED_CAPABILITIES:
            raise IfcOpenShellIntegrationError(
                f"Unsupported IfcOpenShell capability: {request.capability_id}"
            )

        if request.capability_id == "ifc.write":
            destination = self._required_path(request.inputs, "destination_file")
            if destination.suffix.lower() != ".ifc":
                raise IfcOpenShellIntegrationError(
                    "destination_file must use the .ifc extension."
                )
            entities = request.inputs.get("entities", [])
            if not isinstance(entities, list):
                raise IfcOpenShellIntegrationError("entities must be a list.")
            return

        source = self._required_path(request.inputs, "source_file")
        if not source.is_file():
            raise IfcOpenShellIntegrationError(
                f"Source file does not exist: {source}"
            )
        if source.suffix.lower() != ".ifc":
            raise IfcOpenShellIntegrationError(
                "source_file must use the .ifc extension."
            )

        if request.capability_id == "ifc.query":
            entity_type = str(request.inputs.get("entity_type", "")).strip()
            if not entity_type:
                raise IfcOpenShellIntegrationError(
                    "ifc.query requires entity_type."
                )

    def _open_model(self, source: Path):
        module = self._load_module()
        try:
            return module.open(str(source))
        except Exception as exc:
            raise IfcOpenShellIntegrationError(
                f"Unable to open IFC file {source}: {exc}"
            ) from exc

    def _model_summary(self, model) -> dict[str, Any]:
        projects = model.by_type("IfcProject")
        sites = model.by_type("IfcSite")
        buildings = model.by_type("IfcBuilding")
        storeys = model.by_type("IfcBuildingStorey")
        spaces = model.by_type("IfcSpace")
        products = model.by_type("IfcProduct")
        return {
            "schema": str(getattr(model, "schema", "")),
            "project_count": len(projects),
            "site_count": len(sites),
            "building_count": len(buildings),
            "storey_count": len(storeys),
            "space_count": len(spaces),
            "product_count": len(products),
            "projects": [
                {
                    "id": item.id(),
                    "global_id": self._entity_global_id(item),
                    "name": self._entity_name(item),
                }
                for item in projects
            ],
        }

    def _read_psets(self, model) -> list[dict[str, Any]]:
        try:
            util_element = self._module_loader("ifcopenshell.util.element")
        except Exception as exc:
            raise IfcOpenShellIntegrationError(
                f"Unable to load IfcOpenShell property-set utilities: {exc}"
            ) from exc

        rows = []
        for product in model.by_type("IfcObject"):
            psets = util_element.get_psets(product)
            if psets:
                rows.append(
                    {
                        "id": product.id(),
                        "type": product.is_a(),
                        "global_id": self._entity_global_id(product),
                        "name": self._entity_name(product),
                        "property_sets": psets,
                    }
                )
        return rows

    def _spatial_structure(self, model) -> dict[str, Any]:
        rows = []
        for entity_type in (
            "IfcProject",
            "IfcSite",
            "IfcBuilding",
            "IfcBuildingStorey",
            "IfcSpace",
        ):
            for item in model.by_type(entity_type):
                rows.append(
                    {
                        "id": item.id(),
                        "type": item.is_a(),
                        "global_id": self._entity_global_id(item),
                        "name": self._entity_name(item),
                        "long_name": str(getattr(item, "LongName", "") or ""),
                        "elevation": getattr(item, "Elevation", None),
                    }
                )
        return {"entities": rows}

    def _validate_model(self, source: Path) -> dict[str, Any]:
        model = self._open_model(source)
        issues = []
        try:
            validate_module = self._module_loader("ifcopenshell.validate")
            logger = validate_module.json_logger()
            validate_module.validate(model, logger)
            for statement in getattr(logger, "statements", []):
                issues.append(dict(statement))
        except Exception as exc:
            issues.append(
                {
                    "level": "warning",
                    "message": (
                        "Formal validator unavailable: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

        return {
            "is_valid": not any(
                str(item.get("level", "")).lower() in {"error", "critical"}
                for item in issues
            ),
            "issue_count": len(issues),
            "issues": issues,
            "summary": self._model_summary(model),
        }

    def _write_model(self, request: AdapterExecutionRequest) -> dict[str, Any]:
        module = self._load_module()
        schema = str(request.inputs.get("schema", "IFC4"))
        try:
            model = module.file(schema=schema)
        except TypeError:
            model = module.file(schema)

        for specification in request.inputs.get("entities", []):
            if not isinstance(specification, Mapping):
                raise IfcOpenShellIntegrationError(
                    "Each entity specification must be an object."
                )
            entity_type = str(specification.get("type", "")).strip()
            attributes = specification.get("attributes", {})
            if not entity_type:
                raise IfcOpenShellIntegrationError(
                    "Each entity specification requires type."
                )
            if not isinstance(attributes, Mapping):
                raise IfcOpenShellIntegrationError(
                    "Entity attributes must be an object."
                )
            model.create_entity(entity_type, **dict(attributes))

        destination = self._required_path(request.inputs, "destination_file")
        destination.parent.mkdir(parents=True, exist_ok=True)
        model.write(str(destination))
        return {
            "destination_file": str(destination),
            "schema": str(getattr(model, "schema", schema)),
            "entity_count": len(list(model)),
        }

    def _execute(self, request: AdapterExecutionRequest) -> AdapterExecutionResult:
        capability = request.capability_id
        outputs: dict[str, Any]
        output_files: list[str] = []

        if capability == "ifc.write":
            outputs = self._write_model(request)
            output_files.append(outputs["destination_file"])
        else:
            source = self._required_path(request.inputs, "source_file")
            model = self._open_model(source)

            if capability == "ifc.read":
                outputs = self._model_summary(model)
            elif capability == "ifc.query":
                entity_type = str(request.inputs["entity_type"])
                entities = model.by_type(entity_type)
                limit = int(request.inputs.get("limit", 1000))
                outputs = {
                    "entity_type": entity_type,
                    "count": len(entities),
                    "entities": [
                        self._entity_info(item)
                        for item in entities[:max(0, limit)]
                    ],
                }
            elif capability == "ifc.pset.read":
                outputs = {"products": self._read_psets(model)}
            elif capability == "ifc.structure.read":
                outputs = self._spatial_structure(model)
            elif capability == "ifc.validate":
                outputs = self._validate_model(source)
            elif capability == "ifc.digital_twin.export":
                outputs = {
                    "summary": self._model_summary(model),
                    "spatial_structure": self._spatial_structure(model),
                    "property_sets": self._read_psets(model),
                }
            else:
                raise IfcOpenShellIntegrationError(
                    f"Unsupported capability: {capability}"
                )

            destination_raw = str(
                request.inputs.get("destination_file", "")
            ).strip()
            if destination_raw:
                destination = self._write_json(
                    Path(destination_raw).resolve(),
                    outputs,
                )
                output_files.append(str(destination))

        evidence = {}
        for value in output_files:
            path = Path(value)
            if path.is_file():
                evidence[str(path)] = sha256(path.read_bytes()).hexdigest()

        evidence_payload = {
            "request_id": request.request_id,
            "capability_id": capability,
            "outputs": outputs,
            "output_file_sha256": evidence,
        }

        return AdapterExecutionResult(
            request_id=request.request_id,
            adapter_id=self.ADAPTER_ID,
            application_id=self.APPLICATION_ID,
            status="completed",
            outputs={
                "data": outputs,
                "output_files": output_files,
                "output_file_sha256": evidence,
            },
            evidence_sha256=self.evidence_digest(evidence_payload),
            metadata={
                "schema_version": "1.0",
                "digital_twin_ready": capability == "ifc.digital_twin.export",
            },
        )
