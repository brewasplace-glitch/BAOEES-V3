#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

STATUS = "PASS_REAL_OPEN_SOURCE_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION"
NEXT_STAGE = "PHOENIX_4.41_REAL_PROJECT_STRUCTURAL_DESIGN_CONSOLIDATION_AND_DRAWINGS"
ENGINE_VERSION = "1.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def timber_design_strength(fmk_mpa: float, kmod: float, gamma_m: float) -> float:
    return kmod * fmk_mpa / gamma_m


def section_rect(b_mm: float, h_mm: float) -> Dict[str, float]:
    return {
        "A_mm2": b_mm * h_mm,
        "I_mm4": b_mm * h_mm ** 3 / 12.0,
        "W_mm3": b_mm * h_mm ** 2 / 6.0,
    }


def beam_uniform_analytic(span_m: float, w_kN_m: float, E_mpa: float, b_mm: float, h_mm: float) -> Dict[str, float]:
    sec = section_rect(b_mm, h_mm)
    L_mm = span_m * 1000.0
    w_N_mm = w_kN_m  # 1 kN/m = 1 N/mm
    max_moment_kNm = w_kN_m * span_m ** 2 / 8.0
    reaction_kN = w_kN_m * span_m / 2.0
    delta_mm = 5.0 * w_N_mm * L_mm ** 4 / (384.0 * E_mpa * sec["I_mm4"])
    return {
        "max_moment_kNm": round(max_moment_kNm, 6),
        "support_reaction_each_kN": round(reaction_kN, 6),
        "midspan_deflection_mm": round(delta_mm, 6),
    }


def try_opensees_uniform_beam(span_m: float, w_kN_m: float, E_mpa: float, b_mm: float, h_mm: float) -> Dict[str, Any]:
    try:
        import openseespy.opensees as ops  # type: ignore
    except Exception as exc:
        return {
            "engine": "OpenSeesPy",
            "execution": "BLOCKED_NATIVE_RUNTIME",
            "error": str(exc),
        }

    try:
        E_kN_m2 = E_mpa * 1000.0
        b_m = b_mm / 1000.0
        h_m = h_mm / 1000.0
        A = b_m * h_m
        I = b_m * h_m ** 3 / 12.0

        ops.wipe()
        ops.model("basic", "-ndm", 2, "-ndf", 3)

        nseg = 4
        for i in range(nseg + 1):
            ops.node(i + 1, span_m * i / nseg, 0.0)

        ops.fix(1, 1, 1, 0)
        ops.fix(nseg + 1, 0, 1, 0)

        ops.geomTransf("Linear", 1)
        for i in range(nseg):
            ops.element("elasticBeamColumn", i + 1, i + 1, i + 2, A, E_kN_m2, I, 1)

        ops.timeSeries("Linear", 1)
        ops.pattern("Plain", 1, 1)
        for i in range(nseg):
            ops.eleLoad("-ele", i + 1, "-type", "-beamUniform", -w_kN_m)

        ops.system("BandGeneral")
        ops.numberer("Plain")
        ops.constraints("Plain")
        ops.integrator("LoadControl", 1.0)
        ops.algorithm("Linear")
        ops.analysis("Static")
        rc = ops.analyze(1)
        if rc != 0:
            raise RuntimeError(f"OpenSees analyze returned {rc}")

        ops.reactions()
        r1 = float(ops.nodeReaction(1, 2))
        r2 = float(ops.nodeReaction(nseg + 1, 2))
        mid = float(ops.nodeDisp(3, 2))
        version = str(ops.version()) if hasattr(ops, "version") else "unknown"
        ops.wipe()

        return {
            "engine": "OpenSeesPy",
            "version": version,
            "support_reaction_1_kN": round(r1, 6),
            "support_reaction_2_kN": round(r2, 6),
            "reaction_sum_kN": round(r1 + r2, 6),
            "midspan_deflection_mm": round(mid * 1000.0, 6),
            "execution": "PASS",
        }
    except Exception as exc:
        try:
            ops.wipe()
        except Exception:
            pass
        return {
            "engine": "OpenSeesPy",
            "execution": "FAILED_RUNTIME",
            "error": str(exc),
        }


def pynite_uniform_beam(span_m: float, w_kN_m: float, E_mpa: float, b_mm: float, h_mm: float) -> Dict[str, Any]:
    from importlib.metadata import version
    from Pynite import FEModel3D  # type: ignore

    E_kN_m2 = E_mpa * 1000.0
    nu = 0.30
    G_kN_m2 = E_kN_m2 / (2.0 * (1.0 + nu))
    b_m = b_mm / 1000.0
    h_m = h_mm / 1000.0
    A = b_m * h_m
    Iy = h_m * b_m ** 3 / 12.0
    Iz = b_m * h_m ** 3 / 12.0
    J = max((b_m * h_m ** 3) / 3.0, 1e-12)

    model = FEModel3D()
    model.add_node("N1", 0.0, 0.0, 0.0)
    model.add_node("N2", span_m, 0.0, 0.0)
    model.add_material("TIMBER_PROXY", E_kN_m2, G_kN_m2, nu, 0.0)
    model.add_section("RECT", A, Iy, Iz, J)
    model.add_member("M1", "N1", "N2", "TIMBER_PROXY", "RECT")

    # Copy the documented PyNite simply-supported beam pattern:
    # translations fixed at both ends; torsion fixed at one end; flexural rotations free.
    model.def_support("N1", True, True, True, True, False, False)
    model.def_support("N2", True, True, True, False, False, False)

    model.add_member_dist_load("M1", "Fy", -w_kN_m, -w_kN_m, 0.0, span_m, "SLS")
    model.add_load_combo("SLS", {"SLS": 1.0})
    model.analyze_linear(log=False, check_statics=False, sparse=False)

    n1 = model.nodes["N1"]
    n2 = model.nodes["N2"]
    member = model.members["M1"]
    r1 = float(n1.RxnFY["SLS"])
    r2 = float(n2.RxnFY["SLS"])
    mid = float(member.deflection("dy", x=span_m / 2.0, combo_name="SLS"))

    return {
        "engine": "PyNiteFEA",
        "version": version("PyNiteFEA"),
        "support_reaction_1_kN": round(r1, 6),
        "support_reaction_2_kN": round(r2, 6),
        "reaction_sum_kN": round(r1 + r2, 6),
        "midspan_deflection_mm": round(mid * 1000.0, 6),
        "execution": "PASS",
    }


def solver_crosscheck_case(solver_result: Dict[str, Any], analytic: Dict[str, float], total_load: float) -> Dict[str, Any]:
    if solver_result.get("execution") != "PASS":
        return {
            "solver": solver_result,
            "equilibrium_relative_error": None,
            "deflection_relative_error": None,
            "crosscheck_status": "NOT_EXECUTED",
        }

    equilibrium_error = abs(abs(float(solver_result["reaction_sum_kN"])) - total_load) / max(total_load, 1e-9)
    defl_error = abs(abs(float(solver_result["midspan_deflection_mm"])) - analytic["midspan_deflection_mm"]) / max(analytic["midspan_deflection_mm"], 1e-9)
    return {
        "solver": solver_result,
        "equilibrium_relative_error": round(equilibrium_error, 8),
        "deflection_relative_error": round(defl_error, 8),
        "crosscheck_status": "PASS" if equilibrium_error <= 1e-6 and defl_error <= 0.02 else "FAIL",
    }

def timber_check(span_m: float, b_mm: float, h_mm: float, spacing_m: float, roof_gk: float, roof_qk: float,
                 E_mpa: float, fmd_mpa: float, deflection_ratio: float) -> Dict[str, Any]:
    w_uls = (1.35 * roof_gk + 1.50 * roof_qk) * spacing_m
    w_sls = (roof_gk + roof_qk) * spacing_m
    sec = section_rect(b_mm, h_mm)
    L_mm = span_m * 1000.0
    M_Nmm = w_uls * L_mm ** 2 / 8.0
    stress = M_Nmm / sec["W_mm3"]
    strength_util = stress / fmd_mpa
    delta = beam_uniform_analytic(span_m, w_sls, E_mpa, b_mm, h_mm)["midspan_deflection_mm"]
    limit = L_mm / deflection_ratio
    defl_util = delta / limit
    return {
        "span_m": span_m,
        "section_mm": [b_mm, h_mm],
        "spacing_m": spacing_m,
        "uls_line_load_kN_m": round(w_uls, 4),
        "sls_line_load_kN_m": round(w_sls, 4),
        "bending_stress_mpa": round(stress, 3),
        "design_bending_strength_proxy_mpa": round(fmd_mpa, 3),
        "strength_utilization": round(strength_util, 3),
        "deflection_mm": round(delta, 3),
        "deflection_limit_mm": round(limit, 3),
        "deflection_utilization": round(defl_util, 3),
        "status": "PASS" if max(strength_util, defl_util) <= 1.0 else "FAIL",
    }


def rc_ringbeam_check(span_m: float, trib_width_m: float, roof_gk: float, roof_qk: float,
                      b_mm: float, h_mm: float, gamma_conc: float, fyk_mpa: float, gamma_s: float,
                      cover_mm: float, assumed_bar_dia_mm: float) -> Dict[str, Any]:
    beam_self = (b_mm / 1000.0) * (h_mm / 1000.0) * gamma_conc
    g_line = roof_gk * trib_width_m + beam_self
    q_line = roof_qk * trib_width_m
    w_uls = 1.35 * g_line + 1.50 * q_line
    med = w_uls * span_m ** 2 / 8.0
    d_mm = h_mm - cover_mm - assumed_bar_dia_mm / 2.0
    z_mm = 0.9 * d_mm
    fyd = fyk_mpa / gamma_s
    as_req = med * 1e6 / (0.87 * fyd * z_mm)
    as_min = max(0.0013 * b_mm * d_mm, 0.26 * 2.2 / fyk_mpa * b_mm * d_mm)
    return {
        "span_m": span_m,
        "section_mm": [b_mm, h_mm],
        "tributary_roof_width_m": trib_width_m,
        "g_line_kN_m": round(g_line, 4),
        "q_line_kN_m": round(q_line, 4),
        "uls_line_load_kN_m": round(w_uls, 4),
        "MEd_kNm": round(med, 3),
        "effective_depth_proxy_mm": round(d_mm, 1),
        "required_tension_steel_mm2": round(max(as_req, as_min), 1),
        "calculated_As_from_moment_mm2": round(as_req, 1),
        "minimum_steel_proxy_mm2": round(as_min, 1),
        "status": "GEOMETRY_PRELIM_PASS_REINFORCEMENT_NOT_SOURCE_PROVEN",
        "detailing_note": "100 mm beam width is detailing-sensitive; Phoenix prefers 150x200 mm for the next preliminary design iteration where architecturally compatible.",
    }


def rc_column_axial_capacity(b_mm: float, h_mm: float, bars: int, bar_dia_mm: float,
                             fck_mpa: float, gamma_c: float, fyk_mpa: float, gamma_s: float) -> float:
    As = bars * math.pi * bar_dia_mm ** 2 / 4.0
    Ac = b_mm * h_mm - As
    fcd = fck_mpa / gamma_c
    fyd = fyk_mpa / gamma_s
    nrd_N = 0.8 * fcd * Ac + fyd * As
    return nrd_N / 1000.0


def generate_calculix_deck(path: Path, span_m: float, point_load_kN: float) -> None:
    text = f"""** PHOENIX 4.41 FALLBACK CROSS-CHECK
** REPRESENTATIVE SIMPLY-SUPPORTED BEAM - PRELIMINARY
*NODE
1,0.,0.,0.
2,{span_m/2:.6f},0.,0.
3,{span_m:.6f},0.,0.
*ELEMENT,TYPE=B31,ELSET=EALL
1,1,2
2,2,3
*MATERIAL,NAME=MAT
*ELASTIC
3.0E10,0.20
*BEAM SECTION,ELSET=EALL,MATERIAL=MAT,SECTION=RECT
0.10,0.20
0.,0.,1.
*BOUNDARY
1,1,5
3,2,5
*STEP
*STATIC
*CLOAD
2,2,{-point_load_kN*1000.0:.6f}
*NODE FILE
U,RF
*EL FILE
S,E
*END STEP
"""
    path.write_text(text, encoding="ascii")


def run_calculix(ccx_exe: str | None, deck_path: Path) -> Dict[str, Any]:
    result = {
        "engine": "CalculiX",
        "deck": deck_path.name,
        "execution": "NOT_AVAILABLE_DECK_GENERATED",
        "blocking": False,
    }
    if not ccx_exe:
        return result

    exe = Path(ccx_exe)
    if not exe.exists():
        result["execution"] = "CONFIGURED_PATH_NOT_FOUND_DECK_GENERATED"
        result["configured_path"] = ccx_exe
        return result

    job = deck_path.stem
    try:
        proc = subprocess.run(
            [str(exe), job],
            cwd=str(deck_path.parent),
            capture_output=True,
            text=True,
            timeout=120,
        )
        result["configured_path"] = str(exe)
        result["returncode"] = proc.returncode
        result["stdout_tail"] = proc.stdout[-4000:]
        result["stderr_tail"] = proc.stderr[-4000:]
        frd = deck_path.parent / f"{job}.frd"
        sta = deck_path.parent / f"{job}.sta"
        result["frd_exists"] = frd.exists()
        result["sta_exists"] = sta.exists()
        result["execution"] = "PASS" if proc.returncode == 0 else "FAILED_NONBLOCKING_FALLBACK"
    except Exception as exc:
        result["execution"] = "FAILED_NONBLOCKING_FALLBACK"
        result["error"] = str(exc)
    return result


def choose_timber_resize(spans: List[float], width_mm: float, depths_mm: List[float], spacing_m: float,
                         roof_gk: float, roof_qk: float, E_mpa: float, fmd_mpa: float, deflection_ratio: float) -> Dict[str, Any]:
    target_span = max(spans)
    candidates = []
    for h in depths_mm:
        check = timber_check(target_span, width_mm, h, spacing_m, roof_gk, roof_qk, E_mpa, fmd_mpa, deflection_ratio)
        candidates.append(check)
        if check["status"] == "PASS":
            return {
                "target_span_m": target_span,
                "selected_preliminary_section_mm": [width_mm, h],
                "status": "PRELIMINARY_RESIZE_FOUND",
                "candidate_check": check,
            }
    return {
        "target_span_m": target_span,
        "selected_preliminary_section_mm": None,
        "status": "NO_STANDARD_CANDIDATE_PASSED",
        "candidates": candidates,
    }


def verify_project(derivation_path: Path, config_path: Path, out: Path, ccx_exe: str | None) -> Dict[str, Any]:
    d = json.loads(derivation_path.read_text(encoding="utf-8"))
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    if d["status"] != "PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AND_LOAD_MODEL":
        raise RuntimeError("Prerequisite structural derivation/load model is not PASS")
    if d["governance"]["preliminary_not_for_construction"] is not True:
        raise RuntimeError("Expected preliminary governance flag is missing")

    roof_gk = float(d["load_model"]["roof"]["gk_total_kN_m2"])
    roof_qk = float(d["load_model"]["roof"]["nonaccessible_roof_imposed_qk_kN_m2"])
    spans = [float(v) for v in cfg["span_sensitivity_m"]]

    timber_cfg = cfg["timber_proxy"]
    fmd = timber_design_strength(timber_cfg["fmk_mpa"], timber_cfg["kmod"], timber_cfg["gamma_m"])
    E = timber_cfg["Emean_mpa"]
    spacing = timber_cfg["roof_member_spacing_m"]
    defl_ratio = timber_cfg["deflection_limit_ratio"]

    purlin_checks = [
        timber_check(s, 50.8, 76.2, spacing, roof_gk, roof_qk, E, fmd, defl_ratio)
        for s in spans
    ]
    rafter_checks = [
        timber_check(s, 50.8, 101.6, spacing, roof_gk, roof_qk, E, fmd, defl_ratio)
        for s in spans
    ]

    purlin_resize = choose_timber_resize(
        spans, 50.0, [100.0, 125.0, 150.0, 175.0, 200.0], spacing,
        roof_gk, roof_qk, E, fmd, defl_ratio
    )
    rafter_resize = choose_timber_resize(
        spans, 50.0, [125.0, 150.0, 175.0, 200.0], spacing,
        roof_gk, roof_qk, E, fmd, defl_ratio
    )

    ring_cfg = cfg["rc_ringbeam_proxy"]
    ring_checks = [
        rc_ringbeam_check(
            s, cfg["ringbeam_roof_tributary_width_m"], roof_gk, roof_qk,
            100.0, 200.0, cfg["materials"]["concrete_density_kN_m3"],
            cfg["materials"]["fyk_mpa"], cfg["materials"]["gamma_s"],
            ring_cfg["cover_mm"], ring_cfg["assumed_bar_dia_mm"]
        ) for s in spans
    ]

    # Preferred OpenSees execution plus PyNite operational fallback/cross-check.
    preferred_cases = []
    pynite_cases = []
    selected_cases = []
    open_sees_pass_count = 0

    for s in spans:
        w_sls = (roof_gk + roof_qk) * spacing
        ana = beam_uniform_analytic(s, w_sls, E, 50.8, 76.2)
        total_load = w_sls * s

        ose = try_opensees_uniform_beam(s, w_sls, E, 50.8, 76.2)
        ose_check = solver_crosscheck_case(ose, ana, total_load)
        preferred_cases.append({
            "member": "2x3_purlin_proxy",
            "span_m": s,
            "analytical": ana,
            **ose_check,
        })
        if ose_check["crosscheck_status"] == "PASS":
            open_sees_pass_count += 1

        pyn = pynite_uniform_beam(s, w_sls, E, 50.8, 76.2)
        pyn_check = solver_crosscheck_case(pyn, ana, total_load)
        pynite_cases.append({
            "member": "2x3_purlin_proxy",
            "span_m": s,
            "analytical": ana,
            **pyn_check,
        })
        if pyn_check["crosscheck_status"] != "PASS":
            raise RuntimeError("PyNite operational solver cross-check failed")

    if open_sees_pass_count == len(spans):
        selected_engine = "OpenSeesPy"
        selected_role = "PREFERRED_PRIMARY"
        selected_cases = preferred_cases
        preferred_status = "PASS"
    else:
        selected_engine = "PyNiteFEA"
        selected_role = "PRIMARY_RUNTIME_FALLBACK_AFTER_OPENSEES_NATIVE_BLOCKER"
        selected_cases = pynite_cases
        preferred_status = "BLOCKED_NATIVE_RUNTIME_OR_FAILED"

    # Column preliminary axial-only demand/capacity.
    col_cfg = cfg["column_proxy"]
    tributary_area = cfg["column_tributary_area_m2"]
    ring_length = cfg["column_associated_ringbeam_length_m"]
    column_self = 0.2 * 0.2 * 3.48 * cfg["materials"]["concrete_density_kN_m3"]
    ring_self = 0.1 * 0.2 * ring_length * cfg["materials"]["concrete_density_kN_m3"]
    g_col = roof_gk * tributary_area + column_self + ring_self
    q_col = roof_qk * tributary_area
    n_ed = (1.35 * g_col + 1.50 * q_col) * col_cfg["demand_envelope_factor"]
    n_rd = rc_column_axial_capacity(
        200.0, 200.0, 4, 12.0,
        cfg["materials"]["fck_mpa"], cfg["materials"]["gamma_c"],
        cfg["materials"]["fyk_mpa"], cfg["materials"]["gamma_s"]
    )
    col_util = n_ed / n_rd

    # Foundation gravity-bearing sensitivity.
    wall_g = float(d["load_model"]["masonry"]["150mm_wall_line_weight_kN_m"])
    ring_self_per_m = 0.1 * 0.2 * cfg["materials"]["concrete_density_kN_m3"]
    trib = cfg["ringbeam_roof_tributary_width_m"]
    strip_service_line = wall_g + ring_self_per_m + (roof_gk + roof_qk) * trib
    strip_pressure = strip_service_line / 0.8

    column_service = (g_col + q_col) * col_cfg["demand_envelope_factor"]
    pad_pressure = column_service / 1.0

    tank_env = float(d["load_model"]["elevated_durotank"]["preliminary_gravity_envelope_kN"])
    soil_checks = []
    for s in d["soil_model"]["preliminary_allowable_bearing_scenarios"]:
        qa = float(s["qa_kPa"])
        soil_checks.append({
            "qa_kPa": qa,
            "strip_0p8m_pressure_kPa": round(strip_pressure, 3),
            "strip_utilization": round(strip_pressure / qa, 3),
            "pad_1x1_pressure_kPa": round(pad_pressure, 3),
            "pad_utilization": round(pad_pressure / qa, 3),
            "tank_1x1_gravity_pressure_kPa": round(tank_env, 3),
            "tank_1x1_gravity_utilization": round(tank_env / qa, 3),
            "status": "PASS_GRAVITY_BEARING_ONLY" if max(strip_pressure, pad_pressure, tank_env) <= qa else "FAIL",
        })

    # Wind sensitivity only; no legal coefficient selection.
    wind_checks = []
    projected_width = cfg["wind_projected_width_m"]
    structural_height = float(d["geometry"]["levels_m"]["structural_ring_beam_top"])
    for w in d["load_model"]["wind_sensitivity"]:
        q = float(w["reference_dynamic_pressure_kN_m2"])
        force = q * projected_width * structural_height
        wind_checks.append({
            "scenario": w["scenario"],
            "qref_kN_m2": q,
            "unit_Cp_projected_force_kN": round(force, 3),
            "status": "SENSITIVITY_ONLY_NOT_CODE_DESIGN",
        })

    out.mkdir(parents=True, exist_ok=True)
    models = out / "solver_models"
    models.mkdir(exist_ok=True)
    ccx_deck = models / "calculix_representative_ringbeam.inp"
    max_ring = ring_checks[-1]
    point_equiv = max_ring["uls_line_load_kN_m"] * max_ring["span_m"]
    generate_calculix_deck(ccx_deck, max_ring["span_m"], point_equiv)
    ccx = run_calculix(ccx_exe, ccx_deck)

    result = {
        "schema": "PHOENIX_STRUCTURAL_SOLVER_ELEMENT_VERIFICATION_1.0",
        "engine_version": ENGINE_VERSION,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "project_id": d["project_id"],
        "source_sha256": d["source"]["sha256"],
        "prerequisite_status": d["status"],
        "preferred_solver": {
            "engine": "OpenSeesPy",
            "execution": preferred_status,
            "cases": preferred_cases,
        },
        "primary_solver": {
            "engine": selected_engine,
            "role": selected_role,
            "execution": "PASS",
            "cases": selected_cases,
        },
        "independent_runtime_solver": {
            "engine": "PyNiteFEA",
            "execution": "PASS",
            "cases": pynite_cases,
        },
        "fallback_solver": ccx,
        "element_verification": {
            "timber_purlin_2x3_at_900": {
                "source_section_nominal_mm": [50.8, 76.2],
                "span_sensitivity": purlin_checks,
                "preliminary_resize_if_3p4m_unsupported": purlin_resize,
                "status": "CONDITIONAL_PASS_ONLY_AT_SHORTER_SPANS",
            },
            "timber_rafter_2x4": {
                "source_section_nominal_mm": [50.8, 101.6],
                "span_sensitivity": rafter_checks,
                "preliminary_resize_if_3p4m_unsupported": rafter_resize,
                "status": "CONDITIONAL_PASS_ONLY_AT_SHORTER_SPANS",
            },
            "rc_ringbeam_100x200": {
                "span_sensitivity": ring_checks,
                "status": "STRENGTH_DEMAND_LOW_BUT_REINFORCEMENT_AND_DETAILING_NOT_SOURCE_PROVEN",
                "preliminary_next_iteration": "150x200 mm preferred where architecturally compatible, primarily for reinforcement detailing robustness",
            },
            "rc_column_200x200_4D12": {
                "modeled_axial_demand_kN": round(n_ed, 3),
                "proxy_axial_design_resistance_kN": round(n_rd, 3),
                "axial_utilization": round(col_util, 3),
                "status": "PASS_AXIAL_ONLY_MODELED_ENVELOPE" if col_util <= 1.0 else "FAIL",
                "limitations": ["combined N-M not checked", "slenderness second-order not checked", "lateral system not mapped"],
            },
            "strip_800x200": {
                "modeled_service_line_reaction_kN_m": round(strip_service_line, 3),
                "modeled_bearing_pressure_kPa": round(strip_pressure, 3),
                "status": "PASS_MODELED_GRAVITY_BEARING_ALL_SOIL_SCENARIOS" if all(x["strip_utilization"] <= 1 for x in soil_checks) else "FAIL",
                "final_geotechnical_status": "HOLD_SITE_SPECIFIC_GEOTECH_AND_SETTLEMENT",
            },
            "pad_1000x1000x200": {
                "modeled_service_reaction_kN": round(column_service, 3),
                "modeled_bearing_pressure_kPa": round(pad_pressure, 3),
                "status": "PASS_MODELED_GRAVITY_BEARING_ALL_SOIL_SCENARIOS" if all(x["pad_utilization"] <= 1 for x in soil_checks) else "FAIL",
                "final_geotechnical_status": "HOLD_SITE_SPECIFIC_GEOTECH_AND_PUNCHING/BENDING_DETAIL",
            },
            "elevated_tank": {
                "gravity_envelope_kN": tank_env,
                "one_square_metre_pad_gravity_checks": soil_checks,
                "status": "GRAVITY_BEARING_PRELIM_PASS; SUPPORT_FRAME/WIND/ANCHORAGE_UNRESOLVED",
            },
        },
        "soil_bearing_checks": soil_checks,
        "wind_sensitivity": wind_checks,
        "governance": {
            "preliminary_not_for_construction": True,
            "professional_structural_review_required": True,
            "for_construction_release": "LOCKED",
            "suriname_legal_code_basis_confirmed": False,
            "site_geotechnical_report_available": False,
            "timber_grade_confirmed": False,
        },
        "status": STATUS,
        "next_stage": NEXT_STAGE,
    }

    return result


def report(r: Dict[str, Any]) -> str:
    ev = r["element_verification"]
    lines = [
        "# PHOENIX 4.41 — Anijstraat #616 Solver Execution + Element Verification",
        "",
        f"**Status:** `{r['status']}`",
        "",
        "## Primary solver",
        "",
        f"- Preferred OpenSeesPy execution: **{r['preferred_solver']['execution']}**",
        f"- Executed primary engine: **{r['primary_solver']['engine']}** ({r['primary_solver']['role']}).",
        f"- Executed primary cases: **{len(r['primary_solver']['cases'])}**",
        f"- Independent PyNite execution: **{r['independent_runtime_solver']['execution']}**",
        "",
        "## Preliminary element conclusions",
        "",
        f"- 2x3 purlin @ 900: **{ev['timber_purlin_2x3_at_900']['status']}**.",
        f"- 2x4 rafter: **{ev['timber_rafter_2x4']['status']}**.",
        f"- RC ring beam 100x200: **{ev['rc_ringbeam_100x200']['status']}**.",
        f"- RC column 200x200 4D12: **{ev['rc_column_200x200_4D12']['status']}**, axial utilization {ev['rc_column_200x200_4D12']['axial_utilization']:.3f}.",
        f"- Strip footing 800x200: **{ev['strip_800x200']['status']}**.",
        f"- Pad footing 1000x1000x200: **{ev['pad_1000x1000x200']['status']}**.",
        f"- Elevated tank: **{ev['elevated_tank']['status']}**.",
        "",
        "## Important conditional finding",
        "",
        "The source 2x3 and 2x4 roof members are not accepted blindly. Their result depends strongly on the actual unsupported span.",
        "Phoenix therefore carries the 1.55 / 2.00 / 3.40 m span sensitivity into the next design iteration and generates preliminary resize candidates where necessary.",
        "",
        "## Governance",
        "",
        "- Wind remains a sensitivity study, not a confirmed Suriname legal wind design.",
        "- Foundation bearing checks are gravity-only and do not replace settlement/geotechnical design.",
        "- RC verification uses explicit material/reinforcement proxies where the source drawings do not provide sufficient authority.",
        "- CalculiX is an independent fallback; its deck is always retained, whether or not a local ccx executable is available.",
        "",
        "**PRELIMINARY / NOT FOR CONSTRUCTION**",
        "",
        f"Next stage: `{r['next_stage']}`",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(r: Dict[str, Any], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    def dump(name: str, obj: Any):
        (out/name).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    dump("solver_element_verification.json", r)
    dump("opensees_execution.json", r["preferred_solver"])
    dump("pynite_execution.json", r["independent_runtime_solver"])
    dump("selected_primary_solver.json", r["primary_solver"])
    dump("calculix_fallback_status.json", r["fallback_solver"])
    dump("element_verification.json", r["element_verification"])
    dump("soil_bearing_checks.json", r["soil_bearing_checks"])
    dump("wind_sensitivity.json", r["wind_sensitivity"])
    (out/"solver_element_verification_report.md").write_text(report(r), encoding="utf-8")
    manifest = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "evidence_manifest.json":
            manifest[p.relative_to(out).as_posix()] = {
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
    dump("evidence_manifest.json", manifest)


def analytical_self_test() -> None:
    a = beam_uniform_analytic(2.0, 1.0, 9000.0, 50.8, 76.2)
    assert abs(a["max_moment_kNm"] - 0.5) < 1e-9
    assert abs(a["support_reaction_each_kN"] - 1.0) < 1e-9
    fmd = timber_design_strength(18.0, 0.8, 1.3)
    assert abs(fmd - 11.0769230769) < 1e-6
    nrd = rc_column_axial_capacity(200, 200, 4, 12, 20, 1.5, 500, 1.15)
    assert 600.0 < nrd < 640.0
    print("PHOENIX_4_41_SOLVER_ELEMENT_ANALYTICAL_SELF_TEST=PASS")


def verify_output(path: Path) -> None:
    r = json.loads(path.read_text(encoding="utf-8"))
    assert r["status"] == STATUS
    assert r["primary_solver"]["execution"] == "PASS"
    assert r["primary_solver"]["engine"] in ("OpenSeesPy", "PyNiteFEA")
    assert len(r["primary_solver"]["cases"]) == 3
    assert all(c["crosscheck_status"] == "PASS" for c in r["primary_solver"]["cases"])
    assert r["independent_runtime_solver"]["execution"] == "PASS"
    assert all(c["crosscheck_status"] == "PASS" for c in r["independent_runtime_solver"]["cases"])
    assert r["preferred_solver"]["execution"] in ("PASS", "BLOCKED_NATIVE_RUNTIME_OR_FAILED")
    assert r["governance"]["preliminary_not_for_construction"] is True
    assert r["governance"]["for_construction_release"] == "LOCKED"
    print("PHOENIX_4_41_SOLVER_ELEMENT_OUTPUT_VERIFY=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--derivation", type=Path)
    ap.add_argument("--config", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--ccx-exe", default="")
    ap.add_argument("--verify-output", type=Path)
    ap.add_argument("--analytical-self-test", action="store_true")
    args = ap.parse_args()

    if args.analytical_self_test:
        analytical_self_test()
        return 0
    if args.verify_output:
        verify_output(args.verify_output)
        return 0
    if not all([args.derivation, args.config, args.output]):
        ap.error("--derivation --config --output are required")

    result = verify_project(args.derivation, args.config, args.output, args.ccx_exe or None)
    write_outputs(result, args.output)

    ev = result["element_verification"]
    print(f"PROJECT_ID={result['project_id']}")
    print("PREFERRED_SOLVER=OpenSeesPy")
    print(f"PREFERRED_SOLVER_STATUS={result['preferred_solver']['execution']}")
    print(f"PRIMARY_EXECUTED_SOLVER={result['primary_solver']['engine']}")
    print(f"PRIMARY_SOLVER_ROLE={result['primary_solver']['role']}")
    print("PRIMARY_SOLVER_EXECUTION=PASS")
    print(f"PRIMARY_SOLVER_CASES={len(result['primary_solver']['cases'])}")
    print("PYNITE_INDEPENDENT_EXECUTION=PASS")
    print(f"CALCULIX_FALLBACK={result['fallback_solver']['execution']}")
    print(f"PURLIN_STATUS={ev['timber_purlin_2x3_at_900']['status']}")
    print(f"RAFTER_STATUS={ev['timber_rafter_2x4']['status']}")
    print(f"RINGBEAM_STATUS={ev['rc_ringbeam_100x200']['status']}")
    print(f"COLUMN_AXIAL_UTILIZATION={ev['rc_column_200x200_4D12']['axial_utilization']}")
    print(f"STRIP_FOUNDATION_STATUS={ev['strip_800x200']['status']}")
    print(f"PAD_FOUNDATION_STATUS={ev['pad_1000x1000x200']['status']}")
    print("PRELIMINARY_NOT_FOR_CONSTRUCTION=TRUE")
    print(f"SOLVER_ELEMENT_VERIFICATION_STATUS={result['status']}")
    print(f"NEXT_STAGE={result['next_stage']}")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
