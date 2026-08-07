"""Project Phoenix R8 â€” Autonomous reinforced-concrete design candidate engine.

Engineering-candidate generator only; never a code-compliance certifier.

Consumes:
- explicit analytical geometry / solver basis;
- real v8.4 synthesized CalculiX combinations;
- an explicit R8 RC policy.

Produces:
- preliminary longitudinal/shear reinforcement candidates;
- screening N/M/V and elastic buckling resistances;
- traceable v8.5 verification input;
- locked release gates.
"""

from __future__ import annotations

from copy import deepcopy
from math import pi, sqrt
from typing import Any, Mapping, Sequence


ENGINE_ID = "PHX-AUTONOMOUS-RC-DESIGN-CANDIDATE-V8.5-R8"
VERSION = "1.0.0"


class AutonomousRCDesignBlocked(RuntimeError):
    def __init__(self, reason: str, message: str, evidence: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.evidence = dict(evidence or {})


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _positive(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise AutonomousRCDesignBlocked(
            "RC_DESIGN_POLICY_INVALID",
            f"{label} must be numeric.",
            {"field": label, "value": value},
        )
    if result <= 0:
        raise AutonomousRCDesignBlocked(
            "RC_DESIGN_POLICY_INVALID",
            f"{label} must be > 0.",
            {"field": label, "value": value},
        )
    return result


def _node_xyz(node: Mapping[str, Any]) -> tuple[float, float, float] | None:
    for keys in (("x_m", "y_m", "z_m"), ("x", "y", "z"), ("X", "Y", "Z")):
        if all(key in node for key in keys):
            try:
                return tuple(float(node[key]) for key in keys)  # type: ignore[return-value]
            except (TypeError, ValueError):
                pass

    for key in ("coordinates_m", "coordinates", "xyz", "point"):
        value = node.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            try:
                return float(value[0]), float(value[1]), float(value[2])
            except (TypeError, ValueError):
                pass
        if isinstance(value, Mapping):
            try:
                return (
                    float(value.get("x", value.get("X"))),
                    float(value.get("y", value.get("Y"))),
                    float(value.get("z", value.get("Z"))),
                )
            except (TypeError, ValueError):
                pass
    return None


def _member_length_m(
    member: Mapping[str, Any],
    nodes: Mapping[str, Mapping[str, Any]],
    section: Mapping[str, Any],
) -> float:
    direct = member.get("length_m")
    if direct is not None:
        try:
            value = float(direct)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass

    ni = nodes.get(_text(member.get("node_i")))
    nj = nodes.get(_text(member.get("node_j")))
    if ni and nj:
        ai = _node_xyz(ni)
        aj = _node_xyz(nj)
        if ai and aj:
            length = sqrt(sum((a - b) ** 2 for a, b in zip(ai, aj)))
            if length > 1e-9:
                return length

    span = section.get("source_span_m")
    if span is not None:
        try:
            value = float(span)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass

    raise AutonomousRCDesignBlocked(
        "RC_MEMBER_LENGTH_EVIDENCE_REQUIRED",
        "Memberlengte ontbreekt en kan niet uit knoopcoordinaten of section source span worden afgeleid.",
        {"member_id": _text(member.get("id")), "section_id": _text(member.get("section_id"))},
    )


def _parse_fck_mpa(material: Mapping[str, Any]) -> float:
    for key in ("fck_mpa", "characteristic_compressive_strength_mpa"):
        if material.get(key) is not None:
            try:
                value = float(material[key])
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass

    ref_class = _text(material.get("analysis_reference_class")).upper().replace(" ", "")
    if ref_class.startswith("C") and "/" in ref_class:
        try:
            value = float(ref_class[1:].split("/", 1)[0])
            if value > 0:
                return value
        except ValueError:
            pass

    raise AutonomousRCDesignBlocked(
        "RC_CONCRETE_STRENGTH_CLASS_REQUIRED",
        "Betonsterkteklasse kan niet traceerbaar uit de huidige modeldata worden afgeleid.",
        {"material": dict(material)},
    )


def _rect_section(section: Mapping[str, Any], section_id: str) -> tuple[float, float]:
    try:
        b = float(section.get("width_m"))
        h = float(section.get("height_m"))
    except (TypeError, ValueError):
        raise AutonomousRCDesignBlocked(
            "RC_RECTANGULAR_SECTION_DIMENSIONS_REQUIRED",
            "R8 vereist expliciete breedte en hoogte voor RC line members.",
            {"section_id": section_id},
        )
    if b <= 0 or h <= 0:
        raise AutonomousRCDesignBlocked(
            "RC_RECTANGULAR_SECTION_DIMENSIONS_REQUIRED",
            "RC section width/height must be positive.",
            {"section_id": section_id, "width_m": b, "height_m": h},
        )
    return b, h


def _is_column(section_id: str) -> bool:
    return "COLUMN" in section_id.upper()


def _force_container(result: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in (
        "element_forces",
        "member_forces",
        "member_section_forces",
        "element_section_forces",
    ):
        value = result.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _member_force_record(result: Mapping[str, Any], member_id: str) -> Mapping[str, Any]:
    container = _force_container(result)
    value = container.get(member_id)
    if not isinstance(value, Mapping):
        return {}
    for key in ("forces", "section_forces", "envelope", "values"):
        inner = value.get(key)
        if isinstance(inner, Mapping):
            return inner
    return value


def _force_value(record: Mapping[str, Any], component: str) -> float:
    aliases = {
        "N": ("N", "NX", "axial", "axial_force_kN"),
        "VY": ("VY", "Vy", "vy", "shear_y_kN"),
        "VZ": ("VZ", "Vz", "vz", "shear_z_kN"),
        "MY": ("MY", "My", "my", "moment_y_kNm"),
        "MZ": ("MZ", "Mz", "mz", "moment_z_kNm"),
        "T": ("T", "MX", "Mx", "torsion_kNm"),
    }
    for key in aliases[component]:
        if key in record:
            try:
                return float(record[key])
            except (TypeError, ValueError):
                pass
    return 0.0


def _combination_maps(combination_results: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
    if not isinstance(combination_results, Mapping) or not combination_results:
        raise AutonomousRCDesignBlocked(
            "RC_V8_4_COMBINATION_RESULTS_REQUIRED",
            "v8.4 synthesized_combination_results ontbreken.",
        )
    preferred = combination_results.get("calculix")
    if isinstance(preferred, Mapping) and preferred:
        return "calculix", preferred
    for solver, value in combination_results.items():
        if isinstance(value, Mapping) and value:
            return str(solver), value
    raise AutonomousRCDesignBlocked(
        "RC_V8_4_COMBINATION_RESULTS_REQUIRED",
        "Geen bruikbare solver-combinatieresultaten gevonden.",
    )


def _envelope_for_member(combos: Mapping[str, Any], member_id: str) -> dict[str, Any]:
    uls = {}
    sls = {}
    max_abs = {key: 0.0 for key in ("N", "VY", "VZ", "MY", "MZ", "T")}
    governing = {key: None for key in max_abs}
    record_found = False

    for combo_id, result in combos.items():
        if not isinstance(result, Mapping):
            continue
        record = _member_force_record(result, member_id)
        if record:
            record_found = True
        values = {key: _force_value(record, key) for key in max_abs}
        if "ULS" in str(combo_id).upper():
            uls[str(combo_id)] = values
            for component, value in values.items():
                if abs(value) > max_abs[component]:
                    max_abs[component] = abs(value)
                    governing[component] = str(combo_id)
        elif "SLS" in str(combo_id).upper():
            sls[str(combo_id)] = values

    if not record_found:
        raise AutonomousRCDesignBlocked(
            "RC_MEMBER_FORCE_RESULT_MAPPING_REQUIRED",
            "Geen member-force record gevonden in de v8.4 combinations.",
            {"member_id": member_id},
        )
    if not uls:
        raise AutonomousRCDesignBlocked(
            "RC_ULS_COMBINATION_RESULTS_REQUIRED",
            "Geen ULS-combinaties gevonden voor RC candidate design.",
            {"member_id": member_id},
        )
    return {"uls": uls, "sls": sls, "max_abs": max_abs, "governing": governing}


def _select_longitudinal_reinforcement(
    required_area_mm2: float,
    minimum_bars: int,
    bar_diameters_mm: Sequence[int],
) -> dict[str, Any]:
    candidates = []
    required = max(float(required_area_mm2), 0.0)
    for diameter in bar_diameters_mm:
        one = pi * float(diameter) ** 2 / 4.0
        for count in range(max(2, int(minimum_bars)), 21):
            provided = count * one
            if provided + 1e-9 >= required:
                candidates.append((provided, count, int(diameter), one))
                break
    if not candidates:
        raise AutonomousRCDesignBlocked(
            "RC_REINFORCEMENT_CANDIDATE_NOT_FOUND",
            "R8 kon binnen de candidate bar set geen longitudinale wapening selecteren.",
            {"required_area_mm2": required},
        )
    provided, count, diameter, one = min(candidates, key=lambda row: row[0])
    return {
        "bar_count": count,
        "bar_diameter_mm": diameter,
        "bar_area_each_mm2": one,
        "area_provided_mm2": provided,
    }


def _candidate_resistances(
    *,
    b_m: float,
    h_m: float,
    length_m: float,
    fck_mpa: float,
    policy: Mapping[str, Any],
    envelope: Mapping[str, Any],
    column: bool,
) -> dict[str, Any]:
    p = policy["candidate_parameters"]
    gamma_c = _positive(p["gamma_c"], "gamma_c")
    gamma_s = _positive(p["gamma_s"], "gamma_s")
    alpha_cc = _positive(p["alpha_cc"], "alpha_cc")
    fyk = _positive(p["reinforcement_fyk_mpa"], "reinforcement_fyk_mpa")
    cover = _positive(p["nominal_cover_mm"], "nominal_cover_mm")
    min_rho = _positive(
        p["column_min_longitudinal_ratio"] if column else p["beam_min_longitudinal_ratio"],
        "minimum longitudinal ratio",
    )
    max_rho = _positive(p["max_longitudinal_ratio"], "max_longitudinal_ratio")
    lever = _positive(p["screening_lever_arm_factor"], "screening_lever_arm_factor")
    effective_length_factor = _positive(p["column_effective_length_factor"], "column_effective_length_factor")
    concrete_e_mpa = _positive(p["screening_concrete_elastic_modulus_mpa"], "screening_concrete_elastic_modulus_mpa")

    b_mm = b_m * 1000.0
    h_mm = h_m * 1000.0
    area = b_mm * h_mm
    fcd = alpha_cc * fck_mpa / gamma_c
    fyd = fyk / gamma_s

    max_abs = envelope["max_abs"]
    med_y = float(max_abs["MY"])
    med_z = float(max_abs["MZ"])
    ned = float(max_abs["N"])

    d_y = max(h_mm - cover - 8.0, 0.55 * h_mm)
    d_z = max(b_mm - cover - 8.0, 0.55 * b_mm)
    z_y = lever * d_y
    z_z = lever * d_z

    as_y = med_y * 1.0e6 / max(fyd * z_y, 1e-9)
    as_z = med_z * 1.0e6 / max(fyd * z_z, 1e-9)
    as_n = max(0.0, ned * 1000.0 - fcd * area) / max(fyd - fcd, 1e-9)
    as_min = min_rho * area
    as_max = max_rho * area
    as_req_raw = max(as_min, as_y, as_z, as_n)
    limited = as_req_raw > as_max
    as_req = min(as_req_raw, as_max)

    reinforcement = _select_longitudinal_reinforcement(
        as_req,
        minimum_bars=4,
        bar_diameters_mm=[12, 16, 20, 25, 32],
    )
    as_provided = min(float(reinforcement["area_provided_mm2"]), as_max)
    as_effective = max(0.5 * as_provided, 1e-9)

    nrd = (fcd * max(area - as_provided, 0.0) + fyd * as_provided) / 1000.0
    mrd_y = as_effective * fyd * z_y / 1.0e6
    mrd_z = as_effective * fyd * z_z / 1.0e6

    stirrup_d = float(p["candidate_stirrup_diameter_mm"])
    stirrup_legs = int(p["candidate_stirrup_legs"])
    stirrup_spacing = float(p["candidate_stirrup_spacing_mm"])
    asw = stirrup_legs * pi * stirrup_d**2 / 4.0
    vrd_y = asw / stirrup_spacing * z_y * fyd / 1000.0
    vrd_z = asw / stirrup_spacing * z_z * fyd / 1000.0

    iy = b_mm * h_mm**3 / 12.0
    iz = h_mm * b_mm**3 / 12.0
    le = max(length_m * 1000.0 * effective_length_factor, 1.0)
    euler = pi**2 * concrete_e_mpa * min(iy, iz) / le**2 / 1000.0

    return {
        "material_design_candidate": {
            "fck_mpa": fck_mpa,
            "reinforcement_grade": p["reinforcement_grade"],
            "reinforcement_fyk_mpa": fyk,
            "gamma_c": gamma_c,
            "gamma_s": gamma_s,
            "alpha_cc": alpha_cc,
            "fcd_mpa": fcd,
            "fyd_mpa": fyd,
        },
        "reinforcement_candidate": {
            **reinforcement,
            "area_required_screening_mm2": as_req,
            "area_required_raw_screening_mm2": as_req_raw,
            "area_max_screening_mm2": as_max,
            "minimum_ratio": min_rho,
            "maximum_ratio": max_rho,
            "nominal_cover_mm": cover,
            "symmetric_candidate_layout": True,
            "reinforcement_limit_reached": limited,
            "stirrups": {
                "diameter_mm": stirrup_d,
                "legs": stirrup_legs,
                "spacing_mm": stirrup_spacing,
                "area_per_spacing_mm2": asw,
            },
        },
        "screening_resistances": {
            "N_Rd_compression_kN": nrd,
            "MY_Rd_kNm": mrd_y,
            "MZ_Rd_kNm": mrd_z,
            "VY_Rd_kN": vrd_y,
            "VZ_Rd_kN": vrd_z,
            "buckling_screening_Rd_kN": min(nrd, euler),
        },
        "screening_geometry": {
            "length_m": length_m,
            "width_m": b_m,
            "height_m": h_m,
            "slenderness_screen": length_m * 1000.0 / max(min(b_mm, h_mm), 1.0),
        },
    }


def derive_rc_design_candidate(
    *,
    project_id: str,
    analytical_model: Mapping[str, Any],
    solver_basis: Mapping[str, Any],
    combination_results: Mapping[str, Any],
    analysis_validation_state: str,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    code_basis = dict((policy or {}).get("code_basis") or {})
    for field in ("jurisdiction", "standard_set", "edition", "source_reference", "status"):
        if not _text(code_basis.get(field)):
            raise AutonomousRCDesignBlocked(
                "RC_DESIGN_POLICY_INVALID",
                f"R8 code_basis.{field} ontbreekt.",
            )
    parameter_status = _text(policy.get("numerical_parameter_status"))
    if not parameter_status:
        raise AutonomousRCDesignBlocked(
            "RC_NUMERICAL_PARAMETER_STATUS_REQUIRED",
            "R8 numerical_parameter_status ontbreekt.",
        )

    members = [m for m in _items((analytical_model or {}).get("members")) if isinstance(m, Mapping)]
    node_rows = [n for n in _items((analytical_model or {}).get("nodes")) if isinstance(n, Mapping)]
    nodes = {_text(n.get("id")): n for n in node_rows if _text(n.get("id"))}
    materials = dict((solver_basis or {}).get("materials") or {})
    sections = dict((solver_basis or {}).get("sections") or {})
    solver, combos = _combination_maps(combination_results)

    uls_ids = [str(key) for key in combos if "ULS" in str(key).upper()]
    sls_ids = [str(key) for key in combos if "SLS" in str(key).upper()]
    if not uls_ids:
        raise AutonomousRCDesignBlocked(
            "RC_ULS_COMBINATION_RESULTS_REQUIRED",
            "Geen ULS combinations gevonden.",
        )

    p = policy["candidate_parameters"]
    beam_limit_ratio = _positive(p["beam_vertical_displacement_limit_ratio"], "beam_vertical_displacement_limit_ratio")
    column_limit_ratio = _positive(p["column_displacement_limit_ratio"], "column_displacement_limit_ratio")
    slenderness_limit = _positive(p["member_slenderness_screen_limit"], "member_slenderness_screen_limit")

    candidates = []
    rules = []
    warnings = []

    for member in members:
        member_id = _text(member.get("id"))
        material_id = _text(member.get("material_id"))
        section_id = _text(member.get("section_id"))
        if "MAT-RC" not in material_id.upper() and "REINFORCED-CONCRETE" not in section_id.upper():
            continue

        material = materials.get(material_id)
        section = sections.get(section_id)
        if not isinstance(material, Mapping):
            raise AutonomousRCDesignBlocked(
                "RC_MATERIAL_BASIS_REQUIRED",
                "RC material ontbreekt in solver_basis.materials.",
                {"member_id": member_id, "material_id": material_id},
            )
        if not isinstance(section, Mapping):
            raise AutonomousRCDesignBlocked(
                "RC_SECTION_BASIS_REQUIRED",
                "RC section ontbreekt in solver_basis.sections.",
                {"member_id": member_id, "section_id": section_id},
            )

        b_m, h_m = _rect_section(section, section_id)
        length_m = _member_length_m(member, nodes, section)
        fck_mpa = _parse_fck_mpa(material)
        envelope = _envelope_for_member(combos, member_id)
        column = _is_column(section_id)

        design = _candidate_resistances(
            b_m=b_m,
            h_m=h_m,
            length_m=length_m,
            fck_mpa=fck_mpa,
            policy=policy,
            envelope=envelope,
            column=column,
        )

        candidates.append({
            "member_id": member_id,
            "material_id": material_id,
            "section_id": section_id,
            "member_role": "COLUMN" if column else "BEAM",
            "demand_envelope": deepcopy(envelope),
            **design,
            "candidate_status": "ENGINEERING_CANDIDATE_REQUIRING_REVIEW",
            "normative_parameter_status": parameter_status,
        })

        resistance = design["screening_resistances"]
        ref = f"PHOENIX_R8_RC_CANDIDATE_POLICY:{member_id}"

        for combo_id in uls_ids:
            for component, capacity_key, unit in (
                ("N_COMPRESSION", "N_Rd_compression_kN", "kN"),
                ("MY", "MY_Rd_kNm", "kNm"),
                ("MZ", "MZ_Rd_kNm", "kNm"),
                ("VY", "VY_Rd_kN", "kN"),
                ("VZ", "VZ_Rd_kN", "kN"),
            ):
                rules.append({
                    "id": f"{member_id}-{combo_id}-{component}",
                    "member_id": member_id,
                    "limit_state": "ULS",
                    "combination_id": combo_id,
                    "solver": solver,
                    "rule_type": "FORCE_CAPACITY_RATIO",
                    "demand_component": component,
                    "capacity": float(resistance[capacity_key]),
                    "unit": unit,
                    "mandatory": True,
                    "normative_reference": f"{ref}:{component}_SCREENING_RESISTANCE",
                })

            if column:
                rules.append({
                    "id": f"{member_id}-{combo_id}-NMYMZ-INTERACTION",
                    "member_id": member_id,
                    "limit_state": "ULS",
                    "combination_id": combo_id,
                    "solver": solver,
                    "rule_type": "LINEAR_INTERACTION",
                    "limit": 1.0,
                    "mandatory": True,
                    "terms": [
                        {"demand_component": "N_COMPRESSION", "capacity": float(resistance["N_Rd_compression_kN"]), "unit": "kN"},
                        {"demand_component": "MY", "capacity": float(resistance["MY_Rd_kNm"]), "unit": "kNm"},
                        {"demand_component": "MZ", "capacity": float(resistance["MZ_Rd_kNm"]), "unit": "kNm"},
                    ],
                    "normative_reference": f"{ref}:LINEAR_N_M_SCREENING_INTERACTION",
                })
                rules.append({
                    "id": f"{member_id}-{combo_id}-BUCKLING-SCREEN",
                    "member_id": member_id,
                    "limit_state": "ULS",
                    "combination_id": combo_id,
                    "solver": solver,
                    "rule_type": "BUCKLING_RESISTANCE_RATIO",
                    "buckling_resistance_kN": float(resistance["buckling_screening_Rd_kN"]),
                    "mandatory": True,
                    "normative_reference": f"{ref}:ELASTIC_EULER_SCREENING_ONLY",
                })

        end_node = _text(member.get("node_j"))
        sls_ratio = column_limit_ratio if column else beam_limit_ratio
        dof = "UX" if column else "UZ"
        for combo_id in sls_ids:
            if end_node:
                rules.append({
                    "id": f"{member_id}-{combo_id}-DISPLACEMENT",
                    "member_id": member_id,
                    "limit_state": "SLS",
                    "combination_id": combo_id,
                    "solver": solver,
                    "rule_type": "NODE_DISPLACEMENT_LIMIT",
                    "node_id": end_node,
                    "dof": dof,
                    "max_abs_displacement_m": float(length_m / sls_ratio),
                    "mandatory": True,
                    "normative_reference": f"{ref}:INTERIM_SLS_DISPLACEMENT_SCREEN",
                })
            rules.append({
                "id": f"{member_id}-{combo_id}-SLENDERNESS-SCREEN",
                "member_id": member_id,
                "limit_state": "SLS",
                "combination_id": combo_id,
                "solver": solver,
                "rule_type": "SLENDERNESS_LIMIT",
                "actual_slenderness": float(design["screening_geometry"]["slenderness_screen"]),
                "max_slenderness": float(slenderness_limit),
                "mandatory": False,
                "normative_reference": f"{ref}:INTERIM_SLENDERNESS_SCREEN",
            })

        if design["reinforcement_candidate"]["reinforcement_limit_reached"]:
            warnings.append({
                "type": "RC_REINFORCEMENT_SCREENING_LIMIT_REACHED",
                "member_id": member_id,
                "message": "Candidate steel demand exceeded configured max ratio; redesign/review required.",
            })

    if not candidates:
        raise AutonomousRCDesignBlocked(
            "RC_MEMBERS_REQUIRED",
            "R8 vond geen RC members om te ontwerpen.",
        )

    member_input = {
        "code_basis": code_basis,
        "verification_rules": rules,
        "verification_policy": {
            "acceptable_analysis_validation_states": [str(analysis_validation_state)],
            "require_normative_reference": True,
            "require_mandatory_rules_for_each_member": True,
            "mandatory_limit_states": ["ULS", "SLS"],
            "pass_tolerance": 1e-12,
        },
    }

    return {
        "schema_version": "phoenix.autonomous-rc-design-candidate/1.0",
        "engine": {"id": ENGINE_ID, "version": VERSION},
        "project_id": project_id,
        "status": "CANDIDATE_GENERATED",
        "solver": solver,
        "analysis_validation_state": str(analysis_validation_state),
        "code_basis": code_basis,
        "numerical_parameter_status": parameter_status,
        "candidate_parameters": deepcopy(policy["candidate_parameters"]),
        "member_count": len(candidates),
        "candidate_members": candidates,
        "verification_rule_count": len(rules),
        "member_verification_input": member_input,
        "warnings": warnings,
        "limitations": [
            "Engineering candidate only; not a legal/code-compliance certificate.",
            "Current Dutch National Annex identity is referenced; interim R8 numerical parameters are not claimed to reproduce all Dutch NDP values.",
            "Detailed anchorage, laps, crack width, fire, fatigue, punching, torsion, D-regions and final second-order RC verification remain outside this R8 candidate scope.",
            "Local reinforcement product availability and Suriname legal applicability are not verified.",
            "Professional engineering review remains mandatory before construction release.",
        ],
        "release": {
            "automatic_code_compliance_claim": False,
            "automatic_structural_approval": False,
            "for_construction_release": "LOCKED",
            "production_release": "LOCKED",
            "engineering_review_required": True,
        },
    }
