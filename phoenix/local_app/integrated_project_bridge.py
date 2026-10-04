"""Official Start Screen bridge to Phase-18 integrated project orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import re

from phoenix.autonomy import IntegratedProjectOrchestrationService


MODE_MAP = {
    "manual": "LEVEL_0_MANUAL",
    "guided": "LEVEL_2_SEMI_AUTONOMOUS",
    "autonomous": "LEVEL_3_GOVERNED_AUTONOMOUS_TASK",
}


@dataclass(frozen=True)
class StartScreenBridgeResult:
    run_id: str
    path: Path | None
    payload: dict[str, Any]


class OfficialStartIntegratedProjectBridge:
    """Translate start-screen sessions into the governed Phase-18 contract.

    The bridge only records orchestration readiness. It never invents design
    variants, evidence, calculations, drawings, prices or professional release.
    """

    def __init__(self, repository: Path):
        self.repository = Path(repository).resolve()
        self.service = IntegratedProjectOrchestrationService.from_repo(self.repository)
        self.output_root = (
            self.repository / "outputs" / "runtime" / "phase19_start_screen_bridge"
        )

    @staticmethod
    def _clean(value: Any) -> str:
        return str(value or "").strip()

    @classmethod
    def _project_id(cls, session: Mapping[str, Any]) -> str:
        explicit = cls._clean(session.get("project_id"))
        if explicit:
            return explicit
        selected = cls._clean(session.get("selected_project"))
        if selected:
            stem = Path(selected).stem
            slug = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-")
            if slug:
                return slug[:96]
        session_id = cls._clean(session.get("session_id"))
        if session_id:
            return session_id
        raise ValueError("PHASE19_PROJECT_ID_REQUIRED")

    @classmethod
    def _location_reference(cls, session: Mapping[str, Any]) -> str:
        return cls._clean(session.get("location_reference"))

    @staticmethod
    def _artifact(value: str, source: str) -> dict[str, Any]:
        data = value.encode("utf-8")
        return {
            "artifact_id": "start-screen-project-brief",
            "source": source,
            "verified": True,
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def build_contract(self, session: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(session, Mapping):
            raise ValueError("PHASE19_SESSION_OBJECT_REQUIRED")
        mode = self._clean(session.get("project_mode")).lower() or "manual"
        if mode not in MODE_MAP:
            raise ValueError("PHASE19_PROJECT_MODE_DENY")
        instruction = self._clean(session.get("brief"))
        outputs = session.get("desired_outputs", [])
        if not isinstance(outputs, list):
            raise ValueError("PHASE19_DESIRED_OUTPUTS_ARRAY_REQUIRED")
        outputs = [self._clean(value) for value in outputs if self._clean(value)]

        variants = session.get("design_variants", [])
        if variants is None:
            variants = []
        if not isinstance(variants, list):
            raise ValueError("PHASE19_DESIGN_VARIANTS_ARRAY_REQUIRED")

        evidence: dict[str, Any] = {}
        if instruction:
            evidence["project_intake"] = {
                "project_brief": self._artifact(
                    instruction,
                    self._clean(session.get("session_file")) or "official-start-screen",
                )
            }

        contract = {
            "project_id": self._project_id(session),
            "instruction": instruction,
            "location_reference": self._location_reference(session),
            "requested_outputs": outputs,
            "design_variants": variants,
            "selected_variant_id": self._clean(session.get("selected_variant_id")) or None,
            "verified_inputs": session.get("verified_inputs", {}),
            "evidence": session.get("evidence", evidence),
            "start_screen_context": {
                "session_id": self._clean(session.get("session_id")),
                "project_type": self._clean(session.get("project_type")).upper(),
                "project_mode": mode,
                "autonomy_level": MODE_MAP[mode],
                "upload_batch": self._clean(session.get("upload_batch")) or None,
                "output_format_preferences": dict(session.get("output_format_preferences") or {}),
            },
        }
        return contract

    def plan(self, session: Mapping[str, Any], *, persist: bool = True) -> StartScreenBridgeResult:
        contract = self.build_contract(session)
        orchestration = self.service.run(contract)
        run_id = "P19-" + hashlib.sha256(
            json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16].upper()
        missing = []
        for key in ("instruction", "location_reference", "requested_outputs"):
            if contract.get(key) in (None, "", [], {}):
                missing.append(key)
        payload = {
            "schema": "PHOENIX_START_SCREEN_INTEGRATED_PROJECT_BRIDGE_V1",
            "version": "1.0.0",
            "run_id": run_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "status": orchestration["status"],
            "autonomy_level": contract["start_screen_context"]["autonomy_level"],
            "requested_outputs": list(contract["requested_outputs"]),
            "missing_start_inputs": missing,
            "variant_count": orchestration["concept_variant_count"],
            "selected_variant_id": orchestration["selected_variant_id"],
            "stage_count": len(orchestration["stages"]),
            "stages": orchestration["stages"],
            "discipline_plan": orchestration["discipline_plan"],
            "shared_model": orchestration["shared_model"],
            "professional_release_required": True,
            "professional_release": False,
            "repository_mutation": False,
            "automatic_engine_activation": False,
            "no_output_fabrication": True,
            "orchestration_result_sha256": orchestration["result_sha256"],
        }
        path = None
        if persist:
            self.output_root.mkdir(parents=True, exist_ok=True)
            path = self.output_root / f"{run_id}.json"
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return StartScreenBridgeResult(run_id=run_id, path=path, payload=payload)

    def get(self, run_id: str) -> dict[str, Any] | None:
        run_id = self._clean(run_id)
        if not re.fullmatch(r"P19-[A-F0-9]{16}", run_id):
            raise ValueError("PHASE19_RUN_ID_DENY")
        path = self.output_root / f"{run_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))
