"""Project Phoenix v8.3 autonomous solver-basis and element-assignment engine.

This module creates an analysis-only, reference-grounded solver basis for the
v8.3 linear-elastic solver package. It does not claim code compliance,
certification, product verification, professional approval, or construction
release.

Design rules:
- Project facts win over reference assumptions.
- Supplier catalog/range data may never define the required design class.
- In relaxed material-certification mode, availability/certification may not
  block analysis if a traceable analysis material model exists.
- Missing properties that are required by the solver are explicit blockers.
- Production/for-construction release remains locked.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
import hashlib
import json
import math
import os

ENGINE_ID = "PHX-STRUCT-AUTONOMOUS-SOLVER-BASIS-V8.3"
ENGINE_VERSION = "1.0.0"
RELAXED_MODE = "UNCERTIFIED_DESIGN_ASSUMPTION_ALLOWED"
REFERENCE_CONFIG = "configs/phoenix/structural_solver_reference_basis_v1_0.json"
LOCKED_RELEASE = "LOCKED"
DOFS = ("UX", "UY", "UZ", "RX", "RY", "RZ")


@dataclass(frozen=True)
class BuildResult:
    status: str
    structural_analysis_basis: Dict[str, Any]
    register: Dict[str, Any]
    blockers: List[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "structural_analysis_basis": self.structural_analysis_basis,
            "register": self.register,
            "blockers": self.blockers,
        }


def _items(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        result = float(value)
        if not math.isfinite(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def _positive(value: Any) -> Optional[float]:
    result = _num(value)
    return result if result is not None and result > 0.0 else None


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def _reference_config(repository: Path) -> Dict[str, Any]:
    data = _read_json(repository / REFERENCE_CONFIG)
    if not data:
        raise ValueError(f"Reference solver-basis configuration missing: {REFERENCE_CONFIG}")
    return data


def _is_relaxed_mode(material_selection: Optional[Mapping[str, Any]] = None, candidates: Optional[Sequence[Any]] = None) -> bool:
    if os.environ.get("PHOENIX_MATERIAL_CERTIFICATION_MODE", "").strip().upper() == RELAXED_MODE:
        return True
    selection_mode = str((material_selection or {}).get("material_certification_mode") or "").strip().upper()
    if selection_mode == RELAXED_MODE:
        return True

    def contains_mode(value: Any, depth: int = 0) -> bool:
        if depth > 6:
            return False
        if isinstance(value, str):
            return value.strip().upper() == RELAXED_MODE
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key).strip().upper() == "PHOENIX_MATERIAL_CERTIFICATION_MODE" and str(item).strip().upper() == RELAXED_MODE:
                    return True
                if contains_mode(item, depth + 1):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(contains_mode(item, depth + 1) for item in value)
        return False

    return contains_mode(candidates or [])


def _distance(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    ax, ay, az = (_num(a.get(k)) for k in ("x", "y", "z"))
    bx, by, bz = (_num(b.get(k)) for k in ("x", "y", "z"))
    if None in (ax, ay, az, bx, by, bz):
        raise ValueError("Analytical node coordinates must be numeric for autonomous sizing")
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)


def _round_up(value: float, increment: float) -> float:
    if increment <= 0:
        return value
    return math.ceil((value - 1e-12) / increment) * increment


def _node_map(model: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for raw in _items(model.get("nodes")):
        if not isinstance(raw, dict):
            continue
        node_id = str(raw.get("id") or "").strip()
        if node_id:
            result[node_id] = raw
    return result


def _candidate_family(element: Mapping[str, Any]) -> str:
    value = str(element.get("material_candidate") or element.get("material_family") or "").strip().lower()
    aliases = {
        "reinforced_concrete_candidate": "reinforced_concrete",
        "structural_concrete": "reinforced_concrete",
        "concrete": "reinforced_concrete",
        "masonry_candidate": "masonry",
        "masonry_unit": "masonry",
        "structural_timber": "timber",
        "timber_candidate": "timber",
        "structural_steel": "structural_steel",
        "steel_candidate": "structural_steel",
    }
    return aliases.get(value, value)


def _selected_product_material(
    material_selection: Mapping[str, Any],
    family: str,
) -> Optional[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    """Return a solver material only when product evidence contains all solver fields.

    Supplier descriptions, price text, capability ranges and certification labels are
    deliberately ignored as numerical design-property sources.
    """
    family_aliases = {
        "reinforced_concrete": {"structural_concrete", "reinforced_concrete"},
        "masonry": {"masonry_unit", "masonry"},
        "timber": {"structural_timber", "timber"},
        "structural_steel": {"structural_steel", "steel"},
    }
    valid_families = family_aliases.get(family, {family})
    for selection in _items(material_selection.get("selections")):
        if not isinstance(selection, dict):
            continue
        if str(selection.get("material_family") or "").strip().lower() not in valid_families:
            continue
        product = selection.get("selected_product") or {}
        if not isinstance(product, dict):
            continue
        props = product.get("technical_properties") or {}
        if not isinstance(props, dict):
            continue
        e = _positive(props.get("elastic_modulus_kN_m2"))
        nu = _num(props.get("poisson_ratio"))
        rho = _positive(props.get("density_kg_m3"))
        if e is None or nu is None or rho is None or not (-1.0 < nu < 0.5):
            continue
        material_id = str(product.get("engineering_material_id") or product.get("product_id") or "").strip()
        if not material_id:
            continue
        solver = {
            "elastic_modulus_kN_m2": e,
            "poisson_ratio": nu,
            "density_kg_m3": rho,
            "source_kind": "PROJECT_PRODUCT_TECHNICAL_EVIDENCE",
            "source_product_id": product.get("product_id"),
            "certification_status": selection.get("engineering_qualification_status"),
            "analysis_only": True,
            "code_compliance_claimed": False,
        }
        return material_id, solver, selection
    return None


def _reference_material(
    config: Mapping[str, Any],
    family: str,
) -> Optional[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    raw = (config.get("reference_materials") or {}).get(family)
    if not isinstance(raw, dict):
        return None
    material_id = str(raw.get("material_id") or "").strip()
    e = _positive(raw.get("elastic_modulus_kN_m2"))
    nu = _num(raw.get("poisson_ratio"))
    rho = _positive(raw.get("density_kg_m3"))
    if not material_id or e is None or nu is None or rho is None or not (-1.0 < nu < 0.5):
        return None
    solver = {
        "elastic_modulus_kN_m2": e,
        "poisson_ratio": nu,
        "density_kg_m3": rho,
        "analysis_reference_class": raw.get("analysis_reference_class"),
        "required_design_class": None,
        "source_kind": "REFERENCE_GROUNDED_CONCEPT_ASSUMPTION",
        "source_references": deepcopy(raw.get("source_references") or []),
        "review_required": True,
        "analysis_only": True,
        "product_properties_verified": False,
        "code_compliance_claimed": False,
    }
    return material_id, solver, raw


def _resolve_material(
    *,
    family: str,
    config: Mapping[str, Any],
    material_selection: Mapping[str, Any],
    relaxed: bool,
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Dict[str, Any]]:
    selected = _selected_product_material(material_selection, family)
    if selected is not None:
        material_id, solver, selection = selected
        return material_id, solver, {
            "family": family,
            "resolution": "PROJECT_PRODUCT_TECHNICAL_EVIDENCE",
            "material_id": material_id,
            "selection_status": selection.get("selection_status"),
        }

    if not relaxed:
        return None, None, {
            "family": family,
            "resolution": "STRICT_MODE_REQUIRES_ENGINEERING_QUALIFIED_PRODUCT_PROPERTIES",
        }

    reference = _reference_material(config, family)
    if reference is not None:
        material_id, solver, raw = reference
        return material_id, solver, {
            "family": family,
            "resolution": "REFERENCE_GROUNDED_ANALYSIS_ASSUMPTION",
            "material_id": material_id,
            "analysis_reference_class": raw.get("analysis_reference_class"),
            "required_design_class": None,
            "review_required": True,
        }

    return None, None, {
        "family": family,
        "resolution": "SOLVER_MATERIAL_PROPERTIES_UNRESOLVED",
    }


def _load_profile(workspace: Path) -> Dict[str, Any]:
    candidates = [
        workspace / "results" / "session_adapters" / "architecture" / "structural_project_profile.json",
        workspace / "results" / "session_adapters" / "architecture" / "project_structural_profile.json",
    ]
    for path in candidates:
        data = _read_json(path)
        if data:
            return data
    return {}


def _wall_thickness_from_profile(profile: Mapping[str, Any]) -> Optional[float]:
    assumptions = profile.get("assumptions") or {}
    if isinstance(assumptions, dict):
        value = _positive(assumptions.get("minimum_loadbearing_wall_thickness_m"))
        if value is not None:
            return value
    for item in _items(profile.get("assumption_register")):
        if isinstance(item, dict) and item.get("id") == "minimum_loadbearing_wall_thickness_m":
            value = _positive(item.get("value"))
            if value is not None:
                return value
    return None


def _member_role(element: Mapping[str, Any], nodes: Mapping[str, Any]) -> str:
    explicit = str(element.get("type") or "").strip().lower()
    candidate = str(element.get("section_candidate") or "").strip().upper()
    if "column" in explicit or "COLUMN" in candidate:
        return "column"
    if "beam" in explicit or "BEAM" in candidate:
        return "beam"
    ni, nj = str(element.get("node_i") or ""), str(element.get("node_j") or "")
    if ni in nodes and nj in nodes:
        a, b = nodes[ni], nodes[nj]
        dz = abs((_num(a.get("z")) or 0.0) - (_num(b.get("z")) or 0.0))
        length = _distance(a, b)
        if length > 0 and dz / length >= 0.85:
            return "column"
        return "beam"
    return "unresolved"


def _member_section(
    element: Mapping[str, Any],
    nodes: Mapping[str, Any],
    config: Mapping[str, Any],
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Dict[str, Any]]:
    role = _member_role(element, nodes)
    rules = config.get("preliminary_section_rules") or {}
    if role == "column":
        width = _positive((rules.get("column") or {}).get("default_square_width_m"))
        if width is None:
            return None, None, {"resolution": "COLUMN_REFERENCE_SIZE_REQUIRED"}
        section_id = f"SEC-COLUMN-{int(round(width*1000))}x{int(round(width*1000))}-REF"
        return section_id, {
            "type": "rectangular_beam",
            "width_m": width,
            "height_m": width,
            "source_kind": "REFERENCE_GROUNDED_PRELIMINARY_SIZING",
            "review_required": True,
        }, {"role": role, "rule": "REFERENCE_DEFAULT_COLUMN"}

    if role == "beam":
        ni, nj = str(element.get("node_i") or ""), str(element.get("node_j") or "")
        if ni not in nodes or nj not in nodes:
            return None, None, {"resolution": "BEAM_GEOMETRY_REQUIRED"}
        span = _distance(nodes[ni], nodes[nj])
        beam_rules = rules.get("beam") or {}
        ratio = _positive(beam_rules.get("height_span_ratio")) or 0.10
        min_h = _positive(beam_rules.get("minimum_height_m")) or 0.30
        max_h = _positive(beam_rules.get("maximum_height_m")) or 0.80
        min_b = _positive(beam_rules.get("minimum_width_m")) or 0.25
        width_ratio = _positive(beam_rules.get("width_height_ratio")) or 0.45
        increment = _positive(beam_rules.get("rounding_increment_m")) or 0.05
        h = min(max_h, max(min_h, _round_up(span * ratio, increment)))
        b = max(min_b, _round_up(h * width_ratio, increment))
        section_id = f"SEC-BEAM-{int(round(b*1000))}x{int(round(h*1000))}-REF"
        return section_id, {
            "type": "rectangular_beam",
            "width_m": b,
            "height_m": h,
            "source_kind": "REFERENCE_GROUNDED_PRELIMINARY_SIZING",
            "source_span_m": span,
            "review_required": True,
        }, {"role": role, "rule": "SPAN_BASED_REFERENCE_SIZING", "span_m": span}

    return None, None, {"resolution": "MEMBER_ROLE_UNRESOLVED"}


def _shell_span(element: Mapping[str, Any], nodes: Mapping[str, Any]) -> Optional[float]:
    ids = [str(v) for v in _items(element.get("node_ids"))]
    if len(ids) < 3 or any(v not in nodes for v in ids):
        return None
    edge_lengths: List[float] = []
    for idx, node_id in enumerate(ids):
        edge_lengths.append(_distance(nodes[node_id], nodes[ids[(idx + 1) % len(ids)] ]))
    return max(edge_lengths) if edge_lengths else None


def _shell_section(
    element: Mapping[str, Any],
    nodes: Mapping[str, Any],
    config: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Dict[str, Any]]:
    shell_type = str(element.get("type") or "").strip().lower()
    raw_candidate = _positive(element.get("thickness_candidate"))
    if raw_candidate is not None:
        t = raw_candidate
        source = "PROJECT_ANALYTICAL_MODEL_EXPLICIT_THICKNESS"
    elif "wall" in shell_type:
        t = _wall_thickness_from_profile(profile)
        if t is None:
            return None, None, {"resolution": "LOADBEARING_WALL_THICKNESS_REQUIRED"}
        source = "PROJECT_PROFILE_MINIMUM_LOADBEARING_WALL_THICKNESS"
    elif "slab" in shell_type:
        span = _shell_span(element, nodes)
        if span is None:
            return None, None, {"resolution": "SLAB_GEOMETRY_REQUIRED"}
        slab_rules = (config.get("preliminary_section_rules") or {}).get("slab") or {}
        factor = _positive(slab_rules.get("thickness_span_factor")) or 0.035
        min_t = _positive(slab_rules.get("minimum_thickness_m")) or 0.16
        max_t = _positive(slab_rules.get("maximum_thickness_m")) or 0.35
        increment = _positive(slab_rules.get("rounding_increment_m")) or 0.01
        t = min(max_t, max(min_t, _round_up(span * factor, increment)))
        source = "SPAN_BASED_REFERENCE_PRELIMINARY_SIZING"
    else:
        return None, None, {"resolution": "SHELL_ROLE_UNRESOLVED"}

    section_id = f"SEC-SHELL-{int(round(t*1000))}-REF"
    return section_id, {
        "type": "shell",
        "thickness_m": t,
        "source_kind": source,
        "review_required": True,
    }, {"role": shell_type or "shell", "rule": source, "thickness_m": t}


def _element_candidate_view(model: Mapping[str, Any], raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Return an element view enriched from v8.1 top-level candidate maps.

    v8.1 historically stores some candidate assignments both as element-local fields
    and as top-level ``material_candidates`` / ``section_candidates`` maps.  v8.3 must
    consume both representations without mutating the original analytical artifact.
    Element-local fields always win.
    """
    element = dict(raw)
    element_id = str(element.get("id") or "").strip()
    if not element_id:
        return element

    candidate_maps = (
        ("material_candidate", "material_candidates"),
        ("section_candidate", "section_candidates"),
        ("thickness_candidate", "thickness_candidates"),
    )
    for field, map_name in candidate_maps:
        current = element.get(field)
        if current not in (None, ""):
            continue
        mapping = model.get(map_name) or {}
        if isinstance(mapping, Mapping) and element_id in mapping:
            element[field] = mapping[element_id]

    return element


def _all_elements(model: Mapping[str, Any]) -> Iterable[Tuple[str, Dict[str, Any], str]]:
    for raw in _items(model.get("members")):
        if isinstance(raw, dict) and raw.get("id"):
            element = _element_candidate_view(model, raw)
            yield str(element["id"]), element, "member"
    for raw in _items(model.get("shells")):
        if isinstance(raw, dict) and raw.get("id"):
            element = _element_candidate_view(model, raw)
            yield str(element["id"]), element, "shell"


def build_autonomous_solver_basis(
    *,
    repository: Path,
    workspace: Path,
    project_id: str,
    analytical_model: Mapping[str, Any],
    action_load_model: Mapping[str, Any],
    material_selection: Optional[Mapping[str, Any]] = None,
    candidates: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    repository = Path(repository)
    workspace = Path(workspace)
    config = _reference_config(repository)
    material_selection = material_selection or {}
    relaxed = _is_relaxed_mode(material_selection, candidates)
    nodes = _node_map(analytical_model)
    profile = _load_profile(workspace)

    blockers: List[Dict[str, Any]] = []
    warnings: List[str] = []
    materials: Dict[str, Dict[str, Any]] = {}
    sections: Dict[str, Dict[str, Any]] = {}
    by_id: Dict[str, Dict[str, str]] = {}
    material_resolution: Dict[str, Any] = {}
    section_resolution: Dict[str, Any] = {}

    elements = list(_all_elements(analytical_model))
    if not nodes or not elements:
        blockers.append({
            "reason": "STRUCTURAL_ANALYTICAL_MODEL_REQUIRED_FOR_AUTONOMOUS_SOLVER_BASIS",
            "message": "v8.3 autonomous solver basis requires analytical nodes and elements from v8.1.",
        })

    families = sorted({_candidate_family(e) for _, e, _ in elements if _candidate_family(e)})
    for family in families:
        material_id, material, trace = _resolve_material(
            family=family,
            config=config,
            material_selection=material_selection,
            relaxed=relaxed,
        )
        material_resolution[family] = trace
        if material_id is None or material is None:
            blockers.append({
                "reason": "STRUCTURAL_SOLVER_REFERENCE_MATERIAL_PROPERTIES_REQUIRED",
                "message": (
                    f"No traceable solver material model is available for material family '{family}'. "
                    "Phoenix will not invent elastic modulus, Poisson ratio, or density."
                ),
                "material_family": family,
            })
        else:
            materials[material_id] = material

    family_to_material = {
        family: trace.get("material_id")
        for family, trace in material_resolution.items()
        if trace.get("material_id")
    }

    for element_id, element, element_kind in elements:
        family = _candidate_family(element)
        material_id = family_to_material.get(family)
        if material_id is None:
            continue
        if element_kind == "member":
            section_id, section, trace = _member_section(element, nodes, config)
        else:
            section_id, section, trace = _shell_section(element, nodes, config, profile)
        section_resolution[element_id] = trace
        if section_id is None or section is None:
            blockers.append({
                "reason": "STRUCTURAL_SOLVER_SECTION_BASIS_REQUIRED",
                "message": f"No traceable preliminary solver section could be derived for element {element_id}.",
                "element_id": element_id,
                "element_type": element.get("type"),
            })
            continue
        # v8.3 OpenSees shell sections bind material properties at section creation.
        # Therefore a geometric section id may never be shared by different material
        # families even when the thickness/size is identical.
        family_token = "".join(ch if ch.isalnum() else "-" for ch in family.upper()).strip("-") or "MATERIAL"
        section_id = f"{section_id}-{family_token}"
        sections.setdefault(section_id, section)
        by_id[element_id] = {"material_id": material_id, "section_id": section_id}

    missing_assignment_ids = sorted(element_id for element_id, _, _ in elements if element_id not in by_id)
    if missing_assignment_ids:
        blockers.append({
            "reason": "STRUCTURAL_SOLVER_ELEMENT_ASSIGNMENTS_INCOMPLETE",
            "message": "Not all analytical elements received traceable material and section assignments.",
            "missing_element_ids": missing_assignment_ids[:100],
        })

    if not _items(action_load_model.get("load_cases")):
        warnings.append("v8.2 action/load model contains no load_cases; v8.3 may generate an empty load-case package.")

    structural_analysis_basis = {
        "solver_basis": {
            "basis": "AUTONOMOUS_REFERENCE_GROUNDED_CONCEPT_ANALYSIS_V1_0",
            "analysis_type": "LINEAR_STATIC",
            "gravity_acceleration_m_s2": 9.81,
            "materials": materials,
            "sections": sections,
            "automatic_normative_value_invention": False,
            "capacity_strength_properties_used": False,
            "analysis_material_properties_scope": "ELASTIC_MODULUS_POISSON_DENSITY_ONLY",
            "supplier_capability_may_define_design_class": False,
            "required_design_class_status": "REMAINS_SEPARATE_FROM_ANALYSIS_REFERENCE_PROPERTIES",
            "professional_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
        "element_assignments": {"by_id": by_id, "by_type": {}},
        "solver_adapters": ["opensees", "calculix"],
        "execution_policy": {
            "allow_execution": False,
            "require_explicit_cli_opt_in": True,
            "solver_executables": {"opensees": "OpenSees", "calculix": "ccx"},
            "automatic_solver_execution": False,
            "automatic_professional_approval": False,
        },
    }

    status = "PASSED" if not blockers else "BLOCKED_INPUT"
    register = {
        "schema_version": "phoenix.autonomous-solver-basis-register/1.0",
        "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION},
        "project_id": project_id,
        "status": status,
        "material_certification_mode": RELAXED_MODE if relaxed else "CERTIFIED_STRICT",
        "analysis_scope": "LINEAR_ELASTIC_CONCEPT_ANALYSIS",
        "capacity_strength_properties_used": False,
        "analytical_model_sha256": _fingerprint(analytical_model),
        "action_load_model_sha256": _fingerprint(action_load_model),
        "project_fact_precedence": True,
        "supplier_capability_may_define_design_class": False,
        "material_resolution": material_resolution,
        "section_resolution": section_resolution,
        "element_count": len(elements),
        "assigned_element_count": len(by_id),
        "material_count": len(materials),
        "section_count": len(sections),
        "support_policy": "PROVISIONAL_FIXED_BASE_CANDIDATES_MAY_BE_CARRIED_TO_SOLVER_AS_REVIEW_REQUIRED_BOUNDARY_CONDITION",
        "warnings": warnings,
        "blockers": blockers,
        "release": {
            "solver_basis_release": "CANDIDATE_ONLY",
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "professional_structural_review_required": True,
            "production_release": LOCKED_RELEASE,
        },
    }
    return BuildResult(status, structural_analysis_basis, register, blockers).as_dict()


def apply_solver_basis_to_analytical_model(
    analytical_model: Mapping[str, Any],
    solver_input: Mapping[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Apply autonomous by-id assignments without mutating the v8.1 artifact."""
    model = deepcopy(dict(analytical_model))
    assignments = solver_input.get("element_assignments") or {}
    by_id = assignments.get("by_id") or {}
    by_type = assignments.get("by_type") or {}
    missing: List[str] = []

    def resolve(element: MutableMapping[str, Any]) -> None:
        element_id = str(element.get("id") or "")
        element_type = str(element.get("type") or "")
        assignment = by_id.get(element_id)
        if not isinstance(assignment, dict):
            assignment = by_type.get(element_type)
        if isinstance(assignment, dict):
            if assignment.get("material_id"):
                element["material_id"] = str(assignment["material_id"])
            if assignment.get("section_id"):
                element["section_id"] = str(assignment["section_id"])
        if not element.get("material_id") or not element.get("section_id"):
            missing.append(element_id)

    for key in ("members", "shells"):
        values = model.get(key)
        if not isinstance(values, list):
            continue
        for raw in values:
            if isinstance(raw, dict):
                resolve(raw)

    return model, sorted(v for v in missing if v)


def normalize_support_candidates_for_solver(analytical_model: Mapping[str, Any]) -> Dict[str, Any]:
    """Carry explicit v8.1 PROVISIONAL_FIXED_BASE candidates into a review-required solver BC.

    No new support location is invented. Only nodes already marked by v8.1 as
    PROVISIONAL_FIXED_BASE are converted. Existing explicit supports/dofs win.
    """
    model = deepcopy(dict(analytical_model))
    existing = model.get("supports")
    if isinstance(existing, list) and existing:
        return model
    normalized: List[Dict[str, Any]] = []
    for raw in _items(model.get("support_candidates")):
        if not isinstance(raw, dict):
            continue
        if str(raw.get("type") or "").strip().upper() != "PROVISIONAL_FIXED_BASE":
            continue
        node_id = str(raw.get("node_id") or "").strip()
        if not node_id:
            continue
        normalized.append({
            "id": str(raw.get("id") or f"SUP-{node_id}"),
            "node_id": node_id,
            "dofs": list(DOFS),
            "source_candidate_id": raw.get("source_candidate_id"),
            "source_support_type": "PROVISIONAL_FIXED_BASE",
            "solver_boundary_condition_basis": "V8_1_PROVISIONAL_FIXED_BASE_CANDIDATE",
            "approval_state": "CANDIDATE_ONLY",
            "review_required": True,
        })
    if normalized:
        model["supports"] = normalized
    return model


__all__ = [
    "build_autonomous_solver_basis",
    "apply_solver_basis_to_analytical_model",
    "normalize_support_candidates_for_solver",
]
