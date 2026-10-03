from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import os
import shutil

from .executor_adapters import AdapterExecutionContext, AdapterExecutionResult


EXPECTED_KEYS = (
    "gis",
    "geotechnical",
    "traffic",
    "bim",
    "structural_steel",
    "concrete",
    "hydraulics",
    "water_supply",
    "sewer_design",
    "fire_safety",
    "climate_control",
    "electrical",
    "road_design",
    "sustainability",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class DisciplineDescriptor:
    key: str
    engine_id: str
    adapter_id: str
    action: str
    order: int
    dependencies: tuple[str, ...]
    required_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    existing_bindings: tuple[str, ...]
    external_backends: tuple[str, ...]
    release_boundary: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DisciplineDescriptor":
        return cls(
            key=str(value["key"]),
            engine_id=str(value["engine_id"]),
            adapter_id=str(value["adapter_id"]),
            action=str(value["action"]),
            order=int(value["order"]),
            dependencies=tuple(str(x) for x in value.get("dependencies", ())),
            required_inputs=tuple(str(x) for x in value.get("required_inputs", ())),
            outputs=tuple(str(x) for x in value.get("outputs", ())),
            existing_bindings=tuple(str(x) for x in value.get("existing_bindings", ())),
            external_backends=tuple(str(x) for x in value.get("external_backends", ())),
            release_boundary=str(value["release_boundary"]),
        )


class MultidisciplinaryEngineSuiteService:
    """Fail-closed orchestration contract for the fourteen engineering disciplines.

    The service prepares and validates a deterministic workflow. It never invents
    solver results, activates third-party binaries, mutates the repository, or
    represents preliminary output as professionally released design.
    """

    def __init__(self, config: Mapping[str, Any], *, repo_root: Path | None = None):
        self.config = dict(config)
        self.repo_root = Path(repo_root).resolve() if repo_root else None
        self.descriptors = tuple(
            DisciplineDescriptor.from_dict(x) for x in self.config.get("engines", ())
        )
        self._validate()

    @classmethod
    def from_repo(cls, repo_root: Path) -> "MultidisciplinaryEngineSuiteService":
        root = Path(repo_root).resolve()
        path = root / "configs" / "phoenix" / "multidisciplinary_engine_suite_v1.json"
        return cls(json.loads(path.read_text(encoding="utf-8-sig")), repo_root=root)

    def _validate(self) -> None:
        if self.config.get("schema") != "PHOENIX_MULTIDISCIPLINARY_ENGINE_SUITE_V1":
            raise RuntimeError("PHASE17_SUITE_SCHEMA_DENY")
        if self.config.get("status") != "ACTIVE_GOVERNED" or self.config.get("fail_closed") is not True:
            raise RuntimeError("PHASE17_SUITE_GOVERNANCE_DENY")
        if self.config.get("automatic_engine_activation") is not False:
            raise RuntimeError("PHASE17_AUTOMATIC_ENGINE_ACTIVATION_DENY")
        if self.config.get("automatic_repository_mutation") is not False:
            raise RuntimeError("PHASE17_AUTOMATIC_REPOSITORY_MUTATION_DENY")
        if self.config.get("final_professional_release_required") is not True:
            raise RuntimeError("PHASE17_PROFESSIONAL_RELEASE_BOUNDARY_DENY")
        if int(self.config.get("engine_count", 0)) != 14 or len(self.descriptors) != 14:
            raise RuntimeError("PHASE17_EXACT_ENGINE_COUNT_DENY")
        keys = tuple(x.key for x in sorted(self.descriptors, key=lambda x: x.order))
        if keys != EXPECTED_KEYS:
            raise RuntimeError("PHASE17_ENGINE_ORDER_DENY")
        if len({x.key for x in self.descriptors}) != 14:
            raise RuntimeError("PHASE17_DUPLICATE_ENGINE_KEY_DENY")
        if len({x.engine_id for x in self.descriptors}) != 14:
            raise RuntimeError("PHASE17_DUPLICATE_ENGINE_ID_DENY")
        known = {x.key for x in self.descriptors}
        for descriptor in self.descriptors:
            if not descriptor.engine_id.startswith("engineering."):
                raise RuntimeError("PHASE17_ENGINE_NAMESPACE_DENY")
            if not descriptor.required_inputs or not descriptor.outputs:
                raise RuntimeError(f"PHASE17_EMPTY_CONTRACT_DENY:{descriptor.key}")
            unknown = set(descriptor.dependencies) - known
            if unknown:
                raise RuntimeError(f"PHASE17_UNKNOWN_DEPENDENCY_DENY:{descriptor.key}")
            for dependency in descriptor.dependencies:
                dep = next(x for x in self.descriptors if x.key == dependency)
                if dep.order >= descriptor.order:
                    raise RuntimeError(f"PHASE17_DEPENDENCY_ORDER_DENY:{descriptor.key}:{dependency}")

    def backend_probe(self) -> dict[str, dict[str, Any]]:
        aliases = {
            "qgis": ("QGIS_PROCESS_EXE", ("qgis_process-qgis-ltr.exe", "qgis_process.exe", "qgis_process")),
            "ifcopenshell": ("", ()),
            "freecad": ("FREECAD_CMD", ("FreeCADCmd.exe", "freecadcmd.exe", "FreeCADCmd", "freecadcmd")),
            "opensees": ("OPENSEES_EXE", ("OpenSees.exe", "OpenSees")),
            "calculix": ("CALCULIX_CCX", ("ccx.exe", "ccx")),
            "energyplus": ("ENERGYPLUS_EXE", ("energyplus.exe", "energyplus")),
            "openstudio": ("OPENSTUDIO_EXE", ("openstudio.exe", "openstudio")),
            "contam": ("CONTAM_EXE", ("contamx3.exe", "contamx3")),
            "openmodelica": ("OPENMODELICA_EXE", ("omc.exe", "omc")),
        }
        result: dict[str, dict[str, Any]] = {}
        requested = sorted({name for x in self.descriptors for name in x.external_backends})
        for name in requested:
            if name == "ifcopenshell":
                try:
                    __import__("ifcopenshell")
                    available, resolved = True, "python:ifcopenshell"
                except ImportError:
                    available, resolved = False, None
            else:
                environment, candidates = aliases[name]
                configured = os.environ.get(environment) if environment else None
                resolved = configured if configured and Path(configured).is_file() else None
                if resolved is None:
                    resolved = next((shutil.which(x) for x in candidates if shutil.which(x)), None)
                available = resolved is not None
            result[name] = {
                "available": available,
                "resolved": resolved,
                "automatic_installation": False,
                "automatic_activation": False,
            }
        return result

    def plan(self, project: Mapping[str, Any]) -> dict[str, Any]:
        project_id = str(project.get("project_id", "")).strip()
        if not project_id:
            raise ValueError("PHASE17_PROJECT_ID_REQUIRED")
        supplied = project.get("verified_inputs", {})
        if not isinstance(supplied, Mapping):
            raise ValueError("PHASE17_VERIFIED_INPUTS_OBJECT_REQUIRED")
        backends = self.backend_probe()
        rows = []
        any_hold = False
        for descriptor in sorted(self.descriptors, key=lambda x: x.order):
            discipline_inputs = supplied.get(descriptor.key, {})
            if not isinstance(discipline_inputs, Mapping):
                discipline_inputs = {}
            missing = [x for x in descriptor.required_inputs if discipline_inputs.get(x) in (None, "", [], {})]
            backend_state = {
                name: backends[name]["available"] for name in descriptor.external_backends
            }
            unavailable = sorted(name for name, available in backend_state.items() if not available)
            status = "READY_FOR_GOVERNED_EXECUTION" if not missing else "HOLD_MISSING_VERIFIED_INPUTS"
            if missing:
                any_hold = True
            rows.append({
                "key": descriptor.key,
                "engine_id": descriptor.engine_id,
                "adapter_id": descriptor.adapter_id,
                "action": descriptor.action,
                "order": descriptor.order,
                "dependencies": list(descriptor.dependencies),
                "status": status,
                "missing_verified_inputs": missing,
                "declared_outputs": list(descriptor.outputs),
                "existing_bindings": list(descriptor.existing_bindings),
                "external_backends": backend_state,
                "unavailable_optional_or_required_backends": unavailable,
                "release_boundary": descriptor.release_boundary,
                "professional_release": False,
                "calculation_claimed": False,
            })
        result = {
            "schema": "PHOENIX_MULTIDISCIPLINARY_ENGINE_RESULT_V1",
            "project_id": project_id,
            "suite_version": str(self.config["version"]),
            "status": "HOLD_MISSING_VERIFIED_INPUTS" if any_hold else "READY_FOR_GOVERNED_EXECUTION",
            "engines": rows,
            "backend_probe": backends,
            "automatic_engine_activation": False,
            "automatic_repository_mutation": False,
            "repository_mutation": False,
            "professional_release": False,
            "result_sha256": "",
        }
        result["result_sha256"] = object_sha256({k: v for k, v in result.items() if k != "result_sha256"})
        return result

    def synthetic_proof(self) -> dict[str, Any]:
        verified = {
            descriptor.key: {name: f"verified:{descriptor.key}:{name}" for name in descriptor.required_inputs}
            for descriptor in self.descriptors
        }
        result = self.plan({"project_id": "PHASE17-SYNTHETIC-PROOF", "verified_inputs": verified})
        if result["status"] != "READY_FOR_GOVERNED_EXECUTION":
            raise RuntimeError("PHASE17_SYNTHETIC_PROOF_NOT_READY")
        return {
            "schema": "PHOENIX_PHASE17_SYNTHETIC_PROOF_V1",
            "status": "PASS",
            "engine_count": len(result["engines"]),
            "ordered_engine_keys": [x["key"] for x in result["engines"]],
            "all_release_boundaries_present": all(bool(x["release_boundary"]) for x in result["engines"]),
            "no_calculation_fabrication": all(x["calculation_claimed"] is False for x in result["engines"]),
            "automatic_engine_activation": False,
            "repository_mutation": False,
            "result_sha256": result["result_sha256"],
        }


class _DisciplineAdapter:
    adapter_id = ""
    discipline_key = ""

    def __init__(self, host: Any):
        self.host = host

    def execute(self, ctx: AdapterExecutionContext) -> AdapterExecutionResult:
        if ctx.step.mutating:
            raise RuntimeError("PHASE17_READ_ONLY_ADAPTER_MUTATION_DENY")
        root = Path(getattr(self.host, "repo_root", Path.cwd()))
        service = MultidisciplinaryEngineSuiteService.from_repo(root)
        payload = ctx.execution_payloads.get(ctx.step.step_id, {})
        project = payload.get("project", payload) if isinstance(payload, Mapping) else {}
        result = service.plan(project)
        selected = next(x for x in result["engines"] if x["key"] == self.discipline_key)
        return AdapterExecutionResult("COMPLETE", result=selected)


class GisDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.gis", "gis"
class GeotechnicalDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.geotechnical", "geotechnical"
class TrafficDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.traffic", "traffic"
class BimDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.bim", "bim"
class StructuralSteelDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.structural_steel", "structural_steel"
class ConcreteDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.concrete", "concrete"
class HydraulicsDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.hydraulics", "hydraulics"
class WaterSupplyDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.water_supply", "water_supply"
class SewerDesignDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.sewer_design", "sewer_design"
class FireSafetyDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.fire_safety", "fire_safety"
class ClimateControlDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.climate_control", "climate_control"
class ElectricalDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.electrical", "electrical"
class RoadDesignDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.road_design", "road_design"
class SustainabilityDisciplineAdapter(_DisciplineAdapter):
    adapter_id, discipline_key = "builtin.engineering.sustainability", "sustainability"
