from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

VERSION = "1.0.0"


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _iter_reasons(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        reason = value.get("reason")
        if reason:
            yield str(reason)
        reasons = value.get("reasons")
        if isinstance(reasons, list):
            for item in reasons:
                if item:
                    yield str(item)
        for child in value.values():
            yield from _iter_reasons(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_reasons(child)


def _import_required(global_sourcing: Dict[str, Any], acquisition: Dict[str, Any]) -> bool:
    reasons = set(_iter_reasons(global_sourcing)) | set(_iter_reasons(acquisition))
    import_reasons = {
        "GLOBAL_SUPPLIER_EVIDENCE_REQUIRED",
        "GLOBAL_PRODUCT_CANDIDATE_REQUIRED",
        "NO_STRUCTURED_GLOBAL_PRODUCT_EVIDENCE_ACQUIRED",
        "COMPLETE_LANDED_COST_EVIDENCE_REQUIRED",
    }
    if reasons & import_reasons:
        return True
    try:
        if int(global_sourcing.get("selected_import_count") or 0) > 0:
            return True
    except Exception:
        pass
    return False


def enforce_landed_cost_gate(workspace: Path) -> Dict[str, Any]:
    workspace = Path(workspace)
    architecture = workspace / "results" / "session_adapters" / "architecture"
    sourcing_path = architecture / "global_material_sourcing_register.json"
    landed_path = architecture / "landed_cost_register.json"
    acquisition_path = workspace / "sources" / "import_acquisition" / "global_supplier_import_acquisition_register.json"

    sourcing = _read_json(sourcing_path)
    landed = _read_json(landed_path)
    acquisition = _read_json(acquisition_path)

    if not landed:
        return {
            "status": "NO_LANDED_COST_REGISTER",
            "path": str(landed_path),
            "changed": False,
        }

    selected_imports = landed.get("selected_imports")
    if not isinstance(selected_imports, list):
        selected_imports = []

    import_required = _import_required(sourcing, acquisition)
    changed = False

    if not selected_imports and import_required:
        if landed.get("status") != "BLOCKED":
            landed["status"] = "BLOCKED"
            changed = True
        landed["gate_reason"] = "IMPORT_REQUIRED_BUT_NO_COMPLETE_LANDED_COST_EVIDENCE"
        landed["empty_import_pass_forbidden"] = True
        landed["production_release"] = "LOCKED"
        changed = True
    elif not selected_imports and not import_required:
        if landed.get("status") == "PASSED":
            landed["status"] = "NOT_APPLICABLE"
            changed = True
        landed["gate_reason"] = "NO_IMPORT_SELECTED_AND_NO_IMPORT_REQUIRED"
        landed["empty_import_pass_forbidden"] = True
        changed = True
    else:
        missing_complete = []
        required_keys = (
            "product_cost",
            "freight_cost",
            "destination_cost",
            "customs_duty",
            "tax",
            "fx_rate",
            "total_landed_cost",
        )
        for index, item in enumerate(selected_imports):
            if not isinstance(item, dict):
                missing_complete.append(index)
                continue
            missing = [key for key in required_keys if item.get(key) is None]
            if missing:
                missing_complete.append({"index": index, "missing": missing})
        if missing_complete:
            landed["status"] = "BLOCKED"
            landed["gate_reason"] = "SELECTED_IMPORT_LANDED_COST_INCOMPLETE"
            landed["incomplete_imports"] = missing_complete
            landed["production_release"] = "LOCKED"
            changed = True

    landed["gate_guard_version"] = VERSION
    if changed:
        _write_json(landed_path, landed)

    return {
        "status": landed.get("status"),
        "changed": changed,
        "path": str(landed_path),
        "import_required": import_required,
        "selected_import_count": len(selected_imports),
    }


def _infer_workspace(result: Any = None, args: Any = None, kwargs: Any = None) -> Optional[Path]:
    candidates = []
    if isinstance(kwargs, dict):
        for key in ("workspace", "project_workspace", "project_dir", "project_root"):
            value = kwargs.get(key)
            if value:
                candidates.append(Path(str(value)))
        pid = kwargs.get("project_id")
        if pid:
            repo = Path(__file__).resolve().parents[2]
            candidates.append(repo / "projects" / "runtime" / str(pid))

    def walk(value: Any) -> Optional[str]:
        if isinstance(value, dict):
            for key in ("project_id",):
                if value.get(key):
                    return str(value[key])
            for child in value.values():
                found = walk(child)
                if found:
                    return found
        elif isinstance(value, (list, tuple)):
            for child in value:
                found = walk(child)
                if found:
                    return found
        return None

    pid = walk(result) or walk(args) or walk(kwargs)
    if pid:
        repo = Path(__file__).resolve().parents[2]
        candidates.append(repo / "projects" / "runtime" / pid)

    for candidate in candidates:
        if candidate.exists() and (candidate / "results").exists():
            return candidate

    repo = Path(__file__).resolve().parents[2]
    runtime = repo / "projects" / "runtime"
    if runtime.exists():
        dirs = [p for p in runtime.iterdir() if p.is_dir()]
        dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        if dirs:
            return dirs[0]
    return None


def postprocess_adapter_result(result: Any, args: Any = None, kwargs: Any = None) -> Any:
    try:
        workspace = _infer_workspace(result=result, args=args, kwargs=kwargs)
        if workspace:
            gate = enforce_landed_cost_gate(workspace)
            if isinstance(result, dict):
                result.setdefault("landed_cost_gate_guard", gate)
    except Exception as exc:  # fail safe: never manufacture a pass
        if isinstance(result, dict):
            result.setdefault("landed_cost_gate_guard", {"status": "BLOCKED", "error": type(exc).__name__})
    return result
