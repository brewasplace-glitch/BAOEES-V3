"""Phoenix Autonomous Project Bootstrap & Session-Driven Orchestrator v1.0.

This layer closes the gap between the Official Start Screen and project engines:
- a start-screen session becomes a durable project workspace;
- desired outputs become a dependency/capability plan;
- autonomous mode never selects legacy pilot-specific runners;
- session/project/upload/output context is passed to the generic orchestrator;
- missing generic capabilities produce a controlled BLOCKED state, never false success.
"""
from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_id(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-._")
    return value[:80]


def portable_path_reference(path: Path, repository: Path) -> str:
    """Return repo-relative path when provable, otherwise a stable absolute path.

    On Windows, tempfile paths can surface through both long-path and 8.3 aliases.
    Path.relative_to() then raises even though both strings identify the same
    location. A manifest reference must never make project bootstrap fail.
    """
    resolved_path = path.resolve()
    resolved_repo = repository.resolve()
    try:
        return resolved_path.relative_to(resolved_repo).as_posix()
    except ValueError:
        return str(resolved_path)


@dataclass
class BootstrapResult:
    project_id: str
    workspace: str
    project_manifest: str
    digital_twin_state: str
    orchestration_plan: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "workspace": self.workspace,
            "project_manifest": self.project_manifest,
            "digital_twin_state": self.digital_twin_state,
            "orchestration_plan": self.orchestration_plan,
        }


class AutonomousProjectOrchestrator:
    VERSION = "1.2.0"

    def __init__(self, repository: Path, config_path: Path | None = None):
        self.repository = repository.resolve()
        self.config_path = (
            config_path.resolve()
            if config_path is not None
            else self.repository / "configs" / "phoenix" / "autonomous_project_orchestrator_v1_0.json"
        )
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Session / project bootstrap
    # ------------------------------------------------------------------
    def derive_project_id(self, session: dict[str, Any]) -> str:
        selected = _safe_id(str(session.get("selected_project") or ""))
        if selected:
            return selected

        brief = str(session.get("brief") or "").strip()
        if brief:
            first = brief.splitlines()[0].strip()
            candidate = _safe_id(first)
            # Explicit user project ids like PHOENIX-PAT-001 should be preserved.
            if (
                3 <= len(candidate) <= 80
                and " " not in first
                and re.fullmatch(r"[A-Za-z0-9._-]+", first)
            ):
                return candidate

        ptype = _safe_id(str(session.get("project_type") or "PROJECT")) or "PROJECT"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"PHX-{ptype}-{stamp}-{secrets.token_hex(3).upper()}"

    def bootstrap_session(self, session: dict[str, Any], session_file: Path) -> BootstrapResult:
        project_id = self.derive_project_id(session)
        workspace = self.repository / "projects" / "runtime" / project_id
        for rel in ("inputs", "digital_twin", "orchestration", "results", "logs"):
            (workspace / rel).mkdir(parents=True, exist_ok=True)

        session_copy = workspace / "inputs" / "project_analysis_session.json"
        session_copy.write_text(
            json.dumps(session, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        upload_ref = None
        batch = str(session.get("upload_batch") or "").strip()
        if batch:
            upload_root = self.repository / "inputs" / "runtime" / "official_start_v3_uploads" / batch
            manifest = upload_root / "upload_manifest.json"
            upload_ref = {
                "batch_id": batch,
                "root": upload_root.relative_to(self.repository).as_posix(),
                "manifest": (
                    manifest.relative_to(self.repository).as_posix()
                    if manifest.is_file()
                    else None
                ),
                "available": upload_root.is_dir(),
            }

        manifest_value = {
            "schema_version": "phoenix.autonomous-project-manifest/1.0",
            "orchestrator_version": self.VERSION,
            "project_id": project_id,
            "project_type": session.get("project_type"),
            "project_mode": session.get("project_mode"),
            "brief": session.get("brief"),
            "selected_project": session.get("selected_project"),
            "desired_outputs": session.get("desired_outputs", []),
            "session_id": session.get("session_id"),
            "source_session_file": portable_path_reference(session_file, self.repository),
            "upload": upload_ref,
            "created_utc": utc_now(),
            "release": {
                "production_acceptance_test": "PENDING",
                "production_release": "LOCKED",
                "automatic_professional_approval": False,
            },
        }
        manifest_path = workspace / "project_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest_value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        twin = {
            "schema_version": "phoenix.digital-twin-project-state/1.0",
            "project_id": project_id,
            "session_id": session.get("session_id"),
            "state": "BOOTSTRAPPED",
            "source_of_truth": "project_manifest.json",
            "disciplines": {},
            "desired_outputs": session.get("desired_outputs", []),
            "release": manifest_value["release"],
            "updated_utc": utc_now(),
        }
        twin_path = workspace / "digital_twin" / "project_state.json"
        twin_path.write_text(
            json.dumps(twin, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        plan = self.build_plan(session, project_id)
        plan_path = workspace / "orchestration" / "dependency_plan.json"
        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        return BootstrapResult(
            project_id=project_id,
            workspace=workspace.relative_to(self.repository).as_posix(),
            project_manifest=manifest_path.relative_to(self.repository).as_posix(),
            digital_twin_state=twin_path.relative_to(self.repository).as_posix(),
            orchestration_plan=plan_path.relative_to(self.repository).as_posix(),
        )

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def build_plan(self, session: dict[str, Any], project_id: str) -> dict[str, Any]:
        output_map = self.config["output_capability_map"]
        capabilities = self.config["capabilities"]
        requested_outputs = [str(x) for x in session.get("desired_outputs", [])]

        requested_caps: set[str] = {"project_bootstrap", "intake_normalization"}
        unknown_outputs: list[str] = []
        for output_id in requested_outputs:
            cap_list = output_map.get(output_id)
            if not cap_list:
                unknown_outputs.append(output_id)
                continue
            requested_caps.update(cap_list)

        # Expand dependencies transitively.
        changed = True
        while changed:
            changed = False
            for cap_id in list(requested_caps):
                cap = capabilities.get(cap_id, {})
                for dep in cap.get("depends_on", []):
                    if dep not in requested_caps:
                        requested_caps.add(dep)
                        changed = True

        order = self.config["capability_order"]
        steps = []
        for index, cap_id in enumerate([x for x in order if x in requested_caps], 1):
            cap = capabilities[cap_id]
            availability = self.capability_availability(cap_id)
            steps.append({
                "step": index,
                "capability_id": cap_id,
                "label": cap["label"],
                "depends_on": cap.get("depends_on", []),
                "execution_mode": cap.get("execution_mode", "adapter"),
                "availability": availability,
                "status": "PENDING",
            })

        return {
            "schema_version": "phoenix.autonomous-dependency-plan/1.0",
            "orchestrator_version": self.VERSION,
            "project_id": project_id,
            "session_id": session.get("session_id"),
            "project_type": session.get("project_type"),
            "requested_outputs": requested_outputs,
            "unknown_outputs": unknown_outputs,
            "capability_count": len(steps),
            "steps": steps,
            "legacy_pilot_runners_allowed": False,
            "created_utc": utc_now(),
        }

    def capability_availability(self, capability_id: str) -> dict[str, Any]:
        cap = self.config["capabilities"][capability_id]
        if cap.get("execution_mode") == "internal":
            return {
                "status": "AVAILABLE",
                "adapter": "internal",
                "runner": None,
            }

        candidates = [str(x) for x in cap.get("runner_candidates", [])]
        discovered = []
        for rel in candidates:
            path = self.repository / rel
            if path.is_file():
                discovered.append(rel)

        safe = [
            rel for rel in discovered
            if "pilot" not in rel.lower()
            and "moskee" not in rel.lower()
            and "plutostraat" not in rel.lower()
            and "bruynzeel" not in rel.lower()
        ]
        if safe and cap.get("session_adapter_ready", False):
            return {
                "status": "AVAILABLE",
                "adapter": "generic_session_adapter",
                "runner": safe[0],
                "discovered_candidates": discovered,
            }
        if safe:
            return {
                "status": "DISCOVERED_UNADAPTED",
                "adapter": None,
                "runner": safe[0],
                "discovered_candidates": discovered,
            }
        return {
            "status": "MISSING_GENERIC_CAPABILITY",
            "adapter": None,
            "runner": None,
            "discovered_candidates": discovered,
        }

    # ------------------------------------------------------------------
    # Runtime orchestration
    # ------------------------------------------------------------------
    def _write_adapter_state(
        self,
        workspace: Path,
        session: dict[str, Any],
        bootstrap: dict[str, Any],
        capability_states: dict[str, Any],
    ) -> Path:
        path = workspace / "orchestration" / "adapter_state.json"
        path.write_text(
            json.dumps({
                "schema_version": "phoenix.session-adapter-state/1.0",
                "orchestrator_version": self.VERSION,
                "project_id": bootstrap["project_id"],
                "session_id": session["session_id"],
                "capabilities": capability_states,
                "updated_utc": utc_now(),
            }, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def _run_adapter(
        self,
        *,
        runner_ref: str,
        session_file: Path,
        workspace: Path,
        adapter_output: Path,
        log_path: Path,
    ) -> tuple[int, dict[str, Any] | None]:
        runner = (self.repository / runner_ref).resolve()
        if not runner.is_file():
            return 10, {
                "status": "BLOCKED",
                "blockers": [{
                    "reason": "SESSION_ADAPTER_RUNNER_MISSING",
                    "message": f"Session Adapter runner ontbreekt: {runner_ref}",
                }],
                "outputs": [],
            }

        adapter_output.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(runner),
            "--session-file", str(session_file),
            "--workspace", str(workspace),
            "--output-dir", str(adapter_output),
            "--expect-session-adapted",
        ]
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8", newline="\n") as log:
            log.write("PROJECT PHOENIX GENERIC SESSION ADAPTER\n")
            log.write(json.dumps(command, ensure_ascii=False) + "\n\n")
            log.flush()
            proc = subprocess.run(
                command,
                cwd=str(self.repository),
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )

        result_path = adapter_output / "adapter_result.json"
        result = None
        if result_path.is_file():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                result = None
        return int(proc.returncode), result

    def run_session(self, session_file: Path, output_dir: Path) -> int:
        session_file = session_file.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        session = json.loads(session_file.read_text(encoding="utf-8"))

        if str(session.get("project_mode") or "").lower() != "autonomous":
            raise ValueError("Session is niet in Autonomous Project Mode.")

        bootstrap = session.get("bootstrap")
        if not isinstance(bootstrap, dict) or not bootstrap.get("workspace"):
            result = self.bootstrap_session(session, session_file)
            bootstrap = result.to_dict()
            session["bootstrap"] = bootstrap
            session_file.write_text(
                json.dumps(session, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        workspace = self.repository / bootstrap["workspace"]
        plan_path = self.repository / bootstrap["orchestration_plan"]
        # Rebuild plan so newly installed adapters are reflected immediately.
        plan = self.build_plan(session, bootstrap["project_id"])
        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        progress_path = output_dir / "progress.json"

        def progress(percent: int, status: str, step: str, extra: dict[str, Any] | None = None):
            value = {
                "schema_version": "phoenix.autonomous-progress/1.1",
                "session_id": session["session_id"],
                "project_id": bootstrap["project_id"],
                "percent": int(percent),
                "status": status,
                "step": step,
                "updated_utc": utc_now(),
            }
            if extra:
                value.update(extra)
            progress_path.write_text(
                json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (workspace / "orchestration" / "progress.json").write_text(
                json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        progress(3, "RUNNING", "Projectworkspace en sessiecontext laden")

        blockers: list[dict[str, Any]] = []
        capability_states: dict[str, Any] = {}
        produced: list[str] = [
            bootstrap["project_manifest"],
            bootstrap["digital_twin_state"],
            bootstrap["orchestration_plan"],
        ]
        steps = plan["steps"]
        total = max(1, len(steps))

        for idx, step in enumerate(steps, 1):
            cap_id = step["capability_id"]
            availability = self.capability_availability(cap_id)
            step["availability"] = availability

            # Internal control capabilities always execute in-process.
            if step["execution_mode"] == "internal":
                step["status"] = "PASSED"
                capability_states[cap_id] = {
                    "status": "PASSED",
                    "label": step["label"],
                    "outputs": [],
                    "blockers": [],
                }
                self._write_adapter_state(workspace, session, bootstrap, capability_states)
                pct = min(92, 5 + round((idx / total) * 80))
                progress(pct, "RUNNING", f"Capability gereed: {step['label']}")
                continue

            # If a declared dependency did not pass, do not execute the adapter.
            failed_deps = [
                dep for dep in step.get("depends_on", [])
                if (capability_states.get(dep) or {}).get("status") != "PASSED"
            ]
            if failed_deps:
                block = {
                    "capability_id": cap_id,
                    "label": step["label"],
                    "reason": "BLOCKED_DEPENDENCY",
                    "dependencies": failed_deps,
                    "message": "Session Adapter niet gestart omdat vereiste upstream-capability niet PASSED is.",
                }
                blockers.append(block)
                step["status"] = "BLOCKED_DEPENDENCY"
                capability_states[cap_id] = {
                    "status": "BLOCKED_DEPENDENCY",
                    "label": step["label"],
                    "outputs": [],
                    "blockers": [block],
                }
                self._write_adapter_state(workspace, session, bootstrap, capability_states)
                pct = min(92, 5 + round((idx / total) * 80))
                progress(pct, "RUNNING", f"Dependency geblokkeerd: {step['label']}")
                continue

            if availability["status"] != "AVAILABLE":
                block = {
                    "capability_id": cap_id,
                    "label": step["label"],
                    "reason": availability["status"],
                    "runner": availability.get("runner"),
                    "message": "Generieke Session Adapter is niet uitvoerbaar.",
                }
                blockers.append(block)
                step["status"] = "BLOCKED"
                capability_states[cap_id] = {
                    "status": "BLOCKED",
                    "label": step["label"],
                    "outputs": [],
                    "blockers": [block],
                }
                self._write_adapter_state(workspace, session, bootstrap, capability_states)
                continue

            adapter_root = workspace / "results" / "session_adapters" / cap_id
            log_path = workspace / "logs" / f"session_adapter_{cap_id}.log"
            rc, result = self._run_adapter(
                runner_ref=availability["runner"],
                session_file=session_file,
                workspace=workspace,
                adapter_output=adapter_root,
                log_path=log_path,
            )

            if not isinstance(result, dict):
                status = "FAILED"
                cap_blockers = [{
                    "capability_id": cap_id,
                    "reason": "ADAPTER_RESULT_MISSING",
                    "message": f"Session Adapter leverde geen geldig adapter_result.json (exitcode {rc}).",
                }]
                outputs = []
            else:
                status = str(result.get("status") or ("PASSED" if rc == 0 else "BLOCKED" if rc == 10 else "FAILED")).upper()
                outputs = [str(x) for x in result.get("outputs", [])]
                cap_blockers = list(result.get("blockers", []))
                adapter_metadata = dict(result.get("metadata") or {})

            # Normalize adapter terminal states for orchestration.
            if rc == 0 and status == "PASSED":
                step["status"] = "PASSED"
                normalized = "PASSED"
            elif rc == 10 or status.startswith("BLOCKED"):
                step["status"] = "BLOCKED"
                normalized = "BLOCKED"
                for item in cap_blockers or [{
                    "reason":"SESSION_ADAPTER_BLOCKED",
                    "message":f"{step['label']} is gecontroleerd geblokkeerd.",
                }]:
                    blockers.append({
                        "capability_id": cap_id,
                        "label": step["label"],
                        **item,
                    })
            else:
                step["status"] = "FAILED"
                normalized = "FAILED"
                blockers.append({
                    "capability_id": cap_id,
                    "label": step["label"],
                    "reason": "SESSION_ADAPTER_FAILED",
                    "return_code": rc,
                    "message": f"Session Adapter stopte met exitcode {rc}.",
                })

            capability_states[cap_id] = {
                "status": normalized,
                "adapter_status": status,
                "label": step["label"],
                "runner": availability["runner"],
                "outputs": outputs,
                "blockers": cap_blockers,
                "metadata": adapter_metadata if isinstance(result, dict) else {},
                "log": log_path.relative_to(self.repository).as_posix(),
            }
            produced.extend(outputs)
            self._write_adapter_state(workspace, session, bootstrap, capability_states)

            pct = min(92, 5 + round((idx / total) * 80))
            progress(
                pct,
                "RUNNING",
                f"Session Adapter: {step['label']} → {normalized}",
                {"active_capability": cap_id},
            )

        plan["evaluated_utc"] = utc_now()
        plan["blocker_count"] = len(blockers)
        plan["capability_states"] = capability_states
        plan_path.write_text(
            json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        blockers_path = workspace / "orchestration" / "blockers.json"
        blockers_path.write_text(
            json.dumps({
                "schema_version": "phoenix.autonomous-blocker-register/1.1",
                "session_id": session["session_id"],
                "project_id": bootstrap["project_id"],
                "blocker_count": len(blockers),
                "blockers": blockers,
                "legacy_pilot_runner_blocked": True,
                "generic_session_adapter_masterpack": "1.0.0",
                "updated_utc": utc_now(),
            }, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        produced.append(blockers_path.relative_to(self.repository).as_posix())

        # Granular desired-output state. Adapter capabilities may pass while a
        # final requested deliverable is still only a concept candidate.
        output_states = {}
        output_map = self.config["output_capability_map"]
        output_level_blockers = []
        for output_id in session.get("desired_outputs", []):
            required = output_map.get(output_id, [])
            states = [(capability_states.get(cap) or {}).get("status", "NOT_PLANNED") for cap in required]
            explicit_coverage = []
            for cap in required:
                meta = (capability_states.get(cap) or {}).get("metadata") or {}
                coverage = (meta.get("desired_output_states") or {}).get(output_id)
                if isinstance(coverage, dict):
                    explicit_coverage.append({"capability_id":cap, **coverage})

            if any(x == "FAILED" for x in states):
                status = "FAILED"
            elif any(x != "PASSED" for x in states) or not required:
                status = "BLOCKED"
            elif explicit_coverage and any(str(x.get("status") or "").upper() != "PASSED" for x in explicit_coverage):
                status = "BLOCKED"
            else:
                status = "PASSED"

            output_states[output_id] = {
                "status": status,
                "required_capabilities": required,
                "capability_states": states,
                "adapter_output_coverage": explicit_coverage,
            }
            if status == "BLOCKED" and required and all(x == "PASSED" for x in states) and explicit_coverage:
                first = next((x for x in explicit_coverage if str(x.get("status") or "").upper() != "PASSED"), explicit_coverage[0])
                output_level_blockers.append({
                    "capability_id":"desired_output",
                    "output_id":output_id,
                    "label":output_id,
                    "reason":first.get("reason") or "DESIRED_OUTPUT_NOT_FINAL",
                    "message":first.get("message") or "Gewenste uitvoer is nog niet definitief geproduceerd.",
                })

        blockers.extend(output_level_blockers)
        plan["blocker_count"] = len(blockers)
        plan["desired_output_states"] = output_states
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        blockers_path.write_text(
            json.dumps({
                "schema_version": "phoenix.autonomous-blocker-register/1.2",
                "session_id": session["session_id"],
                "project_id": bootstrap["project_id"],
                "blocker_count": len(blockers),
                "blockers": blockers,
                "legacy_pilot_runner_blocked": True,
                "generic_session_adapter_masterpack": "1.0.0",
                "autonomous_architectural_bootstrap": "1.0.0",
                "updated_utc": utc_now(),
            }, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        result_index = {
            "schema_version": "phoenix.autonomous-result-index/1.2",
            "project_id": bootstrap["project_id"],
            "session_id": session["session_id"],
            "desired_outputs": session.get("desired_outputs", []),
            "desired_output_states": output_states,
            "capability_states": capability_states,
            "produced": sorted(set(produced)),
            "blocked_outputs": [k for k,v in output_states.items() if v["status"] != "PASSED"],
            "passed_outputs": [k for k,v in output_states.items() if v["status"] == "PASSED"],
            "production_release": "LOCKED",
            "updated_utc": utc_now(),
        }
        result_index_path = workspace / "results" / "result_index.json"
        result_index_path.write_text(
            json.dumps(result_index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        summary = {
            "schema_version": "phoenix.autonomous-session-orchestration-summary/1.2",
            "orchestrator_version": self.VERSION,
            "session_adapter_masterpack_version": "1.0.0",
            "autonomous_architectural_bootstrap_version": "1.0.0",
            "session_id": session["session_id"],
            "project_id": bootstrap["project_id"],
            "project_mode": session.get("project_mode"),
            "desired_output_count": len(session.get("desired_outputs", [])),
            "legacy_pilot_runners_invoked": False,
            "session_context_propagated": True,
            "project_workspace_created": True,
            "dependency_plan_created": True,
            "session_adapters_executed": True,
            "blocker_count": len(blockers),
            "blockers": blockers,
            "status": "BLOCKED" if blockers else "PASSED",
            "production_release": "LOCKED",
            "workspace": bootstrap["workspace"],
            "result_index": result_index_path.relative_to(self.repository).as_posix(),
            "finished_utc": utc_now(),
        }
        (output_dir / "orchestration_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (workspace / "orchestration" / "orchestration_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if blockers:
            progress(
                92,
                "BLOCKED",
                "Generic Session Adapters uitgevoerd; projectspecifieke input/dependencies blokkeren resterende output",
                {"blocker_count": len(blockers), "blockers": blockers[:12]},
            )
            return 10

        progress(100, "PASSED", "Alle geplande Generic Session Adapters zijn geslaagd")
        return 0
