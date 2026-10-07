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
from phoenix.design.tropical_residential.adapters import detect_open_source_stack
from phoenix.design.tropical_residential.digital_twin import build_digital_twin_patch
from phoenix.design.tropical_residential.engine import generate_variants, select_balanced
from phoenix.design.tropical_residential.ifc_handoff import build_authoritative_ifc_contract
from phoenix.design.tropical_residential.ifc_author import author_ifc4
from phoenix.design.tropical_residential.output import write_package
from phoenix.design.tropical_residential.real_output import write_layout_bundle
from phoenix.design.tropical_residential.real_spatial import build_real_layout


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

    The bridge records orchestration readiness and may generate five explicitly
    provisional concept variants from verified upload bytes and declared input.
    It never claims survey, cadastral, legal or professional verification.
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

    @staticmethod
    def _run_id(contract: Mapping[str, Any]) -> str:
        return "P19-" + hashlib.sha256(
            json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:16].upper()

    @staticmethod
    def _object_sha256(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @classmethod
    def _request_fingerprint(cls, contract: Mapping[str, Any]) -> str:
        context = contract.get("start_screen_context") or {}
        return cls._object_sha256({
            "instruction": contract.get("instruction"),
            "location_reference": contract.get("location_reference"),
            "requested_outputs": contract.get("requested_outputs"),
            "project_type": context.get("project_type"),
            "project_mode": context.get("project_mode"),
            "upload_batch": context.get("upload_batch"),
        })

    @staticmethod
    def _evidence_artifact(artifact_id: str, source: str, payload: Any, **extra: Any) -> dict[str, Any]:
        artifact = {
            "artifact_id": artifact_id,
            "source": source,
            "verified": True,
            "sha256": OfficialStartIntegratedProjectBridge._object_sha256(payload),
        }
        artifact.update(extra)
        return artifact

    def validate_upload_batch(self, batch_id: str) -> dict[str, Any]:
        batch_id = self._clean(batch_id)
        if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z_[a-f0-9]{8}", batch_id):
            raise ValueError("PHASE19_UPLOAD_BATCH_ID_DENY")
        manifest_path = (
            self.repository / "inputs" / "runtime" / "official_start_v3_uploads"
            / batch_id / "upload_manifest.json"
        )
        if not manifest_path.is_file():
            raise ValueError("PHASE19_UPLOAD_BATCH_NOT_FOUND")
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw.decode("utf-8-sig"))
        if self._clean(manifest.get("batch_id")) != batch_id:
            raise ValueError("PHASE19_UPLOAD_BATCH_MANIFEST_DENY")
        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("PHASE19_UPLOAD_BATCH_EMPTY_DENY")
        batch_root = manifest_path.parent.resolve()
        verified_files = []
        for item in files:
            if not isinstance(item, Mapping):
                raise ValueError("PHASE19_UPLOAD_FILE_RECORD_DENY")
            name = Path(self._clean(item.get("name"))).name
            if not name:
                raise ValueError("PHASE19_UPLOAD_FILE_NAME_DENY")
            path = (batch_root / name).resolve()
            if batch_root not in path.parents or not path.is_file():
                raise ValueError("PHASE19_UPLOAD_FILE_NOT_FOUND")
            raw_file = path.read_bytes()
            declared_size = int(item.get("size_bytes", -1))
            if declared_size != len(raw_file):
                raise ValueError("PHASE19_UPLOAD_FILE_SIZE_DENY")
            verified_files.append({
                "name": name,
                "size_bytes": len(raw_file),
                "sha256": hashlib.sha256(raw_file).hexdigest(),
                "suffix": path.suffix.lower(),
            })
        return {
            "batch_id": batch_id,
            "file_count": len(files),
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "files": verified_files,
            "verified": True,
            "verification_status": "CONCEPT_INPUT_INTEGRITY_VERIFIED",
            "verification_scope": "FILE_INTEGRITY_AND_USER_DECLARED_LOCATION_ONLY",
            "survey_verified": False,
            "cadastral_verified": False,
            "professional_release_eligible": False,
        }

    @staticmethod
    def _number(pattern: str, text: str, default: float) -> float:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return float(match.group(1).replace(",", ".")) if match else float(default)

    def _concept_project(self, session: Mapping[str, Any], run_id: str) -> tuple[dict[str, Any], list[str]]:
        brief = self._clean(session.get("brief"))
        assumptions: list[str] = []
        area = self._number(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|vierkante\s+meter)", brief, 300.0)
        if not re.search(r"\d+(?:[.,]\d+)?\s*(?:m2|m²|vierkante\s+meter)", brief, re.I):
            assumptions.append("Bruto vloeroppervlak voorlopig 300 m2 conform projectproef-opdracht.")
        storeys = int(self._number(r"(\d+)\s*(?:verdiepingen|bouwlagen)", brief, 2))
        bedrooms = int(self._number(r"(\d+)\s*slaapkamer", brief, 3))
        parking = int(self._number(r"(\d+)\s*(?:wagens|auto(?:'s)?|parkeerplaatsen)", brief, 2))
        bathrooms = self._number(r"(\d+(?:[.,]\d+)?)\s*badkamer", brief, 2.0)
        assumptions.extend([
            "Perceelafmetingen zijn niet digitaal gewaarmerkt; conceptvarianten claimen geen definitieve terreinpassing.",
            "Rooilijnen, erfdienstbaarheden en lokale bouwregels blijven te verifiëren.",
            "Bodemonderzoek en sonderingen ontbreken; funderingsvrijgave blijft geblokkeerd.",
        ])
        return ({
            "project_id": self._project_id(session),
            "project_name": "Perceel 314 Urban Villa",
            "run_id": run_id,
            "climate_profile": "hot_humid",
            "site": {
                "width_m": 0.0,
                "depth_m": 0.0,
                "north_deg": 0.0,
                "flood_risk": True,
                "cyclone_risk": False,
                "coastal_exposure": False,
                "location_reference": self._location_reference(session),
                "terrain_level_nap_m": 0.85,
                "fill_sand_m": 0.40,
                "floor_level_nap_m": 1.50,
            },
            "program": {
                "target_floor_area_m2": area,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "storeys": storeys,
                "parking_spaces": parking,
            },
            "preferences": {
                "veranda": True,
                "open_plan": True,
                "courtyard": False,
                "garage_spaces": 2,
                "master_suite": True,
                "pool_reservation": True,
                "budget_tier": "mid_range",
                "style": "contemporary tropical urban villa",
                "roof_form": "flat_roof_steel_tube_trusses",
                "structural_grids_m": [[3, 6], [2, 6]],
                "materials": ["concrete", "steel", "masonry", "timber"],
            },
        }, assumptions)

    def prepare_concept_inputs(self, session: Mapping[str, Any], run_id: str) -> dict[str, Any]:
        location = self._location_reference(session)
        if not location:
            raise ValueError("PHASE19_R4_LOCATION_REQUIRED")
        upload = self.validate_upload_batch(self._clean(session.get("upload_batch")))
        project, assumptions = self._concept_project(session, run_id)
        variants = generate_variants(project)
        if len(variants) != 5 or [x.variant_id for x in variants] != list("ABCDE"):
            raise RuntimeError("PHASE19_R4_EXACT_FIVE_VARIANTS_DENY")
        raised_floor = round(project["site"]["floor_level_nap_m"] - project["site"]["terrain_level_nap_m"], 3)
        variant_dicts = []
        for variant in variants:
            value = variant.to_dict()
            value["raised_floor_m"] = raised_floor
            value["roof_pitch_deg"] = 0
            value["features"] = sorted(set(value["features"] + [
                "flat_roof_steel_tube_trusses",
                "grid_3x6m_and_2x6m_review",
                "two_car_garage",
                "master_suite",
                "future_pool_reservation",
            ]))
            value["assumptions"] = value["assumptions"] + assumptions
            variant_dicts.append(value)
        recommended = select_balanced(variants)
        recommended_dict = next(x for x in variant_dicts if x["variant_id"] == recommended.variant_id)
        output_dir = self.output_root / run_id / "five_variants"

        # PHOENIX_4_6_19_PHASE19_REAL_VARIANT_PROVIDER_RESTORE_R1
        # Restore the proven real-spatial A-E authoring route as the primary
        # Phase-19 variant provider. The foundation package is retained below
        # only as a backward-compatible fallback artifact set.
        real_spatial_root = output_dir / "real_spatial"
        real_variant_files = []
        topology_hashes = []
        ifc_evidence = {}
        for item in variant_dicts:
            layout = build_real_layout(project, item)
            validation = dict(layout.get("geometry_validation") or {})
            if not bool(validation.get("valid")):
                raise RuntimeError(
                    f"PHASE19_REAL_SPATIAL_GEOMETRY_DENY:{item['variant_id']}:"
                    f"{validation.get('warnings', [])}"
                )
            if len(layout.get("rooms") or []) <= 5:
                raise RuntimeError(f"PHASE19_REAL_SPATIAL_ROOM_COUNT_DENY:{item['variant_id']}")
            if len(layout.get("walls") or []) <= 4:
                raise RuntimeError(f"PHASE19_REAL_SPATIAL_WALL_COUNT_DENY:{item['variant_id']}")
            if len(layout.get("openings") or []) <= 2:
                raise RuntimeError(f"PHASE19_REAL_SPATIAL_OPENING_COUNT_DENY:{item['variant_id']}")

            bundle = write_layout_bundle(real_spatial_root / "variants", layout)
            variant_dir = real_spatial_root / "variants" / f"variant_{item['variant_id']}"
            ifc_path = variant_dir / f"variant_{item['variant_id']}.ifc"
            try:
                ifc_evidence[item["variant_id"]] = author_ifc4(project, layout, ifc_path)
            except (ModuleNotFoundError, ImportError) as exc:
                raise RuntimeError(
                    f"PHASE19_REAL_SPATIAL_IFC_DEPENDENCY_DENY:{item['variant_id']}:{exc}"
                ) from exc

            topology_payload = {
                "footprint": layout["footprint"],
                "rooms": [
                    {
                        "storey_index": room["storey_index"],
                        "room_id": room["room_id"],
                        "zone": room["zone"],
                        "x": round(float(room["x"]), 4),
                        "y": round(float(room["y"]), 4),
                        "width": round(float(room["width"]), 4),
                        "depth": round(float(room["depth"]), 4),
                    }
                    for room in layout["rooms"]
                ],
                "openings": [
                    {
                        "storey_index": opening["storey_index"],
                        "kind": opening["kind"],
                        "host_wall_key": opening["host_wall_key"],
                        "x": round(float(opening["x"]), 4),
                        "y": round(float(opening["y"]), 4),
                        "width_m": round(float(opening["width_m"]), 4),
                    }
                    for opening in layout["openings"]
                ],
            }
            topology_sha256 = hashlib.sha256(
                json.dumps(topology_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            topology_hashes.append(topology_sha256)

            layout_json = Path(bundle["layout_json"])
            storey_svgs = [Path(value) for value in bundle["svg_plans"]]
            real_variant_files.append({
                "variant_id": item["variant_id"],
                "strategy": item["strategy"],
                "provider": "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
                "svg_path": storey_svgs[0].relative_to(self.repository).as_posix(),
                "storey_svg_paths": [
                    value.relative_to(self.repository).as_posix() for value in storey_svgs
                ],
                "json_path": layout_json.relative_to(self.repository).as_posix(),
                "ifc_path": ifc_path.relative_to(self.repository).as_posix(),
                "topology_sha256": topology_sha256,
                "room_count": len(layout["rooms"]),
                "wall_count": len(layout["walls"]),
                "opening_count": len(layout["openings"]),
            })

        if len(set(topology_hashes)) != 5:
            raise RuntimeError(
                f"PHASE19_REAL_VARIANT_DISTINCTNESS_DENY:"
                f"unique={len(set(topology_hashes))}:required=5"
            )

        real_spatial_manifest = {
            "schema": "PHOENIX_PHASE19_REAL_SPATIAL_VARIANT_PROVIDER_V1",
            "provider": "phoenix.design.tropical_residential.real_spatial",
            "variant_count": 5,
            "variant_order": list("ABCDE"),
            "unique_topology_count": len(set(topology_hashes)),
            "variant_files": real_variant_files,
            "ifc_evidence": ifc_evidence,
            "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
        }
        real_spatial_manifest_path = real_spatial_root / "real_spatial_manifest.json"
        real_spatial_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        real_spatial_manifest_path.write_text(
            json.dumps(real_spatial_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        legacy_summary = write_package(
            output_dir,
            project,
            variant_dicts,
            recommended_dict,
            detect_open_source_stack(),
            build_digital_twin_patch(project, variant_dicts, recommended.variant_id),
            build_authoritative_ifc_contract(project, recommended_dict),
        )
        summary = {
            "primary_provider": "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
            "real_spatial_manifest_path": real_spatial_manifest_path.relative_to(self.repository).as_posix(),
            "unique_topology_count": len(set(topology_hashes)),
            "legacy_foundation_package": legacy_summary,
        }
        rules_files = [
            "configs/phoenix/jurisdictions/suriname/suriname_regulatory_use_policy_v1_0.json",
            "configs/phoenix/jurisdictions/suriname/suriname_structural_rule_registry_v1_0.json",
            "configs/phoenix/building_code_profiles/foundations/sr_foundation_v1_0.json",
        ]
        rules_basis = []
        for relative in rules_files:
            path = self.repository / relative
            if not path.is_file():
                raise RuntimeError(f"PHASE19_R4_RULE_BASIS_MISSING:{relative}")
            rules_basis.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        manifest = {
            "schema": "PHOENIX_PHASE19_R4_FIVE_VARIANT_MANIFEST_V1",
            "run_id": run_id,
            "project_id": project["project_id"],
            "variant_count": 5,
            "variant_order": list("ABCDE"),
            "recommended_variant_id": recommended.variant_id,
            "selection_status": "AWAITING_USER_SELECTION",
            "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
            "variant_provider": "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
            "unique_topology_count": len(set(topology_hashes)),
            "real_spatial_manifest_path": real_spatial_manifest_path.relative_to(self.repository).as_posix(),
            "project": project,
            "variants": variant_dicts,
            "summary": summary,
            "assumptions": assumptions,
        }
        manifest_path = output_dir / "five_variant_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        evidence = dict(session.get("evidence") or {})
        brief = self._clean(session.get("brief"))
        if brief and "project_intake" not in evidence:
            evidence["project_intake"] = {
                "project_brief": self._artifact(
                    brief,
                    self._clean(session.get("session_file")) or "official-start-screen",
                )
            }
        evidence["site_and_regulatory_analysis"] = {
            "location_evidence": self._evidence_artifact(
                "phase19-r4-location-evidence", "official-start-upload-batch", upload,
                verification_scope=upload["verification_scope"], survey_verified=False,
                cadastral_verified=False, professional_review_required=True,
            ),
            "applicable_rules": self._evidence_artifact(
                "phase19-r4-preliminary-rule-basis", "phoenix-suriname-policy-bundle", rules_basis,
                legal_applicability_verified=False, authority_confirmation_required=True,
                professional_review_required=True,
            ),
        }
        evidence["five_design_variants"] = {
            "five_variant_manifest": self._evidence_artifact(
                "phase19-r4-five-variant-manifest", manifest_path.relative_to(self.repository).as_posix(), manifest,
                concept_only=True, professional_review_required=True,
            )
        }
        return {
            "project": project,
            "design_variants": variant_dicts,
            "evidence": evidence,
            "manifest": manifest,
            "manifest_path": manifest_path.relative_to(self.repository).as_posix(),
            "variant_files": real_variant_files,
            "real_spatial_manifest_path": real_spatial_manifest_path.relative_to(self.repository).as_posix(),
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

        upload_batch = self._clean(session.get("upload_batch"))
        if upload_batch:
            evidence["project_uploads"] = self.validate_upload_batch(upload_batch)

        contract = {
            "project_id": self._project_id(session),
            "instruction": instruction,
            "location_reference": self._location_reference(session),
            "requested_outputs": outputs,
            "design_variants": variants,
            "selected_variant_id": self._clean(session.get("selected_variant_id")) or None,
            "verified_inputs": session.get("verified_inputs", {}),
            "evidence": session.get("evidence") or evidence,
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

    def _existing_for_fingerprint(self, fingerprint: str) -> StartScreenBridgeResult | None:
        if not self.output_root.is_dir():
            return None
        for path in sorted(self.output_root.glob("P19-*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                continue
            if payload.get("request_fingerprint") == fingerprint:
                payload["duplicate_run_reused"] = True
                return StartScreenBridgeResult(
                    run_id=str(payload["run_id"]), path=path, payload=payload
                )
        return None

    def plan(
        self,
        session: Mapping[str, Any],
        *,
        persist: bool = True,
        force_replan: bool = False,
    ) -> StartScreenBridgeResult:
        # PHOENIX_4_6_19_PHASE19_FRESH_RUN_REAL_VARIANT_BINDING_R2
        # Determine identity from the incoming user request first. Concept
        # authoring must never change the request/run identity.
        initial_contract = self.build_contract(session)
        fingerprint = self._request_fingerprint(initial_contract)
        if persist and not force_replan:
            existing = self._existing_for_fingerprint(fingerprint)
            if existing is not None:
                return existing
        run_id = self._run_id(initial_contract)

        runtime_session = dict(session)
        location_ready = bool(self._location_reference(runtime_session))
        upload_ready = bool(self._clean(runtime_session.get("upload_batch")))
        if location_ready and upload_ready:
            # A fresh run always authors and binds its own current-run
            # concept package. Never inherit _phase19_r4_concept_package
            # from a previous run/session.
            runtime_session.pop("_phase19_r4_concept_package", None)
            concept = self.prepare_concept_inputs(runtime_session, run_id)
            runtime_session["design_variants"] = concept["design_variants"]
            runtime_session["evidence"] = concept["evidence"]
            runtime_session["phase19_r4_project"] = concept["project"]
            runtime_session["phase19_r4_source_run_id"] = run_id
            runtime_session["_phase19_r4_concept_package"] = {
                "manifest_path": concept["manifest_path"],
                "variant_files": concept["variant_files"],
                "real_spatial_manifest_path": concept["real_spatial_manifest_path"],
                "variant_provider": "PHOENIX_TROPICAL_REAL_SPATIAL_LAYOUT_v1",
                "variant_count": 5,
                "variant_order": list("ABCDE"),
                "recommended_variant_id": concept["manifest"]["recommended_variant_id"],
                "selection_status": "AWAITING_USER_SELECTION",
                "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
                "survey_verified": False,
                "cadastral_verified": False,
                "legal_applicability_verified": False,
                "source_run_id": run_id,
            }

        contract = self.build_contract(runtime_session)
        orchestration = self.service.run(contract)
        missing = []
        for key in ("instruction", "location_reference", "requested_outputs"):
            if contract.get(key) in (None, "", [], {}):
                missing.append(key)
        payload = {
            "schema": "PHOENIX_START_SCREEN_INTEGRATED_PROJECT_BRIDGE_V1",
            "version": "1.1.0",
            "run_id": run_id,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "session_id": contract["start_screen_context"]["session_id"],
            "upload_batch": contract["start_screen_context"]["upload_batch"],
            "request_fingerprint": fingerprint,
            "duplicate_run_reused": False,
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
        concept_package = runtime_session.get("_phase19_r4_concept_package")
        if isinstance(concept_package, Mapping):
            concept_package = dict(concept_package)
            source_run_id = self._clean(concept_package.get("source_run_id"))
            if source_run_id and source_run_id != run_id:
                raise RuntimeError(
                    f"PHASE19_CONCEPT_PACKAGE_RUN_ID_DENY:{source_run_id}:{run_id}"
                )
            payload["concept_package"] = concept_package
        path = None
        if persist:
            self.output_root.mkdir(parents=True, exist_ok=True)
            path = self.output_root / f"{run_id}.json"
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return StartScreenBridgeResult(run_id=run_id, path=path, payload=payload)

    def _session_for_run(self, run_id: str) -> tuple[Path, dict[str, Any]]:
        root = self.repository / "outputs" / "runtime" / "phoenix_start_v3_sessions"
        for path in sorted(root.glob("PHX-*.json"), reverse=True):
            session = json.loads(path.read_text(encoding="utf-8-sig"))
            try:
                contract = self.build_contract(session)
            except (ValueError, TypeError):
                continue
            if self._run_id(contract) == run_id:
                return path, session
        raise ValueError("PHASE19_RESUME_SESSION_NOT_FOUND")

    def resume(
        self,
        run_id: str,
        updates: Mapping[str, Any],
        *,
        persist: bool = True,
    ) -> StartScreenBridgeResult:
        run_id = self._clean(run_id).upper()
        previous = self.get(run_id)
        if previous is None:
            raise ValueError("PHASE19_RESUME_RUN_NOT_FOUND")
        allowed_statuses = {
            "HOLD_MISSING_PROJECT_INPUTS",
            "HOLD_MISSING_VERIFIED_INPUTS",
            "WAITING_FOR_EVIDENCE",
            "WAITING_FOR_FIVE_VARIANTS",
        }
        if previous.get("status") not in allowed_statuses:
            raise ValueError("PHASE19_RESUME_STATUS_DENY")
        location_reference = self._clean(updates.get("location_reference"))
        upload_batch = self._clean(updates.get("upload_batch"))
        if not location_reference:
            raise ValueError("PHASE19_RESUME_LOCATION_REQUIRED")
        self.validate_upload_batch(upload_batch)
        session_path, session = self._session_for_run(run_id)
        session["location_reference"] = location_reference
        session["upload_batch"] = upload_batch
        session["resumed_from_run_id"] = run_id
        concept = self.prepare_concept_inputs(session, run_id)
        session["design_variants"] = concept["design_variants"]
        session["evidence"] = concept["evidence"]
        session["phase19_r4_project"] = concept["project"]
        session["phase19_r4_source_run_id"] = run_id
        session["_phase19_r4_concept_package"] = {
            "manifest_path": concept["manifest_path"],
            "variant_files": concept["variant_files"],
            "variant_count": 5,
            "variant_order": list("ABCDE"),
            "recommended_variant_id": concept["manifest"]["recommended_variant_id"],
            "selection_status": "AWAITING_USER_SELECTION",
            "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
            "survey_verified": False,
            "cadastral_verified": False,
            "legal_applicability_verified": False,
        }
        if persist:
            session_path.write_text(
                json.dumps(session, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        result = self.plan(session, persist=persist, force_replan=True)
        result.payload["resumed_from_run_id"] = run_id
        result.payload["safe_resume"] = True
        if persist and result.path is not None:
            result.path.write_text(
                json.dumps(result.payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        return result

    def get(self, run_id: str) -> dict[str, Any] | None:
        run_id = self._clean(run_id)
        if not re.fullmatch(r"P19-[A-F0-9]{16}", run_id):
            raise ValueError("PHASE19_RUN_ID_DENY")
        path = self.output_root / f"{run_id}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))
