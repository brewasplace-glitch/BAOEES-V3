"""Phoenix Geotechnical Bootstrap Adapter — Wave 5 v1.0.

Consumes a verified Phoenix GIS bootstrap artifact and creates a traceable
geotechnical site model. It accepts only explicitly supplied soil data and
assumptions. It never fabricates soil layers, bearing capacity, settlement,
groundwater observations or foundation suitability.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Mapping

from phoenix.orchestration.runtime import AdapterResult


class GeotechnicalBootstrapError(ValueError):
    """Raised when geotechnical bootstrap input violates the contract."""


@dataclass(frozen=True)
class SoilLayer:
    layer_id: str
    top_level_m: float
    bottom_level_m: float
    classification: str
    unit_weight_kn_m3: float | None = None
    friction_angle_deg: float | None = None
    cohesion_kpa: float | None = None
    undrained_shear_strength_kpa: float | None = None
    source_reference: str | None = None

    def validate(self) -> None:
        if not self.layer_id.strip():
            raise GeotechnicalBootstrapError("layer_id is required.")
        if not self.classification.strip():
            raise GeotechnicalBootstrapError("classification is required.")
        if self.top_level_m <= self.bottom_level_m:
            raise GeotechnicalBootstrapError(
                f"Soil layer {self.layer_id} must have top_level_m above bottom_level_m."
            )
        if self.unit_weight_kn_m3 is not None and self.unit_weight_kn_m3 <= 0:
            raise GeotechnicalBootstrapError("unit weight must be positive.")
        if self.friction_angle_deg is not None and not (
            0 <= self.friction_angle_deg <= 60
        ):
            raise GeotechnicalBootstrapError(
                "friction angle must be between 0 and 60 degrees."
            )
        if self.cohesion_kpa is not None and self.cohesion_kpa < 0:
            raise GeotechnicalBootstrapError("cohesion cannot be negative.")
        if (
            self.undrained_shear_strength_kpa is not None
            and self.undrained_shear_strength_kpa < 0
        ):
            raise GeotechnicalBootstrapError(
                "undrained shear strength cannot be negative."
            )


@dataclass(frozen=True)
class GeotechnicalBootstrapConfig:
    project_id: str
    gis_artifact: str | Path
    output_directory: str | Path
    soil_layers: tuple[SoilLayer, ...] = ()
    groundwater_level_m: float | None = None
    groundwater_basis: str | None = None
    investigation_references: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    allow_assumed_groundwater: bool = False
    assumed_groundwater_level_m: float = -0.50

    def validate(self) -> None:
        if not self.project_id.strip():
            raise GeotechnicalBootstrapError("project_id is required.")

        gis_path = Path(self.gis_artifact)
        if not gis_path.is_file():
            raise GeotechnicalBootstrapError(
                f"GIS artifact does not exist: {gis_path}"
            )

        for layer in self.soil_layers:
            layer.validate()

        ordered = sorted(
            self.soil_layers,
            key=lambda layer: layer.top_level_m,
            reverse=True,
        )
        for first, second in zip(ordered, ordered[1:]):
            if second.top_level_m > first.bottom_level_m:
                raise GeotechnicalBootstrapError(
                    f"Soil layers {first.layer_id} and {second.layer_id} overlap."
                )

        if self.groundwater_level_m is not None and not (
            self.groundwater_basis and self.groundwater_basis.strip()
        ):
            raise GeotechnicalBootstrapError(
                "groundwater_basis is required with a supplied groundwater level."
            )

        if self.allow_assumed_groundwater and self.groundwater_level_m is not None:
            raise GeotechnicalBootstrapError(
                "Choose supplied groundwater or assumed groundwater, not both."
            )


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _read_and_verify_gis_artifact(path: Path, project_id: str) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_hash = payload.get("artifact_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise GeotechnicalBootstrapError("GIS artifact SHA-256 is missing or invalid.")

    verification = dict(payload)
    verification.pop("artifact_sha256", None)
    actual_hash = sha256(_canonical_json(verification).encode("utf-8")).hexdigest()
    if actual_hash != expected_hash:
        raise GeotechnicalBootstrapError("GIS artifact integrity verification failed.")

    if payload.get("project_id") != project_id:
        raise GeotechnicalBootstrapError(
            "GIS artifact project_id does not match geotechnical configuration."
        )
    return payload


def create_geotechnical_bootstrap_adapter(config: GeotechnicalBootstrapConfig):
    """Create a configured PXO geotechnical adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "geotechnical":
            raise GeotechnicalBootstrapError(
                f"Geotechnical adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise GeotechnicalBootstrapError(
                "Runtime project_id does not match geotechnical configuration."
            )
        if not plan_fingerprint.strip():
            raise GeotechnicalBootstrapError("plan_fingerprint is required.")

        gis_path = Path(config.gis_artifact)
        gis_payload = _read_and_verify_gis_artifact(gis_path, project_id)

        groundwater_level = config.groundwater_level_m
        groundwater_status = "not_supplied"
        groundwater_basis = config.groundwater_basis

        if groundwater_level is not None:
            groundwater_status = "supplied"
        elif config.allow_assumed_groundwater:
            groundwater_level = config.assumed_groundwater_level_m
            groundwater_status = "assumption"
            groundwater_basis = (
                "Phoenix project assumption; must be replaced by project-specific evidence."
            )

        if config.soil_layers:
            data_status = "supplied_soil_profile"
        else:
            data_status = "awaiting_ground_investigation"

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = output_directory / "geotechnical_site_model_v1_0.json"

        payload = {
            "schema": "phoenix-geotechnical-site-model-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "gis_artifact": gis_path.as_posix(),
            "gis_artifact_sha256": gis_payload["artifact_sha256"],
            "location_reference": gis_payload.get("location_reference"),
            "data_status": data_status,
            "soil_layers": [
                {
                    "layer_id": layer.layer_id,
                    "top_level_m": layer.top_level_m,
                    "bottom_level_m": layer.bottom_level_m,
                    "classification": layer.classification,
                    "unit_weight_kn_m3": layer.unit_weight_kn_m3,
                    "friction_angle_deg": layer.friction_angle_deg,
                    "cohesion_kpa": layer.cohesion_kpa,
                    "undrained_shear_strength_kpa": (
                        layer.undrained_shear_strength_kpa
                    ),
                    "source_reference": layer.source_reference,
                }
                for layer in config.soil_layers
            ],
            "groundwater": {
                "level_m": groundwater_level,
                "status": groundwater_status,
                "basis": groundwater_basis,
            },
            "investigation_references": list(config.investigation_references),
            "assumptions": list(config.assumptions),
            "verified_design_values": {},
            "foundation_recommendation": None,
            "unresolved_requirements": [
                "verified ground investigation",
                "laboratory or field test evidence where required",
                "design groundwater level",
                "settlement assessment",
                "bearing resistance assessment",
                "foundation recommendation by competent engineering workflow",
            ],
            "claims_policy": {
                "fabricated_soil_profile_forbidden": True,
                "fabricated_bearing_capacity_forbidden": True,
                "bootstrap_is_not_a_foundation_design": True,
                "assumed_groundwater_must_be_identified": True,
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
                f"geotechnical-bootstrap-artifact:{artifact_hash}",
                f"geotechnical-data-status:{data_status}",
                f"groundwater-status:{groundwater_status}",
            ),
            metadata={
                "adapter": "phoenix_geotechnical_bootstrap_v1_0",
                "artifact_sha256": artifact_hash,
                "foundation_design_complete": False,
            },
        )

    return adapter
