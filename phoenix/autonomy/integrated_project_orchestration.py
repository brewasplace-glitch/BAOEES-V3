from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import re

from .multidisciplinary_engine_suite import MultidisciplinaryEngineSuiteService, object_sha256


EXPECTED_STAGES = (
    "project_intake",
    "site_and_regulatory_analysis",
    "five_design_variants",
    "governed_variant_selection",
    "multidisciplinary_design",
    "digital_twin_coordination",
    "calculation_verification",
    "drawing_production",
    "quantity_takeoff",
    "cost_estimation",
    "construction_planning",
    "permit_documentation",
    "integrated_reporting",
    "complete_project_dossier",
    "professional_release",
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProjectStageDescriptor:
    stage_id: str
    order: int
    dependencies: tuple[str, ...]
    required_evidence: tuple[str, ...]
    outputs: tuple[str, ...]
    module_bindings: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectStageDescriptor":
        return cls(
            stage_id=str(value["id"]),
            order=int(value["order"]),
            dependencies=tuple(str(x) for x in value.get("dependencies", ())),
            required_evidence=tuple(str(x) for x in value.get("required_evidence", ())),
            outputs=tuple(str(x) for x in value.get("outputs", ())),
            module_bindings=tuple(str(x) for x in value.get("module_bindings", ())),
        )


def _artifact_valid(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        bool(str(value.get("artifact_id", "")).strip())
        and bool(str(value.get("source", "")).strip())
        and value.get("verified") is True
        and bool(SHA256_RE.fullmatch(str(value.get("sha256", ""))))
    )


class IntegratedProjectOrchestrationService:
    """Evidence-bound orchestration of the complete Phoenix project workflow.

    This service coordinates design, calculations, drawings, quantities, cost,
    planning, permits and reporting around the fourteen engineering disciplines.
    It records readiness only; it never fabricates an artifact or professional
    release and never mutates the repository.
    """

    def __init__(
        self,
        config: Mapping[str, Any],
        discipline_service: MultidisciplinaryEngineSuiteService,
        *,
        repo_root: Path | None = None,
    ):
        self.config = dict(config)
        self.discipline_service = discipline_service
        self.repo_root = Path(repo_root).resolve() if repo_root else None
        self.stages = tuple(ProjectStageDescriptor.from_dict(x) for x in self.config.get("stages", ()))
        self._validate()

    @classmethod
    def from_repo(cls, repo_root: Path) -> "IntegratedProjectOrchestrationService":
        root = Path(repo_root).resolve()
        config = json.loads(
            (root / "configs" / "phoenix" / "integrated_project_orchestration_v1.json").read_text(
                encoding="utf-8-sig"
            )
        )
        return cls(config, MultidisciplinaryEngineSuiteService.from_repo(root), repo_root=root)

    def _validate(self) -> None:
        if self.config.get("schema") != "PHOENIX_INTEGRATED_PROJECT_ORCHESTRATION_V1":
            raise RuntimeError("PHASE18_SCHEMA_DENY")
        if self.config.get("status") != "ACTIVE_GOVERNED" or self.config.get("fail_closed") is not True:
            raise RuntimeError("PHASE18_GOVERNANCE_DENY")
        for key in (
            "automatic_repository_mutation",
            "automatic_engine_activation",
            "automatic_professional_release",
        ):
            if self.config.get(key) is not False:
                raise RuntimeError(f"PHASE18_AUTOMATION_BOUNDARY_DENY:{key}")
        if self.config.get("professional_release_required") is not True:
            raise RuntimeError("PHASE18_PROFESSIONAL_RELEASE_REQUIRED")
        if self.config.get("evidence_sha256_required") is not True:
            raise RuntimeError("PHASE18_EVIDENCE_HASH_REQUIRED")
        if int(self.config.get("concept_variant_count", 0)) != 5:
            raise RuntimeError("PHASE18_EXACT_FIVE_VARIANTS_DENY")
        if int(self.config.get("multidisciplinary_engine_count", 0)) != 14:
            raise RuntimeError("PHASE18_EXACT_FOURTEEN_DISCIPLINES_DENY")
        ordered = tuple(x.stage_id for x in sorted(self.stages, key=lambda x: x.order))
        if ordered != EXPECTED_STAGES:
            raise RuntimeError("PHASE18_STAGE_ORDER_DENY")
        if len({x.stage_id for x in self.stages}) != len(EXPECTED_STAGES):
            raise RuntimeError("PHASE18_DUPLICATE_STAGE_DENY")
        known = {x.stage_id for x in self.stages}
        for stage in self.stages:
            if not stage.required_evidence or not stage.outputs or not stage.module_bindings:
                raise RuntimeError(f"PHASE18_EMPTY_STAGE_CONTRACT_DENY:{stage.stage_id}")
            if set(stage.dependencies) - known:
                raise RuntimeError(f"PHASE18_UNKNOWN_DEPENDENCY_DENY:{stage.stage_id}")
            for dependency in stage.dependencies:
                dependency_stage = next(x for x in self.stages if x.stage_id == dependency)
                if dependency_stage.order >= stage.order:
                    raise RuntimeError(f"PHASE18_DEPENDENCY_ORDER_DENY:{stage.stage_id}:{dependency}")

    @staticmethod
    def _project_missing(project: Mapping[str, Any]) -> list[str]:
        required = ("project_id", "instruction", "location_reference", "requested_outputs")
        return [name for name in required if project.get(name) in (None, "", [], {})]

    @staticmethod
    def _validate_variants(project: Mapping[str, Any]) -> tuple[list[str], str | None]:
        variants = project.get("design_variants", [])
        if not isinstance(variants, Sequence) or isinstance(variants, (str, bytes)):
            return [], "PHASE18_DESIGN_VARIANTS_ARRAY_REQUIRED"
        ids = [str(x.get("variant_id", "")).strip() for x in variants if isinstance(x, Mapping)]
        if not variants:
            return [], None
        if len(variants) != 5 or len(ids) != 5 or any(not x for x in ids) or len(set(ids)) != 5:
            return ids, "PHASE18_EXACT_FIVE_UNIQUE_VARIANTS_REQUIRED"
        selected = str(project.get("selected_variant_id") or "").strip()
        if selected and selected not in ids:
            return ids, "PHASE18_SELECTED_VARIANT_NOT_FOUND"
        return ids, None

    def run(self, project: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(project, Mapping):
            raise ValueError("PHASE18_PROJECT_OBJECT_REQUIRED")
        project_id = str(project.get("project_id", "")).strip()
        if not project_id:
            raise ValueError("PHASE18_PROJECT_ID_REQUIRED")
        missing_project = self._project_missing(project)
        variant_ids, variant_error = self._validate_variants(project)
        if variant_error:
            raise ValueError(variant_error)
        evidence = project.get("evidence", {})
        if not isinstance(evidence, Mapping):
            raise ValueError("PHASE18_EVIDENCE_OBJECT_REQUIRED")

        discipline_plan = self.discipline_service.plan(
            {"project_id": project_id, "verified_inputs": project.get("verified_inputs", {})}
        )
        stage_rows: list[dict[str, Any]] = []
        completed: set[str] = set()
        for stage in sorted(self.stages, key=lambda x: x.order):
            supplied = evidence.get(stage.stage_id, {})
            supplied = supplied if isinstance(supplied, Mapping) else {}
            missing_evidence = [name for name in stage.required_evidence if not _artifact_valid(supplied.get(name))]
            dependencies_complete = all(name in completed for name in stage.dependencies)
            if missing_project:
                status = "HOLD_MISSING_PROJECT_INPUTS"
            elif stage.stage_id == "five_design_variants" and len(variant_ids) != 5:
                status = "WAITING_FOR_FIVE_VARIANTS"
            elif stage.stage_id == "governed_variant_selection" and not project.get("selected_variant_id"):
                status = "WAITING_FOR_VARIANT_SELECTION"
            elif stage.stage_id == "multidisciplinary_design" and discipline_plan["status"] != "READY_FOR_GOVERNED_EXECUTION":
                status = "HOLD_MISSING_VERIFIED_INPUTS"
            elif not dependencies_complete:
                status = "BLOCKED_BY_DEPENDENCIES"
            elif missing_evidence:
                status = "WAITING_FOR_EVIDENCE"
            elif stage.stage_id == "professional_release":
                status = "READY_FOR_PROFESSIONAL_REVIEW"
            else:
                status = "EVIDENCE_VERIFIED"
                completed.add(stage.stage_id)
            stage_rows.append({
                "stage_id": stage.stage_id,
                "order": stage.order,
                "dependencies": list(stage.dependencies),
                "status": status,
                "missing_evidence": missing_evidence,
                "declared_outputs": list(stage.outputs),
                "module_bindings": list(stage.module_bindings),
                "outputs_claimed_produced": False,
                "professional_release": False,
            })

        final_stage = stage_rows[-1]
        if missing_project:
            overall = "HOLD_MISSING_PROJECT_INPUTS"
        elif discipline_plan["status"] != "READY_FOR_GOVERNED_EXECUTION":
            overall = "HOLD_MISSING_VERIFIED_INPUTS"
        elif final_stage["status"] == "READY_FOR_PROFESSIONAL_REVIEW":
            overall = "READY_FOR_PROFESSIONAL_REVIEW"
        else:
            overall = "WAITING_FOR_EVIDENCE"
        result = {
            "schema": "PHOENIX_INTEGRATED_PROJECT_RUN_V1",
            "project_id": project_id,
            "orchestration_version": str(self.config["version"]),
            "status": overall,
            "concept_variant_count": 5,
            "selected_variant_id": project.get("selected_variant_id"),
            "stages": stage_rows,
            "discipline_plan": discipline_plan,
            "shared_model": self.config["shared_model"],
            "repository_mutation": False,
            "automatic_engine_activation": False,
            "professional_release": False,
            "result_sha256": "",
        }
        result["result_sha256"] = object_sha256({k: v for k, v in result.items() if k != "result_sha256"})
        return result

    def synthetic_proof(self) -> dict[str, Any]:
        variants = [{"variant_id": f"V{i}"} for i in range(1, 6)]
        verified_inputs = {
            descriptor.key: {name: f"verified:{descriptor.key}:{name}" for name in descriptor.required_inputs}
            for descriptor in self.discipline_service.descriptors
        }
        evidence: dict[str, dict[str, Any]] = {}
        for stage in self.stages:
            evidence[stage.stage_id] = {}
            for name in stage.required_evidence:
                payload = f"PHASE18:{stage.stage_id}:{name}".encode("utf-8")
                evidence[stage.stage_id][name] = {
                    "artifact_id": f"{stage.stage_id}:{name}",
                    "source": "synthetic-proof",
                    "verified": True,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
        result = self.run({
            "project_id": "PHASE18-SYNTHETIC-PROOF",
            "instruction": "Verify the integrated project orchestration contract.",
            "location_reference": "synthetic:test-site",
            "requested_outputs": ["complete_project_dossier"],
            "design_variants": variants,
            "selected_variant_id": "V1",
            "verified_inputs": verified_inputs,
            "evidence": evidence,
        })
        if result["status"] != "READY_FOR_PROFESSIONAL_REVIEW":
            raise RuntimeError("PHASE18_SYNTHETIC_PROOF_NOT_READY")
        return {
            "schema": "PHOENIX_PHASE18_SYNTHETIC_PROJECT_ORCHESTRATION_PROOF_V1",
            "status": "PASS",
            "stage_count": len(result["stages"]),
            "discipline_count": len(result["discipline_plan"]["engines"]),
            "variant_count": result["concept_variant_count"],
            "final_status": result["status"],
            "all_project_capabilities_bound": True,
            "no_outputs_fabricated": all(x["outputs_claimed_produced"] is False for x in result["stages"]),
            "professional_release": False,
            "repository_mutation": False,
            "result_sha256": result["result_sha256"],
        }
