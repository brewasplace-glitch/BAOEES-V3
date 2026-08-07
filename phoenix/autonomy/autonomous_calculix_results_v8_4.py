"""Project Phoenix autonomous CalculiX execution and v8.4 result normalization."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

ENGINE_ID = "PHX-STRUCT-AUTONOMOUS-CALCULIX-RESULTS-V8.4"
VERSION = "1.0.0"
RESULT_NORMALIZATION_VERSION = "8.4-autonomous-calculix/1.0"
REQUIRED_FIELDS = ("node_displacements", "node_reactions", "element_forces", "element_stresses")

class AutonomousCalculixBlocked(RuntimeError):
    def __init__(self, reason: str, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.reason = str(reason)
        self.message = str(message)
        self.details = dict(details or {})

def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]

def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except Exception:
        return path.resolve().as_posix()

def autonomous_calculix_execution_enabled(session: Mapping[str, Any] | None = None) -> bool:
    if os.environ.get("PHOENIX_TEST_MODE") == "1":
        return False
    return str((session or {}).get("project_mode") or "").strip().lower() == "autonomous"

def _program_files_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        raw = os.environ.get(key)
        if raw:
            roots.append(Path(raw))
    if os.name == "nt":
        roots.extend([Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")])
    out: list[Path] = []
    for root in roots:
        if root not in out:
            out.append(root)
    return out

def detect_calculix_executable() -> tuple[Path | None, dict[str, Any]]:
    checked: list[str] = []
    explicit = str(os.environ.get("PHOENIX_CALCULIX_EXECUTABLE") or "").strip()
    if explicit:
        p = Path(explicit)
        checked.append(str(p))
        if p.is_file():
            return p.resolve(), {"source": "PHOENIX_CALCULIX_EXECUTABLE", "checked": checked}
    for command in ("ccx", "ccx.exe", "calculix", "calculix.exe"):
        found = shutil.which(command)
        checked.append(command)
        if found and Path(found).is_file():
            return Path(found).resolve(), {"source": f"PATH:{command}", "checked": checked}
    candidates: list[Path] = []
    for root in _program_files_roots():
        checked.append(str(root))
        if not root.exists():
            continue
        candidates.extend(root.glob("FreeCAD */bin/ccx.exe"))
        candidates.extend(root.glob("FreeCAD*/bin/ccx.exe"))
        candidates.extend(root.glob("CalculiX*/ccx.exe"))
        candidates.extend(root.glob("CalculiX*/bin/ccx.exe"))
    candidates = sorted({p.resolve() for p in candidates if p.is_file()}, key=lambda p: str(p).lower())
    if candidates:
        return candidates[-1], {
            "source": "COMMON_WINDOWS_INSTALL_DISCOVERY",
            "checked": checked,
            "candidates": [str(p) for p in candidates],
        }
    return None, {"source": "NOT_FOUND", "checked": checked}

def calculix_version(executable: Path) -> dict[str, Any]:
    proc = subprocess.run([str(executable), "-v"], text=True, capture_output=True, timeout=30, check=False)
    combined = "\n".join(x for x in (proc.stdout, proc.stderr) if x).strip()
    match = re.search(r"\bVersion\s+([0-9]+(?:\.[0-9]+)+)", combined, re.I)
    return {
        "command": [str(executable), "-v"],
        "return_code": int(proc.returncode),
        "version": match.group(1) if match else None,
        "output": combined[:2000],
    }

def _safe_case_token(case_id: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(case_id)).strip("._")
    return token or "CASE"

def _known_model(analytical_model: Mapping[str, Any]):
    nodes = {str(x.get("id")): dict(x) for x in _items(analytical_model.get("nodes")) if isinstance(x, Mapping) and x.get("id")}
    members = {str(x.get("id")): dict(x) for x in _items(analytical_model.get("members")) if isinstance(x, Mapping) and x.get("id")}
    shells = {str(x.get("id")): dict(x) for x in _items(analytical_model.get("shells")) if isinstance(x, Mapping) and x.get("id")}
    if not nodes or (not members and not shells):
        raise AutonomousCalculixBlocked(
            "CALCULIX_ANALYTICAL_MODEL_REQUIRED",
            "Het v8.3 analytische model bevat onvoldoende nodes/elements voor echte CalculiX-uitvoering.",
        )
    return nodes, members, shells

def _support_node_ids(analytical_model: Mapping[str, Any], known_nodes: Mapping[str, Any]) -> list[str]:
    ids: list[str] = []
    for support in _items(analytical_model.get("supports")):
        if not isinstance(support, Mapping):
            continue
        for key in ("node_id", "node", "target_node_id"):
            node_id = str(support.get(key) or "").strip()
            if node_id and node_id in known_nodes and node_id not in ids:
                ids.append(node_id)
        for raw in _items(support.get("node_ids")):
            node_id = str(raw or "").strip()
            if node_id and node_id in known_nodes and node_id not in ids:
                ids.append(node_id)
    if not ids:
        raise AutonomousCalculixBlocked(
            "CALCULIX_SUPPORT_NODE_SET_REQUIRED",
            "Geen solver-supportnodes beschikbaar voor CalculiX-reactie-evidence.",
        )
    return sorted(ids)

def _mapping_from_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    mapping = dict((manifest.get("solver_mapping") or {}).get("calculix") or {})
    node_tags = mapping.get("node_tags") or {}
    if not isinstance(node_tags, Mapping) or not node_tags:
        raise AutonomousCalculixBlocked(
            "CALCULIX_SOLVER_MAPPING_REQUIRED",
            "v8.3 manifest bevat geen CalculiX node-tag mapping; Phoenix mappt solver-native IDs niet op gokbasis.",
        )
    return mapping

def _calculix_set_data_lines(values: Sequence[int], max_entries: int = 16) -> list[str]:
    """Return deterministic CalculiX set data lines within the parser entry limit."""
    if max_entries <= 0:
        raise ValueError("max_entries must be positive")
    entries = [str(int(value)) for value in values]
    return [
        ", ".join(entries[index:index + max_entries])
        for index in range(0, len(entries), max_entries)
    ]


def _validate_calculix_set_card_width(text: str, max_entries: int = 16) -> None:
    """Reject NSET/ELSET data rows that exceed CalculiX's 16-entry line limit."""
    if max_entries <= 0:
        raise ValueError("max_entries must be positive")

    active_set_keyword = None
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("**"):
            continue

        if line.startswith("*"):
            keyword = line.upper()
            if keyword.startswith("*NSET") or keyword.startswith("*ELSET"):
                active_set_keyword = line
            else:
                active_set_keyword = None
            continue

        if active_set_keyword is None:
            continue

        entry_count = len([part for part in line.split(",") if part.strip()])
        if entry_count > max_entries:
            raise AutonomousCalculixBlocked(
                "CALCULIX_SET_DATA_LINE_TOO_WIDE",
                (
                    f"CalculiX set-dataregel {line_number} bevat {entry_count} entries; "
                    f"maximum is {max_entries}."
                ),
                {
                    "line_number": line_number,
                    "entry_count": entry_count,
                    "maximum_entries": max_entries,
                    "set_keyword": active_set_keyword,
                    "line": line,
                },
            )

def _instrument_deck(text: str, *, support_tags: Sequence[int], element_ids: Sequence[str]) -> str:
    if "*END STEP" not in text.upper():
        raise AutonomousCalculixBlocked("CALCULIX_DECK_END_STEP_REQUIRED", "CalculiX basisdeck bevat geen *END STEP.")
    if not support_tags:
        raise AutonomousCalculixBlocked("CALCULIX_SUPPORT_NODE_SET_REQUIRED", "Support node tags ontbreken.")
    upper = text.upper()
    step_pos = upper.find("*STEP")
    if step_pos < 0:
        raise AutonomousCalculixBlocked("CALCULIX_DECK_STEP_REQUIRED", "CalculiX basisdeck bevat geen *STEP.")
    support_lines = _calculix_set_data_lines(support_tags)
    support_card = "\n*NSET, NSET=PHX_SUPPORT_NODES\n" + "\n".join(support_lines) + "\n"
    text = text[:step_pos] + support_card + text[step_pos:]
    end_pos = text.upper().rfind("*END STEP")
    lines = [
        "",
        "** PHOENIX v8.4 AUTONOMOUS RAW-EVIDENCE OUTPUT",
        "*NODE PRINT, NSET=NALL",
        "U",
        "*NODE PRINT, NSET=PHX_SUPPORT_NODES",
        "RF",
    ]
    for eid in element_ids:
        lines += [f"*EL PRINT, ELSET=E_{eid}", "S"]
    lines += [
        "*NODE FILE, OUTPUT=2D",
        "U",
        "*EL FILE, SECTION FORCES",
        "S, NOE",
        "** END PHOENIX v8.4 AUTONOMOUS RAW-EVIDENCE OUTPUT",
        "",
    ]
    instrumented = text[:end_pos] + "\n".join(lines) + text[end_pos:]
    _validate_calculix_set_card_width(instrumented)
    return instrumented

def _f(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))

def parse_calculix_dat(text: str) -> dict[str, Any]:
    displacements: dict[int, list[float]] = {}
    support_forces: dict[int, list[float]] = {}
    stresses_by_set: dict[str, list[list[float]]] = {}
    mode: str | None = None
    current_set: str | None = None
    seen_rows = False
    disp_heading = re.compile(r"displacements\s*\([^)]*\)\s*for\s+set\s+NALL\b", re.I)
    force_heading = re.compile(r"forces\s*\(fx\s*,\s*fy\s*,\s*fz\)\s*for\s+set\s+PHX_SUPPORT_NODES\b", re.I)
    stress_heading = re.compile(r"stresses\s*\([^)]*\)\s*for\s+set\s+([A-Za-z0-9_.-]+)\b", re.I)
    for raw in text.splitlines():
        line = raw.strip()
        if disp_heading.search(line):
            mode, current_set, seen_rows = "U", None, False
            continue
        if force_heading.search(line):
            mode, current_set, seen_rows = "RF", None, False
            continue
        sm = stress_heading.search(line)
        if sm:
            mode, current_set, seen_rows = "S", sm.group(1).upper(), False
            stresses_by_set.setdefault(current_set, [])
            continue
        if not line:
            if seen_rows:
                mode, current_set, seen_rows = None, None, False
            continue
        if mode is None:
            continue
        parts = line.replace(",", " ").split()
        try:
            if mode in {"U", "RF"} and len(parts) >= 4:
                tag = int(parts[0])
                vals = [_f(parts[1]), _f(parts[2]), _f(parts[3])]
                (displacements if mode == "U" else support_forces)[tag] = vals
                seen_rows = True
            elif mode == "S" and len(parts) >= 8:
                int(parts[0]); int(parts[1])
                stresses_by_set[current_set].append([_f(x) for x in parts[2:8]])
                seen_rows = True
        except (ValueError, TypeError):
            continue
    return {
        "node_displacements": displacements,
        "support_total_forces": support_forces,
        "stresses_by_set": stresses_by_set,
    }

def _canonical_frd_component(name: str) -> str:
    # CalculiX FRD commonly writes the x-z shear component as SZX rather than SXZ.
    # The stress/section-force tensor is symmetric for this output contract.
    token = str(name or "").strip().upper()
    aliases = {
        "SZX": "SXZ",
        "ZX": "XZ",
    }
    return aliases.get(token, token)


def _parse_frd_node_value_record(line: str, component_count: int) -> tuple[int, list[float]] | None:
    """Parse native CalculiX ASCII FRD -1 records.

    FRD is fixed-width, not whitespace-delimited. A valid real record can look like:
      -1 1-9.99960E+01-1.40890E-09 ...
    so ``split()`` cannot be used safely.
    """
    raw = line.rstrip("\r\n")
    match = re.match(r"^\s*-1\s*([0-9]+)(.*)$", raw)
    if not match:
        return None
    node = int(match.group(1))
    tail = match.group(2)
    number_pattern = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][-+]?\d+)?")
    values = [_f(token) for token in number_pattern.findall(tail)]
    if len(values) < component_count:
        return None
    return node, values[:component_count]


def parse_calculix_frd_last_stress(text: str) -> dict[int, dict[str, float]]:
    blocks: list[tuple[list[str], dict[int, list[float]]]] = []
    active = False
    components: list[str] = []
    values: dict[int, list[float]] = {}

    def close():
        nonlocal active, components, values
        if active and components and values:
            blocks.append((list(components), dict(values)))
        active = False
        components = []
        values = {}

    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("-4"):
            close()
            parts = stripped.split()
            active = len(parts) > 1 and parts[1].upper() == "STRESS"
            continue
        if not active:
            continue
        if stripped.startswith("-5"):
            parts = stripped.split()
            if len(parts) > 1:
                components.append(_canonical_frd_component(parts[1]))
            continue
        if stripped.startswith("-1"):
            parsed = _parse_frd_node_value_record(raw, len(components))
            if parsed is not None:
                node, vals = parsed
                values[node] = vals
            continue
        if stripped.startswith("-3"):
            close()
    close()
    if not blocks:
        return {}
    comps, rows = blocks[-1]
    return {
        node: {comps[i]: float(vals[i]) for i in range(min(len(comps), len(vals)))}
        for node, vals in rows.items()
    }

def _stress_envelope(rows: Sequence[Sequence[float]]) -> dict[str, float]:
    names = ("SXX", "SYY", "SZZ", "SXY", "SXZ", "SYZ")
    if not rows:
        return {}
    out: dict[str, float] = {}
    for i, name in enumerate(names):
        vals = [float(row[i]) for row in rows if len(row) > i]
        if vals:
            out[f"{name}_MIN"] = min(vals)
            out[f"{name}_MAX"] = max(vals)
            out[f"{name}_MEAN"] = sum(vals) / len(vals)
            out[f"{name}_MAX_ABS"] = max(abs(v) for v in vals)
    return out

def _section_force_components(row: Mapping[str, float]) -> dict[str, float]:
    # CalculiX SECTION FORCES semantics (beam local axes):
    # xx=V1, yy=V2, zz=N, xy=T, xz/zx=M2, yz=M1.
    aliases = {
        "V1": ("SXX", "XX"),
        "V2": ("SYY", "YY"),
        "N": ("SZZ", "ZZ"),
        "T": ("SXY", "XY"),
        "M2": ("SXZ", "SZX", "XZ", "ZX"),
        "M1": ("SYZ", "YZ"),
    }
    out: dict[str, float] = {}
    for target, choices in aliases.items():
        for key in choices:
            if key in row:
                out[target] = float(row[key])
                break
    return out

def _load_case_ids(action_load_model: Mapping[str, Any]) -> list[str]:
    ids = [str(x.get("id")) for x in _items(action_load_model.get("load_cases")) if isinstance(x, Mapping) and x.get("id")]
    if not ids:
        raise AutonomousCalculixBlocked("CALCULIX_LOAD_CASES_REQUIRED", "Geen v8.2 load cases beschikbaar.")
    return ids

def _normalize_case(
    *,
    case_id: str,
    dat_text: str,
    frd_text: str,
    analytical_model: Mapping[str, Any],
    mapping: Mapping[str, Any],
    equivalent_nodal_loads: Mapping[str, Any],
    raw_reference: str,
):
    nodes, members, shells = _known_model(analytical_model)
    node_tags = {str(k): int(v) for k, v in (mapping.get("node_tags") or {}).items()}
    inverse = {tag: nid for nid, tag in node_tags.items()}
    parsed = parse_calculix_dat(dat_text)
    u_raw = parsed["node_displacements"]
    rf_raw = parsed["support_total_forces"]
    stress_sets = parsed["stresses_by_set"]
    section_raw = parse_calculix_frd_last_stress(frd_text)

    missing_nodes = [nid for nid in nodes if node_tags.get(nid) not in u_raw]
    if missing_nodes:
        raise AutonomousCalculixBlocked(
            "CALCULIX_NODE_DISPLACEMENTS_INCOMPLETE",
            "CalculiX displacement-output kon niet volledig naar Phoenix node IDs worden genormaliseerd.",
            {"case_id": case_id, "missing_node_ids": missing_nodes[:50]},
        )
    node_displacements = {
        nid: {"UX": float(u_raw[tag][0]), "UY": float(u_raw[tag][1]), "UZ": float(u_raw[tag][2])}
        for nid, tag in node_tags.items() if nid in nodes and tag in u_raw
    }

    loads_case = dict((equivalent_nodal_loads or {}).get(case_id) or {})
    node_reactions: dict[str, dict[str, float]] = {}
    for tag, total in rf_raw.items():
        nid = inverse.get(tag)
        if not nid:
            continue
        applied = list(loads_case.get(nid) or [0.0, 0.0, 0.0])
        while len(applied) < 3:
            applied.append(0.0)
        node_reactions[nid] = {
            "FX": float(total[0]) - float(applied[0]),
            "FY": float(total[1]) - float(applied[1]),
            "FZ": float(total[2]) - float(applied[2]),
        }
    support_ids = _support_node_ids(analytical_model, nodes)
    missing_reactions = [nid for nid in support_ids if nid not in node_reactions]
    if missing_reactions:
        raise AutonomousCalculixBlocked(
            "CALCULIX_SUPPORT_REACTIONS_INCOMPLETE",
            "CalculiX supportreacties ontbreken voor een of meer supportnodes.",
            {"case_id": case_id, "missing_node_ids": missing_reactions[:50]},
        )

    element_stresses: dict[str, dict[str, float]] = {}
    for eid in list(members) + list(shells):
        env = _stress_envelope(stress_sets.get(f"E_{eid}".upper()) or [])
        if env:
            element_stresses[eid] = env
    missing_stress = [eid for eid in list(members) + list(shells) if eid not in element_stresses]
    if missing_stress:
        raise AutonomousCalculixBlocked(
            "CALCULIX_ELEMENT_STRESSES_INCOMPLETE",
            "CalculiX integratiepuntspanningen konden niet voor alle Phoenix elementen worden genormaliseerd.",
            {"case_id": case_id, "missing_element_ids": missing_stress[:50]},
        )

    element_forces: dict[str, dict[str, float]] = {}
    for mid, member in members.items():
        ni = str(member.get("node_i") or "")
        nj = str(member.get("node_j") or "")
        ti, tj = node_tags.get(ni), node_tags.get(nj)
        ri = _section_force_components(section_raw.get(ti, {})) if ti is not None else {}
        rj = _section_force_components(section_raw.get(tj, {})) if tj is not None else {}
        if len(ri) < 6 or len(rj) < 6:
            continue
        element_forces[mid] = {
            "END_I_V1": ri["V1"], "END_I_V2": ri["V2"], "END_I_N": ri["N"],
            "END_I_T": ri["T"], "END_I_M2": ri["M2"], "END_I_M1": ri["M1"],
            "END_J_V1": rj["V1"], "END_J_V2": rj["V2"], "END_J_N": rj["N"],
            "END_J_T": rj["T"], "END_J_M2": rj["M2"], "END_J_M1": rj["M1"],
        }
    missing_member_forces = [mid for mid in members if mid not in element_forces]
    if missing_member_forces:
        raise AutonomousCalculixBlocked(
            "CALCULIX_MEMBER_SECTION_FORCES_INCOMPLETE",
            "CalculiX SECTION FORCES-output kon niet voor alle beam-members aan Phoenix IDs worden gekoppeld.",
            {"case_id": case_id, "missing_member_ids": missing_member_forces[:50]},
        )

    result = {
        "solver": "calculix",
        "case_id": case_id,
        "status": "COMPLETED",
        "converged": True,
        "normalization_version": RESULT_NORMALIZATION_VERSION,
        "units": {"length": "m", "force": "kN", "stress": "kN/m2", "rotation": "rad"},
        "node_displacements": node_displacements,
        "node_reactions": node_reactions,
        "element_forces": element_forces,
        "element_stresses": element_stresses,
        "raw_solver_evidence_reference": raw_reference,
        "normalization_details": {
            "node_displacements": "CALCULIX_NODE_PRINT_U",
            "node_reactions": "CALCULIX_NODE_PRINT_RF_MINUS_V8_3_APPLIED_CLOAD",
            "element_forces": "CALCULIX_EL_FILE_SECTION_FORCES_AT_ORIGINAL_BEAM_NODES",
            "element_stresses": "CALCULIX_EL_PRINT_INTEGRATION_POINT_STRESS_ENVELOPES",
            "element_forces_scope": "MEMBERS_ONLY",
            "shell_force_resultants_deferred": True,
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
        },
    }
    return result, {
        "case_id": case_id,
        "node_displacement_count": len(node_displacements),
        "support_reaction_count": len(node_reactions),
        "member_force_count": len(element_forces),
        "element_stress_count": len(element_stresses),
    }

def _expected_case_resultants(equivalent_nodal_loads: Mapping[str, Any], case_ids: Sequence[str]):
    out: dict[str, dict[str, float]] = {}
    for case_id in case_ids:
        total = [0.0, 0.0, 0.0]
        for vector in (equivalent_nodal_loads.get(case_id) or {}).values():
            vals = list(vector or [])
            for i in range(min(3, len(vals))):
                total[i] += float(vals[i])
        out[case_id] = {"FX": total[0], "FY": total[1], "FZ": total[2]}
    return out

def _raw_outputs(case_dir: Path) -> list[Path]:
    allowed = {".inp", ".dat", ".frd", ".sta", ".cvg", ".12d", ".out", ".txt"}
    return sorted(p for p in case_dir.iterdir() if p.is_file() and p.suffix.lower() in allowed)

def _calculix_case_deck_path(solver_package_dir: Path, case_id: str) -> Path:
    """Resolve the exact v8.3 CalculiX base-case deck.

    The v8.3 writer stores solver files under:
        solver_package/<solver>/<filename>
    so CalculiX decks live in solver_package/calculix/calculix_<case>.inp.
    No recursive/fuzzy guessing is used.
    """
    return Path(solver_package_dir) / "calculix" / f"calculix_{case_id}.inp"


def build_autonomous_calculix_results(
    *,
    repository: Path,
    project_id: str,
    analytical_model: Mapping[str, Any],
    action_load_model: Mapping[str, Any],
    solver_package_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    repository = Path(repository).resolve()
    solver_package_dir = Path(solver_package_dir).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    register_path = output_dir / "autonomous_calculix_execution_register.json"
    results_path = output_dir / "autonomous_structural_analysis_results.json"
    evidence_root = output_dir / "solver_evidence" / "calculix"
    register: dict[str, Any] = {
        "schema_version": "phoenix.autonomous-calculix-execution-register/1.0",
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": project_id,
        "status": "BLOCKED",
        "solver": "calculix",
        "real_solver_execution_required": True,
        "raw_solver_evidence_required": True,
        "automatic_code_compliance_claim": False,
        "automatic_structural_approval": False,
        "professional_structural_review_required": True,
        "production_release": "LOCKED",
        "cases": [],
        "blockers": [],
    }
    try:
        executable, discovery = detect_calculix_executable()
        register["executable_discovery"] = discovery
        if executable is None:
            raise AutonomousCalculixBlocked(
                "CALCULIX_EXECUTABLE_REQUIRED",
                "CalculiX executable niet gevonden; Phoenix genereert geen fictieve solverresultaten.",
            )
        register["executable"] = str(executable)
        register["version_probe"] = calculix_version(executable)

        manifest_path = solver_package_dir / "PHOENIX_SOLVER_PACKAGE_MANIFEST_v8_3_0.json"
        if not manifest_path.is_file():
            raise AutonomousCalculixBlocked(
                "V8_3_SOLVER_PACKAGE_MANIFEST_REQUIRED",
                "v8.3 solvermanifest ontbreekt.",
                {"expected": str(manifest_path)},
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mapping = _mapping_from_manifest(manifest)
        equivalent_loads = dict(manifest.get("equivalent_nodal_loads_kN") or {})
        nodes, members, shells = _known_model(analytical_model)
        support_ids = _support_node_ids(analytical_model, nodes)
        node_tags = {str(k): int(v) for k, v in (mapping.get("node_tags") or {}).items()}
        missing_support_tags = [nid for nid in support_ids if nid not in node_tags]
        if missing_support_tags:
            raise AutonomousCalculixBlocked(
                "CALCULIX_SUPPORT_MAPPING_INCOMPLETE",
                "Supportnodes ontbreken in de v8.3 CalculiX mapping.",
                {"missing_node_ids": missing_support_tags},
            )
        support_tags = [node_tags[nid] for nid in support_ids]
        element_ids = list(members) + list(shells)
        case_ids = _load_case_ids(action_load_model)

        normalized: list[dict[str, Any]] = []
        for case_id in case_ids:
            source_deck = _calculix_case_deck_path(solver_package_dir, case_id)
            if not source_deck.is_file():
                raise AutonomousCalculixBlocked(
                    "CALCULIX_BASE_CASE_DECK_REQUIRED",
                    f"CalculiX basisdeck ontbreekt voor load case {case_id}.",
                    {
                        "expected": str(source_deck),
                        "v8_3_solver_layout": "solver_package/calculix/calculix_<case_id>.inp",
                    },
                )
            case_dir = evidence_root / _safe_case_token(case_id)
            case_dir.mkdir(parents=True, exist_ok=True)
            original_copy = case_dir / "v8_3_original.inp"
            shutil.copy2(source_deck, original_copy)
            instrumented = _instrument_deck(
                source_deck.read_text(encoding="utf-8"),
                support_tags=support_tags,
                element_ids=element_ids,
            )
            job = "phoenix_v8_4_case"
            deck = case_dir / f"{job}.inp"
            deck.write_text(instrumented, encoding="utf-8", newline="\n")
            proc = subprocess.run(
                [str(executable), "-i", job],
                cwd=str(case_dir),
                text=True,
                capture_output=True,
                timeout=300,
                check=False,
            )
            (case_dir / "solver_stdout.txt").write_text(proc.stdout or "", encoding="utf-8", newline="\n")
            (case_dir / "solver_stderr.txt").write_text(proc.stderr or "", encoding="utf-8", newline="\n")
            if proc.returncode != 0:
                raise AutonomousCalculixBlocked(
                    "CALCULIX_SOLVER_EXECUTION_FAILED",
                    f"CalculiX stopte met exitcode {proc.returncode} voor load case {case_id}.",
                    {"case_id": case_id, "return_code": int(proc.returncode), "evidence_dir": _repo_ref(case_dir, repository)},
                )
            dat_path = case_dir / f"{job}.dat"
            frd_path = case_dir / f"{job}.frd"
            if not dat_path.is_file() or not frd_path.is_file():
                raise AutonomousCalculixBlocked(
                    "CALCULIX_RAW_RESULT_FILES_REQUIRED",
                    f"CalculiX leverde niet alle vereiste raw-resultaatbestanden voor {case_id}.",
                    {"case_id": case_id, "dat_exists": dat_path.is_file(), "frd_exists": frd_path.is_file()},
                )
            evidence_manifest_path = case_dir / "raw_solver_evidence_manifest.json"
            evidence_files = _raw_outputs(case_dir)
            _write_json(evidence_manifest_path, {
                "schema_version": "phoenix.calculix-raw-solver-evidence/1.0",
                "project_id": project_id,
                "case_id": case_id,
                "solver": "calculix",
                "solver_executable": str(executable),
                "solver_version": (register.get("version_probe") or {}).get("version"),
                "return_code": int(proc.returncode),
                "files": [
                    {"path": _repo_ref(p, repository), "sha256": _sha256(p), "bytes": p.stat().st_size}
                    for p in evidence_files
                ],
            })
            result, diag = _normalize_case(
                case_id=case_id,
                dat_text=dat_path.read_text(encoding="utf-8", errors="replace"),
                frd_text=frd_path.read_text(encoding="utf-8", errors="replace"),
                analytical_model=analytical_model,
                mapping=mapping,
                equivalent_nodal_loads=equivalent_loads,
                raw_reference=_repo_ref(evidence_manifest_path, repository),
            )
            normalized.append(result)
            diag["raw_evidence"] = _repo_ref(evidence_manifest_path, repository)
            register["cases"].append(diag)

        structural_results = {
            "analysis_result_sets": normalized,
            "validation_policy": {
                "required_solvers": ["calculix"],
                "required_result_fields": list(REQUIRED_FIELDS),
                "expected_units": {"length": "m", "force": "kN", "stress": "kN/m2", "rotation": "rad"},
                "require_raw_solver_evidence": True,
                "require_converged_status": True,
                "require_known_entity_ids": True,
                "require_all_load_cases_per_solver": True,
                "cross_solver_comparison_enabled": False,
            },
            "expected_case_resultants_kN": _expected_case_resultants(equivalent_loads, case_ids),
        }
        _write_json(results_path, {
            "schema_version": "phoenix.autonomous-structural-analysis-results/1.0",
            "project_id": project_id,
            "source_engine": ENGINE_ID,
            "structural_analysis_results": structural_results,
            "provenance": {
                "v8_3_solver_manifest": _repo_ref(manifest_path, repository),
                "solver": "calculix",
                "raw_solver_evidence_required": True,
                "normalization_version": RESULT_NORMALIZATION_VERSION,
                "member_section_force_source": "CALCULIX_SECTION_FORCES",
                "shell_force_resultants_normalized": False,
                "shell_stresses_normalized": True,
            },
            "release": {
                "automatic_code_compliance_claim": False,
                "automatic_structural_approval": False,
                "professional_structural_review_required": True,
                "production_release": "LOCKED",
            },
        })
        register["status"] = "PASSED"
        register["analysis_result_set_count"] = len(normalized)
        register["load_case_count"] = len(case_ids)
        register["results_artifact"] = _repo_ref(results_path, repository)
        _write_json(register_path, register)
        return {
            "status": "PASSED",
            "structural_analysis_results": structural_results,
            "register": register,
            "artifacts": [_repo_ref(register_path, repository), _repo_ref(results_path, repository)],
            "blockers": [],
        }
    except AutonomousCalculixBlocked as exc:
        blocker = {"reason": exc.reason, "message": exc.message, **exc.details}
        register["blockers"] = [blocker]
        _write_json(register_path, register)
        return {
            "status": "BLOCKED",
            "structural_analysis_results": None,
            "register": register,
            "artifacts": [_repo_ref(register_path, repository)],
            "blockers": [blocker],
        }
    except Exception as exc:
        blocker = {
            "reason": "CALCULIX_AUTONOMOUS_EXECUTION_INTERNAL_ERROR",
            "message": f"Autonome CalculiX-verwerking stopte fail-safe: {type(exc).__name__}: {exc}",
        }
        register["blockers"] = [blocker]
        _write_json(register_path, register)
        return {
            "status": "BLOCKED",
            "structural_analysis_results": None,
            "register": register,
            "artifacts": [_repo_ref(register_path, repository)],
            "blockers": [blocker],
        }

def _synthetic_dat() -> str:
    return """
 displacements (vx,vy,vz) for set NALL and time  0.1000000E+01
 1  0.0  0.0  0.0
 2  1.0E-6  0.0  0.0

 forces (fx,fy,fz) for set PHX_SUPPORT_NODES and time  0.1000000E+01
 1 -1.0 0.0 0.0

 stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set E_M1 and time  0.1000000E+01
 1 1 100.0 0.0 0.0 0.0 0.0 0.0
 1 2 100.0 0.0 0.0 0.0 0.0 0.0
"""

def _synthetic_frd() -> str:
    # Mirrors real CalculiX ASCII FRD fixed-width records: the node number can be
    # immediately followed by the sign of the first value.
    return """
  100CL  101 0.100000E+01        2                     3    1           0
 -4  STRESS        6    1
 -5  SXX          1    4    1    1
 -5  SYY          1    4    2    2
 -5  SZZ          1    4    3    3
 -5  SXY          1    4    1    2
 -5  SYZ          1    4    2    3
 -5  SZX          1    4    3    1
 -1 1-9.99960E+01-1.40890E-09 4.12410E-09 6.08867E-09 1.21916E-06-9.94503E+04
 -1 2-9.99960E+01 3.88248E-10 1.65976E-10-2.64903E-09 4.54694E-09-5.49032E+02
 -3
"""

def self_test() -> None:
    parsed = parse_calculix_dat(_synthetic_dat())
    assert parsed["node_displacements"][2][0] == 1.0e-6
    assert parsed["support_total_forces"][1][0] == -1.0
    assert len(parsed["stresses_by_set"]["E_M1"]) == 2
    frd = parse_calculix_frd_last_stress(_synthetic_frd())
    assert frd[1]["SXX"] == -99.996
    assert "SXZ" in frd[1] and "SZX" not in frd[1]
    assert len(_section_force_components(frd[1])) == 6
    deck = "*HEADING\n*NODE\n1,0,0,0\n2,1,0,0\n*NSET,NSET=NALL\n1,2\n*STEP\n*STATIC\n*END STEP\n"
    inst = _instrument_deck(deck, support_tags=[1], element_ids=["M1"])
    assert "*NSET, NSET=PHX_SUPPORT_NODES" in inst
    assert "*EL PRINT, ELSET=E_M1" in inst
    assert "*EL FILE, SECTION FORCES" in inst
    print("PHOENIX v8.4 AUTONOMOUS CALCULIX SYNTHETIC SELF-TEST: PASSED")

def real_smoke() -> None:
    executable, _ = detect_calculix_executable()
    if executable is None:
        print("PHOENIX v8.4 REAL CALCULIX SMOKE: SKIPPED (ccx not installed)")
        return
    version = calculix_version(executable)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        job = "phx_v84_smoke"
        deck = d / f"{job}.inp"
        deck.write_text("""*HEADING
PHOENIX v8.4 REAL CALCULIX SMOKE
*NODE
1,0,0,0
2,1,0,0
*ELEMENT,TYPE=B31,ELSET=E_M1
1,1,2
*NSET,NSET=NALL
1,2
*NSET,NSET=PHX_SUPPORT_NODES
1
*BOUNDARY
1,1,6
*MATERIAL,NAME=MAT
*ELASTIC
210000000.,0.3
*BEAM SECTION,ELSET=E_M1,MATERIAL=MAT,SECTION=RECT
0.1,0.1
0.,1.,0.
*STEP
*STATIC
*CLOAD
2,1,1.
*NODE PRINT,NSET=NALL
U
*NODE PRINT,NSET=PHX_SUPPORT_NODES
RF
*EL PRINT,ELSET=E_M1
S
*NODE FILE,OUTPUT=2D
U
*EL FILE,SECTION FORCES
S,NOE
*END STEP
""", encoding="utf-8", newline="\n")
        proc = subprocess.run([str(executable), "-i", job], cwd=str(d), text=True, capture_output=True, timeout=120, check=False)
        if proc.returncode != 0:
            raise SystemExit(f"REAL CALCULIX SMOKE FAILED: ccx exit {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
        dat = d / f"{job}.dat"
        frd = d / f"{job}.frd"
        if not dat.is_file() or not frd.is_file():
            raise SystemExit("REAL CALCULIX SMOKE FAILED: .dat/.frd missing")
        pd = parse_calculix_dat(dat.read_text(encoding="utf-8", errors="replace"))
        pf = parse_calculix_frd_last_stress(frd.read_text(encoding="utf-8", errors="replace"))
        if 1 not in pd["node_displacements"] or 2 not in pd["node_displacements"]:
            raise SystemExit("REAL CALCULIX SMOKE FAILED: displacement parser")
        if 1 not in pd["support_total_forces"]:
            raise SystemExit("REAL CALCULIX SMOKE FAILED: support RF parser")
        if not pd["stresses_by_set"].get("E_M1"):
            raise SystemExit("REAL CALCULIX SMOKE FAILED: stress parser")
        if 1 not in pf or 2 not in pf or len(_section_force_components(pf[1])) < 6:
            raise SystemExit("REAL CALCULIX SMOKE FAILED: section-force FRD parser")
        print(f"PHOENIX v8.4 REAL CALCULIX SMOKE: PASSED / VERSION {version.get('version') or 'UNKNOWN'}")
        print(f"CALCULIX EXECUTABLE: {executable}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--real-smoke", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.real_smoke:
        real_smoke()
        return 0
    parser.error("Use --self-test or --real-smoke")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
