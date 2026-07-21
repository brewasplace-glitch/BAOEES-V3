"""Phoenix Foundation Bootstrap Adapter â€” Wave 6.1 v1.0.

Creates a traceable preliminary foundation concept from a verified Phoenix
geotechnical bootstrap artifact. The result is explicitly not a verified
foundation design.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from phoenix.orchestration.runtime import AdapterResult


class FoundationBootstrapError(ValueError):
    """Raised when foundation bootstrap input violates the contract."""


_ALLOWED_TYPES = frozenset({"strip", "pad", "raft", "pile", "undetermined"})


@dataclass(frozen=True)
class FoundationBootstrapConfig:
    project_id: str
    geotechnical_artifact: str | Path
    output_directory: str | Path
    preferred_foundation_type: str = "undetermined"
    use_phoenix_standard_strip_concept: bool = False
    strip_width_m: float = 1.50
    strip_height_m: float = 0.40
    beam_width_m: float = 0.50
    beam_height_m: float = 0.60
    concept_basis: str | None = None
    assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.project_id.strip():
            raise FoundationBootstrapError("project_id is required.")

        artifact_path = Path(self.geotechnical_artifact)
        if not artifact_path.is_file():
            raise FoundationBootstrapError(
                f"Geotechnical artifact does not exist: {artifact_path}"
            )

        if self.preferred_foundation_type not in _ALLOWED_TYPES:
            raise FoundationBootstrapError(
                f"Unsupported foundation type: {self.preferred_foundation_type}"
            )

        dimensions = (
            self.strip_width_m,
            self.strip_height_m,
            self.beam_width_m,
            self.beam_height_m,
        )
        if any(value <= 0 for value in dimensions):
            raise FoundationBootstrapError(
                "Foundation concept dimensions must be positive."
            )

        if self.use_phoenix_standard_strip_concept:
            if self.preferred_foundation_type not in {"strip", "undetermined"}:
                raise FoundationBootstrapError(
                    "Phoenix strip concept conflicts with preferred foundation type."
                )
        elif self.preferred_foundation_type != "undetermined":
            if not self.concept_basis or not self.concept_basis.strip():
                raise FoundationBootstrapError(
                    "concept_basis is required for an explicit foundation preference."
                )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _verify_geotechnical_artifact(
    path: Path,
    project_id: str,
) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FoundationBootstrapError(
            f"Unable to read geotechnical artifact: {path}"
        ) from exc

    expected_hash = payload.get("artifact_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise FoundationBootstrapError(
            "Geotechnical artifact SHA-256 is missing or invalid."
        )

    unsigned_payload = dict(payload)
    unsigned_payload.pop("artifact_sha256", None)
    actual_hash = sha256(
        _canonical_json(unsigned_payload).encode("utf-8")
    ).hexdigest()

    if actual_hash != expected_hash:
        raise FoundationBootstrapError(
            "Geotechnical artifact integrity verification failed."
        )

    if payload.get("project_id") != project_id:
        raise FoundationBootstrapError(
            "Geotechnical artifact project_id does not match configuration."
        )

    return payload


def create_foundation_bootstrap_adapter(config: FoundationBootstrapConfig):
    """Return a configured PXO foundation adapter."""
    config.validate()

    def adapter(
        *,
        project_id: str,
        engine_id: str,
        plan_fingerprint: str,
    ) -> AdapterResult:
        if engine_id != "foundation":
            raise FoundationBootstrapError(
                f"Foundation adapter cannot execute engine: {engine_id}"
            )
        if project_id != config.project_id:
            raise FoundationBootstrapError(
                "Runtime project_id does not match foundation configuration."
            )
        if not plan_fingerprint.strip():
            raise FoundationBootstrapError("plan_fingerprint is required.")

        geotechnical_path = Path(config.geotechnical_artifact)
        geotechnical = _verify_geotechnical_artifact(
            geotechnical_path,
            project_id,
        )

        foundation_type = config.preferred_foundation_type
        selection_status = "user_preference"

        if config.use_phoenix_standard_strip_concept:
            foundation_type = "strip"
            selection_status = "phoenix_standard_assumption"
        elif foundation_type == "undetermined":
            selection_status = "awaiting_verified_design"

        strip_concept = None
        if foundation_type == "strip":
            strip_concept = {
                "continuous_strip": {
                    "width_m": config.strip_width_m,
                    "height_m": config.strip_height_m,
                },
                "centered_foundation_beam": {
                    "width_m": config.beam_width_m,
                    "height_m": config.beam_height_m,
                },
            }

        soil_layers = geotechnical.get("soil_layers") or []
        geotechnical_status = str(
            geotechnical.get("data_status", "unknown")
        )
        supplied_profile = (
            bool(soil_layers)
            and geotechnical_status == "supplied_soil_profile"
        )
        concept_status = (
            "preliminary_concept_with_supplied_profile"
            if supplied_profile
            else "preliminary_concept_pending_ground_investigation"
        )

        output_directory = Path(config.output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        destination = output_directory / "foundation_concept_v1_0.json"

        artifact = {
            "schema": "phoenix-foundation-concept-v1.0",
            "project_id": project_id,
            "engine_id": engine_id,
            "plan_fingerprint": plan_fingerprint,
            "geotechnical_artifact": geotechnical_path.as_posix(),
            "geotechnical_artifact_sha256": geotechnical["artifact_sha256"],
            "location_reference": geotechnical.get("location_reference"),
            "geotechnical_data_status": geotechnical_status,
            "groundwater": geotechnical.get("groundwater"),
            "foundation_type": foundation_type,
            "selection_status": selection_status,
            "concept_status": concept_status,
            "strip_concept": strip_concept,
            "concept_basis": config.concept_basis,
            "assumptions": list(config.assumptions),
            "verified_design_checks": {
                "bearing_resistance": None,
                "settlement": None,
                "sliding": None,
                "overturning": None,
                "punching": None,
                "structural_capacity": None,
            },
            "design_actions": {},
            "reinforcement": None,
            "foundation_levels": None,
            "unresolved_requirements": [
                "verified design actions from the structural model",
                "verified bearing resistance",
                "settlement verification",
                "foundation level selection",
                "structural capacity verification",
                "reinforcement design",
                "constructability and execution review",
                "competent engineer approval",
            ],
            "claims_policy": {
                "bootstrap_is_not_verified_foundation_design": True,
                "dimensions_are_conceptual_until_verified": True,
                "geotechnical_capacity_must_not_be_invented": True,
                "structural_capacity_must_not_be_invented": True,
            },
        }

        artifact_hash = sha256(
            _canonical_json(artifact).encode("utf-8")
        ).hexdigest()
        artifact["artifact_sha256"] = artifact_hash

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
                f"foundation-bootstrap-artifact:{artifact_hash}",
                f"foundation-type:{foundation_type}",
                f"foundation-selection-status:{selection_status}",
            ),
            metadata={
                "adapter": "phoenix_foundation_bootstrap_v1_0",
                "artifact_sha256": artifact_hash,
                "verified_foundation_design_complete": False,
            },
        )

    return adapter
