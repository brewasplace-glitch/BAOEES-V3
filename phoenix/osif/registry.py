"""Application registry for Phoenix OSIF."""

from __future__ import annotations

import json
from pathlib import Path

from .contracts import ApplicationDescriptor, Capability


class RegistryError(RuntimeError):
    pass


class ApplicationRegistry:
    def __init__(self) -> None:
        self._applications: dict[str, ApplicationDescriptor] = {}

    def register(
        self,
        descriptor: ApplicationDescriptor,
        *,
        replace: bool = False,
    ) -> None:
        descriptor.validate()
        if descriptor.application_id in self._applications and not replace:
            raise RegistryError(
                f"Application already registered: {descriptor.application_id}"
            )
        self._applications[descriptor.application_id] = descriptor

    def get(self, application_id: str) -> ApplicationDescriptor:
        try:
            return self._applications[application_id]
        except KeyError as exc:
            raise RegistryError(
                f"Application not registered: {application_id}"
            ) from exc

    def list_applications(
        self,
        *,
        enabled_only: bool = False,
    ) -> tuple[ApplicationDescriptor, ...]:
        values = self._applications.values()
        if enabled_only:
            values = (item for item in values if item.enabled)
        return tuple(sorted(values, key=lambda item: item.application_id))

    def find_by_capability(
        self,
        capability_id: str,
        *,
        enabled_only: bool = True,
    ) -> tuple[ApplicationDescriptor, ...]:
        return tuple(
            descriptor
            for descriptor in self.list_applications(enabled_only=enabled_only)
            if any(
                item.capability_id == capability_id
                for item in descriptor.capabilities
            )
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": "1.0",
            "applications": [
                descriptor.to_dict()
                for descriptor in self.list_applications()
            ],
        }

    def write_json(self, destination: str | Path) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "ApplicationRegistry":
        registry = cls()
        for item in data.get("applications", []):
            capabilities = tuple(
                Capability(
                    capability_id=str(capability["capability_id"]),
                    name=str(capability["name"]),
                    input_formats=tuple(capability.get("input_formats", [])),
                    output_formats=tuple(capability.get("output_formats", [])),
                    metadata=dict(capability.get("metadata", {})),
                )
                for capability in item.get("capabilities", [])
            )
            registry.register(
                ApplicationDescriptor(
                    application_id=str(item["application_id"]),
                    name=str(item["name"]),
                    adapter_id=str(item["adapter_id"]),
                    execution_mode=str(item["execution_mode"]),
                    version=str(item.get("version", "")),
                    executable=str(item.get("executable", "")),
                    license_id=str(item.get("license_id", "")),
                    capabilities=capabilities,
                    enabled=bool(item.get("enabled", True)),
                    metadata=dict(item.get("metadata", {})),
                )
            )
        return registry
