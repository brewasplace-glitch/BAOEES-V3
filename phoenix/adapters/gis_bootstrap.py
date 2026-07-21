"""Phoenix GIS Bootstrap Adapter — Wave 4 v1.0.

The adapter creates the first real PXO runtime artifact. It records only
user-supplied or explicitly sourced site information and never fabricates
coordinates, zoning, soil, environmental or permit facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Iterable

from phoenix.orchestration.runtime import AdapterResult


class GISBootstrapError(ValueError):
    """Raised when GIS bootstrap configuration is invalid."""


@dataclass(frozen=True)
class GISBootstrapSource:
    source_id: str
    title: str
    reference: str
    source_type: str = "user_supplied"
    retrieved_at: str | None = None

    def validate(self) -> None:
        required = {
            "source_id": self.source_id,
            "title": self.title,
            "reference": self.reference,
            "source_type": self.source_type,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise GISBootstrapError(
                "Missing GIS source fields: " + ", ".join(missing)
            )


@dataclass(frozen=True)
class GISBootstrapConfig:
    project_id: str
    location_reference: str
    output_directory: str | Path
    coordinate_reference_system: str | None = None
    centroid: tuple[float, float] | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    sources: tuple[GISBootstrapSource, ...] = ()
    assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.project_id.strip():
            raise GISBootstrapError("project_id is required.")
        if not self.location_reference.strip():
            raise GISBootstrapError("location_reference is required.")

        if self.centroid is not None:
            if len(self.centroid) != 2:
                raise GISBootstrapError("centroid must contain two values.")
            x, y = self.centroid
            if not all(isinstance(value, (int, float)) for value in (x, y)):
                raise GISBootstrapError("centroid values must be numeric.")

        if self.bounding_box is not None:
            if len(self.bounding_box) != 4:
                raise GISBootstrapError("bounding_box must contain four values.")
            min_x, min_y, max_x, max_y = self.bounding_box
            if not all(
                isinstance(value, (int, float))
                for value in (min_x, min_y, max_x, max_y)
            ):
                raise GISBootstrapError("bounding_box values must be numeric.")
            if min_x >= max_x or min_y >= max_y:
                raise GISBootstrapError("bounding_box minimums must be below maximums.")

        if (self.centroid is not None or self.bounding_box is not None) and not (
            self.coordinate_reference_system
            and self.coordinate_reference_system.strip()
        ):
            raise GISBootstrapError(
                "coordinate_reference_system is required with coordinates."
            )

        for source in self.sources:
            source.validate()


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def create_gis_bootstrap_adapter(config: GISBootstrapConfig):
    """Create a configured PXO GIS adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "gis":
            raise GISBootstrapError(
                f"GIS bootstrap adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise GISBootstrapError(
                "Runtime project_id does not match GIS bootstrap configuration."
            )
        if not plan_fingerprint.strip():
            raise GISBootstrapError("plan_fingerprint is required.")

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = output_directory / "gis_site_context_v1_0.json"

        supplied_geometry = (
            config.centroid is not None or config.bounding_box is not None
        )
        data_status = "supplied_geometry" if supplied_geometry else "reference_only"

        payload = {
            "schema": "phoenix-gis-site-context-v1.0",
            "project_id": config.project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "location_reference": config.location_reference,
            "data_status": data_status,
            "coordinate_reference_system": config.coordinate_reference_system,
            "centroid": list(config.centroid) if config.centroid else None,
            "bounding_box": list(config.bounding_box) if config.bounding_box else None,
            "sources": [
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "reference": source.reference,
                    "source_type": source.source_type,
                    "retrieved_at": source.retrieved_at,
                }
                for source in config.sources
            ],
            "assumptions": list(config.assumptions),
            "verified_facts": [],
            "unresolved_requirements": [
                "authoritative parcel geometry",
                "current zoning and planning rules",
                "environmental constraints",
                "utility constraints",
                "verified access and mobility conditions",
                "verified terrain and elevation data",
            ],
            "claims_policy": {
                "fabricated_coordinates_forbidden": True,
                "unsourced_site_facts_forbidden": True,
                "bootstrap_is_not_authoritative_gis_analysis": True,
            },
        }

        artifact_hash = sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
        payload["artifact_sha256"] = artifact_hash

        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_directory,
            delete=False,
            suffix=".tmp",
        ) as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            temporary = Path(handle.name)

        temporary.replace(destination)

        return AdapterResult(
            outputs=(destination.as_posix(),),
            evidence=(
                f"gis-bootstrap-artifact:{artifact_hash}",
                f"gis-bootstrap-status:{data_status}",
            ),
            metadata={
                "adapter": "phoenix_gis_bootstrap_v1_0",
                "artifact_sha256": artifact_hash,
                "authoritative": False,
            },
        )

    return adapter
