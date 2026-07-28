"""Project Phoenix reinforced-concrete beam design engine.

The module performs preliminary design of a simply supported rectangular
reinforced-concrete beam under distributed and point loads.  The implementation
is deliberately transparent and configurable.  It does not reproduce protected
standards text and it does not replace review by a licensed structural engineer.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.sax.saxutils import escape

FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
STATUS_LABEL = "PRELIMINARY STRUCTURAL DESIGN - ENGINEER REVIEW REQUIRED"


def _round(value: float, digits: int = 3) -> float:
    return round(float(value) + 0.0, digits)


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bar_area(diameter_mm: float) -> float:
    return math.pi * diameter_mm**2 / 4.0


def _safe_sqrt(value: float, label: str) -> float:
    if value < 0.0:
        raise ValueError(f"Negative square-root argument for {label}: {value}")
    return math.sqrt(value)


@dataclass(frozen=True)
class PointLoad:
    load_id: str
    characteristic_kn: float
    position_m: float
    category: str
    psi2: float


class ReinforcedConcreteBeamDesignEngine:
    VERSION = "1.0.0"

    def evaluate(self, config: Mapping[str, Any]) -> dict[str, Any]:
        self._validate_config(config)
        beam = config["beam"]
        materials = config["materials"]
        loads = config["loads"]
        factors = config["design_factors"]
        detailing = config["detailing"]
        service = config["serviceability"]
        standard = config["standard_profile"]

        L = float(beam["span_m"])
        b = float(beam["width_mm"])
        h = float(beam["height_mm"])
        cover = float(beam["nominal_cover_mm"])
        phi_link = float(beam["stirrup_diameter_mm"])
        phi_trial = float(beam["trial_main_bar_diameter_mm"])
        support_width = float(beam["support_width_mm"])

        concrete_density = float(materials["concrete_density_kn_m3"])
        fck = float(materials["fck_mpa"])
        fctm = float(materials["fctm_mpa"])
        fyk = float(materials["fyk_mpa"])
        Es = float(materials["steel_modulus_mpa"])
        fcm = fck + float(materials.get("fcm_increment_mpa", 8.0))
        Ecm = float(materials.get("ecm_mpa") or (22.0 * (fcm / 10.0) ** 0.3 * 1000.0))

        gamma_g = float(factors["gamma_g"])
        gamma_q = float(factors["gamma_q"])
        gamma_c = float(factors["gamma_c"])
        gamma_s = float(factors["gamma_s"])
        alpha_cc = float(factors["alpha_cc"])
        psi2_default = float(factors["psi2_default"])

        d = h - cover - phi_link - phi_trial / 2.0
        if d <= 0.0:
            raise ValueError("Effective depth is not positive.")
        z_approx = 0.9 * d

        self_weight = b / 1000.0 * h / 1000.0 * concrete_density
        gk_super = float(loads["permanent_udl_kn_m"])
        qk = float(loads["variable_udl_kn_m"])
        gk_total = self_weight + gk_super
        point_loads = [
            PointLoad(
                load_id=str(item["load_id"]),
                characteristic_kn=float(item["characteristic_kn"]),
                position_m=float(item["position_m"]),
                category=str(item.get("category", "variable")),
                psi2=float(item.get("psi2", psi2_default)),
            )
            for item in loads.get("point_loads", [])
        ]

        combinations = self._load_combinations(
            gk_total=gk_total,
            qk=qk,
            point_loads=point_loads,
            gamma_g=gamma_g,
            gamma_q=gamma_q,
            psi2_default=psi2_default,
        )
        uls = combinations["ULS_STR"]
        sls_char = combinations["SLS_CHARACTERISTIC"]
        sls_qp = combinations["SLS_QUASI_PERMANENT"]

        stations = self._stations(
            L=L,
            combinations=combinations,
            station_count=int(config["analysis"]["station_count"]),
        )
        uls_stations = stations["ULS_STR"]
        max_m = max(uls_stations, key=lambda row: row["moment_knm"])
        max_abs_v = max(uls_stations, key=lambda row: abs(row["shear_kn"]))
        Med = float(max_m["moment_knm"])
        Ved = abs(float(max_abs_v["shear_kn"]))
        RA_uls = float(uls["reaction_a_kn"])
        RB_uls = float(uls["reaction_b_kn"])

        fcd = alpha_cc * fck / gamma_c
        fyd = fyk / gamma_s
        eta = float(standard["stress_block_eta"])
        lam = float(standard["stress_block_lambda"])
        x_lim_ratio = float(standard["neutral_axis_limit_ratio"])

        M_nmm = Med * 1e6
        discriminant = d**2 - 2.0 * M_nmm / (eta * fcd * b)
        if discriminant <= 0:
            x = float("inf")
            z = 0.0
            As_req = float("inf")
        else:
            x = (d - _safe_sqrt(discriminant, "flexural neutral axis")) / lam
            z = d - 0.5 * lam * x
            As_req = M_nmm / (z * fyd)

        As_min = max(
            float(standard["minimum_reinforcement_factor_1"])
            * fctm
            / fyk
            * b
            * d,
            float(standard["minimum_reinforcement_factor_2"]) * b * d,
        )
        As_max = float(standard["maximum_reinforcement_ratio"]) * b * h
        As_design = max(As_req, As_min)
        bar_selection = self._select_longitudinal_bars(
            required_area_mm2=As_design,
            b_mm=b,
            cover_mm=cover,
            link_diameter_mm=phi_link,
            minimum_clear_spacing_mm=float(detailing["minimum_clear_spacing_mm"]),
            permitted_diameters_mm=[
                float(value) for value in detailing["permitted_main_bar_diameters_mm"]
            ],
            maximum_bars=int(detailing["maximum_bars_in_single_layer"]),
        )
        As_prov = float(bar_selection["provided_area_mm2"])
        phi_main = float(bar_selection["diameter_mm"])
        bar_count = int(bar_selection["count"])
        d_actual = h - cover - phi_link - phi_main / 2.0

        # Re-evaluate flexural section with selected bar diameter and actual depth.
        discriminant_actual = d_actual**2 - 2.0 * M_nmm / (eta * fcd * b)
        if discriminant_actual <= 0:
            x_actual = float("inf")
            z_actual = 0.0
            MRd = 0.0
        else:
            x_actual = (
                d_actual - _safe_sqrt(discriminant_actual, "actual neutral axis")
            ) / lam
            z_actual = d_actual - 0.5 * lam * x_actual
            MRd = As_prov * fyd * z_actual / 1e6

        flexure_util = Med / MRd if MRd > 0.0 else float("inf")
        neutral_axis_util = x_actual / (x_lim_ratio * d_actual) if math.isfinite(x_actual) else float("inf")

        # Shear design.
        rho_l = min(As_prov / (b * d_actual), float(standard["maximum_longitudinal_ratio_for_shear"]))
        k = min(1.0 + math.sqrt(200.0 / d_actual), 2.0)
        c_rdc = float(standard["c_rdc_numerator"]) / gamma_c
        vmin = float(standard["vmin_coefficient"]) * k**1.5 * math.sqrt(fck)
        vrdc_stress = max(
            c_rdc * k * (100.0 * rho_l * fck) ** (1.0 / 3.0),
            vmin,
        )
        VRdc = vrdc_stress * b * d_actual / 1000.0
        cot_theta = float(standard["cot_theta"])
        theta = math.atan(1.0 / cot_theta)
        tan_theta = math.tan(theta)
        v1 = float(standard["v1_coefficient"]) * (
            1.0 - fck / float(standard["v1_denominator_mpa"])
        )
        alpha_cw = float(standard["alpha_cw"])
        VRdmax = (
            alpha_cw
            * b
            * z_approx
            * v1
            * fcd
            / (cot_theta + tan_theta)
            / 1000.0
        )
        asw_s_req = 0.0
        if Ved > VRdc:
            asw_s_req = Ved * 1000.0 / (z_approx * fyd * cot_theta)
        asw_s_min = (
            float(standard["minimum_shear_reinforcement_coefficient"])
            * math.sqrt(fck)
            * b
            / fyk
        )
        asw_s_design = max(asw_s_req, asw_s_min)
        link_selection = self._select_stirrups(
            required_asw_per_s=asw_s_design,
            d_mm=d_actual,
            diameter_mm=phi_link,
            legs=int(detailing["stirrup_legs"]),
            maximum_spacing_mm=float(detailing["maximum_stirrup_spacing_mm"]),
            spacing_increment_mm=float(detailing["stirrup_spacing_increment_mm"]),
        )
        asw_s_prov = float(link_selection["provided_asw_per_s_mm2_per_mm"])
        VRds = asw_s_prov * z_approx * fyd * cot_theta / 1000.0
        shear_resistance = min(VRds, VRdmax)
        shear_util = Ved / shear_resistance if shear_resistance > 0.0 else float("inf")

        # Serviceability - cracked-section effective stiffness estimate.
        I_g = b * h**3 / 12.0
        n = Es / Ecm
        x_cr = (
            -n * As_prov
            + math.sqrt((n * As_prov) ** 2 + 2.0 * b * n * As_prov * d_actual)
        ) / b
        I_cr = b * x_cr**3 / 3.0 + n * As_prov * (d_actual - x_cr) ** 2
        M_cr = fctm * I_g / (h / 2.0) / 1e6
        M_sls_char = max(
            stations["SLS_CHARACTERISTIC"],
            key=lambda row: row["moment_knm"],
        )["moment_knm"]
        ratio = min(M_cr / M_sls_char, 1.0) if M_sls_char > 0 else 1.0
        I_eff = ratio**3 * I_g + (1.0 - ratio**3) * I_cr
        deflection = self._deflection_by_unit_load(
            L_m=L,
            combination=sls_char,
            E_mpa=Ecm,
            I_mm4=I_eff,
            segments=int(config["analysis"]["deflection_segments"]),
        )
        deflection_limit = L * 1000.0 / float(service["deflection_limit_ratio"])
        deflection_util = deflection / deflection_limit

        # Crack-width estimate using configurable EC2-style parameters.
        qp_stations = stations["SLS_QUASI_PERMANENT"]
        M_qp = max(qp_stations, key=lambda row: row["moment_knm"])["moment_knm"]
        sigma_s = M_qp * 1e6 / (max(z_actual, 0.8 * d_actual) * As_prov)
        h_ceff = min(
            2.5 * (h - d_actual),
            (h - x_cr) / 3.0,
            h / 2.0,
        )
        A_ceff = b * h_ceff
        rho_eff = As_prov / A_ceff
        c_bar = cover + phi_link
        k1 = float(service["crack_k1"])
        k2 = float(service["crack_k2"])
        k3 = float(service["crack_k3"])
        k4 = float(service["crack_k4"])
        kt = float(service["crack_kt"])
        sr_max = k3 * c_bar + k1 * k2 * k4 * phi_main / rho_eff
        eps_diff_a = (
            sigma_s
            - kt * fctm / rho_eff * (1.0 + n * rho_eff)
        ) / Es
        eps_diff_b = 0.6 * sigma_s / Es
        eps_diff = max(eps_diff_a, eps_diff_b, 0.0)
        crack_width = sr_max * eps_diff
        crack_limit = float(service["crack_width_limit_mm"])
        crack_util = crack_width / crack_limit

        # Anchorage estimate.
        fctk005 = float(materials["fctk_005_mpa"])
        fctd = fctk005 / gamma_c
        eta1 = float(detailing["anchorage_eta1"])
        eta2 = float(detailing["anchorage_eta2"])
        fbd = float(detailing["anchorage_bond_factor"]) * eta1 * eta2 * fctd
        sigma_sd = min(fyd, Med * 1e6 / (max(z_actual, 0.8 * d_actual) * As_prov))
        lb_rqd = phi_main / 4.0 * sigma_sd / fbd
        lb_min = max(
            float(detailing["minimum_anchorage_factor_phi"]) * phi_main,
            float(detailing["minimum_anchorage_mm"]),
        )
        lb_design = max(lb_rqd, lb_min)
        available_anchorage = support_width + float(detailing["support_extension_for_anchorage_mm"])
        anchorage_util = lb_design / available_anchorage

        bearing_stress_a = RA_uls * 1000.0 / (b * support_width)
        bearing_stress_b = RB_uls * 1000.0 / (b * support_width)
        bearing_limit = float(standard["support_bearing_stress_limit_factor"]) * fcd
        bearing_util = max(bearing_stress_a, bearing_stress_b) / bearing_limit

        depth_warning = h > float(standard["mandatory_deep_section_review_height_mm"])
        fit_pass = bool(bar_selection["fits_single_layer"])
        checks = [
            self._check("CHK-001", "Statics", abs(RA_uls + RB_uls - uls["total_load_kn"]) < 1e-6, "Reactions equal total ULS load."),
            self._check("CHK-002", "Flexure resistance", flexure_util <= 1.0, f"MEd/MRd = {flexure_util:.3f}"),
            self._check("CHK-003", "Neutral axis", neutral_axis_util <= 1.0, f"x/(xlim*d) = {neutral_axis_util:.3f}"),
            self._check("CHK-004", "Minimum reinforcement", As_prov >= As_min, f"As,prov = {As_prov:.1f} mm2; As,min = {As_min:.1f} mm2"),
            self._check("CHK-005", "Maximum reinforcement", As_prov <= As_max, f"As,prov = {As_prov:.1f} mm2; As,max = {As_max:.1f} mm2"),
            self._check("CHK-006", "Bar fit", fit_pass, bar_selection["description"]),
            self._check("CHK-007", "Shear resistance", shear_util <= 1.0, f"VEd/VRd = {shear_util:.3f}"),
            self._check("CHK-008", "Shear compression strut", Ved <= VRdmax, f"VEd = {Ved:.1f} kN; VRd,max = {VRdmax:.1f} kN"),
            self._check("CHK-009", "Deflection", deflection_util <= 1.0, f"delta = {deflection:.2f} mm; limit = {deflection_limit:.2f} mm"),
            self._check("CHK-010", "Crack width", crack_util <= 1.0, f"wk = {crack_width:.3f} mm; limit = {crack_limit:.3f} mm"),
            self._check("CHK-011", "Anchorage fit", anchorage_util <= 1.0, f"lb,design = {lb_design:.0f} mm; available = {available_anchorage:.0f} mm"),
            self._check("CHK-012", "Support bearing", bearing_util <= 1.0, f"bearing utilization = {bearing_util:.3f}"),
            self._check("CHK-013", "Deep-section review gate", not depth_warning, f"h = {h:.0f} mm; mandatory review threshold = {standard['mandatory_deep_section_review_height_mm']} mm"),
            self._check("CHK-014", "Fire design boundary", not bool(config["scope"]["fire_design_included"]), "Fire design is excluded and must be completed separately."),
            self._check("CHK-015", "Professional review gate", True, "All outputs remain preliminary until signed by a competent structural engineer."),
            self._check("CHK-016", "Standard profile declared", bool(standard["profile_id"]), standard["profile_id"]),
        ]
        technical_checks = checks[:13]
        all_technical_passed = all(item["passed"] for item in technical_checks)

        # Load-combination rows and calculation trail.
        combination_rows = [
            {
                "combination_id": key,
                "description": value["description"],
                "udl_kn_m": _round(value["udl_kn_m"]),
                "point_load_total_kn": _round(sum(item["load_kn"] for item in value["point_loads"])),
                "reaction_a_kn": _round(value["reaction_a_kn"]),
                "reaction_b_kn": _round(value["reaction_b_kn"]),
                "total_load_kn": _round(value["total_load_kn"]),
            }
            for key, value in combinations.items()
        ]

        result = {
            "schema_version": "phoenix.reinforced-concrete-beam-design/1.0",
            "engine_version": self.VERSION,
            "status": (
                "PRELIMINARY_DESIGN_CHECKS_PASSED"
                if all_technical_passed
                else "PRELIMINARY_DESIGN_CHECKS_FAILED"
            ),
            "project_id": config["project_id"],
            "beam_id": beam["beam_id"],
            "beam_name": beam["name"],
            "model_object_id": beam.get("model_object_id", "UNASSIGNED"),
            "standard_profile": dict(standard),
            "status_label": STATUS_LABEL,
            "geometry": {
                "span_m": L,
                "width_mm": b,
                "height_mm": h,
                "effective_depth_trial_mm": _round(d),
                "effective_depth_actual_mm": _round(d_actual),
                "support_width_mm": support_width,
            },
            "materials": {
                "concrete_class": materials["concrete_class"],
                "reinforcement_class": materials["reinforcement_class"],
                "fck_mpa": fck,
                "fcd_mpa": _round(fcd),
                "fctm_mpa": fctm,
                "fyk_mpa": fyk,
                "fyd_mpa": _round(fyd),
                "ecm_mpa": _round(Ecm),
            },
            "loads": {
                "self_weight_kn_m": _round(self_weight),
                "permanent_superimposed_kn_m": gk_super,
                "permanent_total_kn_m": _round(gk_total),
                "variable_udl_kn_m": qk,
                "point_loads": [item.__dict__ for item in point_loads],
            },
            "load_combinations": combination_rows,
            "analysis": {
                "uls_reaction_a_kn": _round(RA_uls),
                "uls_reaction_b_kn": _round(RB_uls),
                "uls_max_moment_knm": _round(Med),
                "uls_max_moment_position_m": _round(max_m["x_m"]),
                "uls_max_abs_shear_kn": _round(Ved),
                "uls_max_abs_shear_position_m": _round(max_abs_v["x_m"]),
                "station_count": len(uls_stations),
            },
            "flexure": {
                "required_steel_area_mm2": _round(As_req),
                "minimum_steel_area_mm2": _round(As_min),
                "maximum_steel_area_mm2": _round(As_max),
                "design_steel_area_mm2": _round(As_design),
                "provided_steel_area_mm2": _round(As_prov),
                "main_bar_count": bar_count,
                "main_bar_diameter_mm": phi_main,
                "bar_description": bar_selection["description"],
                "neutral_axis_depth_mm": _round(x_actual),
                "lever_arm_mm": _round(z_actual),
                "moment_resistance_knm": _round(MRd),
                "utilization": _round(flexure_util),
                "neutral_axis_utilization": _round(neutral_axis_util),
            },
            "shear": {
                "design_shear_kn": _round(Ved),
                "concrete_shear_resistance_kn": _round(VRdc),
                "required_asw_per_s_mm2_per_mm": _round(asw_s_req, 4),
                "minimum_asw_per_s_mm2_per_mm": _round(asw_s_min, 4),
                "provided_asw_per_s_mm2_per_mm": _round(asw_s_prov, 4),
                "stirrup_description": link_selection["description"],
                "stirrup_spacing_mm": link_selection["spacing_mm"],
                "shear_reinforcement_resistance_kn": _round(VRds),
                "maximum_shear_resistance_kn": _round(VRdmax),
                "governing_shear_resistance_kn": _round(shear_resistance),
                "utilization": _round(shear_util),
            },
            "serviceability": {
                "characteristic_max_moment_knm": _round(M_sls_char),
                "quasi_permanent_max_moment_knm": _round(M_qp),
                "cracking_moment_knm": _round(M_cr),
                "effective_inertia_mm4": _round(I_eff, 0),
                "estimated_deflection_mm": _round(deflection),
                "deflection_limit_mm": _round(deflection_limit),
                "deflection_utilization": _round(deflection_util),
                "estimated_crack_width_mm": _round(crack_width),
                "crack_width_limit_mm": crack_limit,
                "crack_width_utilization": _round(crack_util),
                "service_steel_stress_mpa": _round(sigma_s),
            },
            "detailing": {
                "bottom_reinforcement": bar_selection["description"],
                "top_hanger_reinforcement": detailing["top_hanger_reinforcement"],
                "stirrups": link_selection["description"],
                "design_anchorage_length_mm": _round(lb_design, 0),
                "available_anchorage_length_mm": _round(available_anchorage, 0),
                "anchorage_utilization": _round(anchorage_util),
                "nominal_cover_mm": cover,
            },
            "support_bearing": {
                "bearing_stress_a_mpa": _round(bearing_stress_a),
                "bearing_stress_b_mpa": _round(bearing_stress_b),
                "bearing_limit_mpa": _round(bearing_limit),
                "utilization": _round(bearing_util),
            },
            "stations": stations,
            "checks": checks,
            "metrics": {
                "technical_check_count": len(technical_checks),
                "technical_checks_passed": sum(1 for item in technical_checks if item["passed"]),
                "all_technical_checks_passed": all_technical_passed,
                "professional_review_required": True,
                "fire_design_included": bool(config["scope"]["fire_design_included"]),
                "final_structural_release_allowed": False,
            },
            "limitations": [
                "This is a preliminary design engine and not a signed structural calculation.",
                "The selected standard profile and National Annex parameters must be confirmed for the project.",
                "Fire resistance, robustness, seismic design, fatigue and accidental actions are outside this v1.0.0 scope.",
                "Construction tolerances, bar curtailment, laps, couplers, support-zone detailing and actual load paths require engineer review.",
                "The 2025 Dutch National Annex introduced shear-related changes; deep sections trigger a mandatory review gate.",
            ],
            "next_gate": (
                "Assign the beam to an approved model object, replace example loads with project loads, "
                "and obtain signed structural-engineer review before use for permit, tender or execution."
            ),
        }
        result["design_fingerprint_sha256"] = _fingerprint(result)
        return result

    @staticmethod
    def _validate_config(config: Mapping[str, Any]) -> None:
        required = [
            "project_id",
            "beam",
            "materials",
            "loads",
            "design_factors",
            "detailing",
            "serviceability",
            "standard_profile",
            "analysis",
            "scope",
        ]
        missing = [item for item in required if item not in config]
        if missing:
            raise ValueError("Missing configuration sections: " + ", ".join(missing))
        beam = config["beam"]
        for key in ("span_m", "width_mm", "height_mm", "nominal_cover_mm"):
            if float(beam[key]) <= 0.0:
                raise ValueError(f"Beam input must be positive: {key}")
        L = float(beam["span_m"])
        for item in config["loads"].get("point_loads", []):
            position = float(item["position_m"])
            if not (0.0 <= position <= L):
                raise ValueError(f"Point load outside beam span: {item['load_id']}")

    @staticmethod
    def _load_combinations(
        *,
        gk_total: float,
        qk: float,
        point_loads: list[PointLoad],
        gamma_g: float,
        gamma_q: float,
        psi2_default: float,
    ) -> dict[str, dict[str, Any]]:
        def make(combination_id: str, description: str, g_factor: float, q_factor: float, qp: bool = False):
            udl = g_factor * gk_total + q_factor * qk
            point_rows = []
            for item in point_loads:
                if item.category == "permanent":
                    factor = g_factor
                elif qp:
                    factor = item.psi2
                else:
                    factor = q_factor
                point_rows.append({
                    "load_id": item.load_id,
                    "load_kn": item.characteristic_kn * factor,
                    "position_m": item.position_m,
                })
            return combination_id, description, udl, point_rows

        raw = [
            make("ULS_STR", "Ultimate STR combination", gamma_g, gamma_q),
            make("SLS_CHARACTERISTIC", "Characteristic service combination", 1.0, 1.0),
            make("SLS_QUASI_PERMANENT", "Quasi-permanent service combination", 1.0, psi2_default, True),
        ]
        result: dict[str, dict[str, Any]] = {}
        for combination_id, description, udl, point_rows in raw:
            total = udl
            RA = udl / 2.0
            RB = udl / 2.0
            # Reactions are first calculated as load per unit span, then scaled.
            # Convert UDL reaction to full span.
            RA *= 1.0
            RB *= 1.0
            result[combination_id] = {
                "description": description,
                "udl_kn_m": udl,
                "point_loads": point_rows,
            }
        # Reactions need the span, therefore finalized in _stations.
        return result

    @staticmethod
    def _stations(
        *,
        L: float,
        combinations: Mapping[str, Mapping[str, Any]],
        station_count: int,
    ) -> dict[str, list[dict[str, float]]]:
        if station_count < 11:
            raise ValueError("station_count must be at least 11")
        x_values = {i * L / (station_count - 1) for i in range(station_count)}
        for combo in combinations.values():
            for point in combo["point_loads"]:
                a = float(point["position_m"])
                x_values.add(a)
                x_values.add(max(0.0, a - 1e-6))
                x_values.add(min(L, a + 1e-6))
        xs = sorted(x_values)
        output: dict[str, list[dict[str, float]]] = {}
        for combination_id, combo in combinations.items():
            w = float(combo["udl_kn_m"])
            point_rows = combo["point_loads"]
            RA = w * L / 2.0 + sum(
                float(item["load_kn"]) * (L - float(item["position_m"])) / L
                for item in point_rows
            )
            RB = w * L / 2.0 + sum(
                float(item["load_kn"]) * float(item["position_m"]) / L
                for item in point_rows
            )
            total = w * L + sum(float(item["load_kn"]) for item in point_rows)
            combo["reaction_a_kn"] = RA
            combo["reaction_b_kn"] = RB
            combo["total_load_kn"] = total
            rows = []
            for x in xs:
                shear = RA - w * x
                moment = RA * x - w * x**2 / 2.0
                for item in point_rows:
                    a = float(item["position_m"])
                    p = float(item["load_kn"])
                    if x >= a:
                        shear -= p
                        moment -= p * (x - a)
                rows.append({
                    "x_m": _round(x, 6),
                    "shear_kn": _round(shear, 6),
                    "moment_knm": _round(max(moment, 0.0), 6),
                })
            output[combination_id] = rows
        return output

    @staticmethod
    def _select_longitudinal_bars(
        *,
        required_area_mm2: float,
        b_mm: float,
        cover_mm: float,
        link_diameter_mm: float,
        minimum_clear_spacing_mm: float,
        permitted_diameters_mm: list[float],
        maximum_bars: int,
    ) -> dict[str, Any]:
        candidates = []
        for diameter in sorted(permitted_diameters_mm):
            area = _bar_area(diameter)
            for count in range(2, maximum_bars + 1):
                provided = count * area
                internal_width = b_mm - 2.0 * (cover_mm + link_diameter_mm)
                clear = (
                    (internal_width - count * diameter) / (count - 1)
                    if count > 1
                    else internal_width - diameter
                )
                fits = clear >= max(minimum_clear_spacing_mm, diameter)
                if provided >= required_area_mm2 and fits:
                    candidates.append((provided, diameter, count, clear))
        if not candidates:
            return {
                "provided_area_mm2": 0.0,
                "diameter_mm": max(permitted_diameters_mm),
                "count": maximum_bars,
                "clear_spacing_mm": 0.0,
                "fits_single_layer": False,
                "description": "NO SINGLE-LAYER BAR ARRANGEMENT FOUND",
            }
        provided, diameter, count, clear = min(candidates, key=lambda item: (item[0], item[2], item[1]))
        return {
            "provided_area_mm2": provided,
            "diameter_mm": diameter,
            "count": count,
            "clear_spacing_mm": clear,
            "fits_single_layer": True,
            "description": f"{count}T{diameter:g} bottom (As={provided:.0f} mm2; clear={clear:.0f} mm)",
        }

    @staticmethod
    def _select_stirrups(
        *,
        required_asw_per_s: float,
        d_mm: float,
        diameter_mm: float,
        legs: int,
        maximum_spacing_mm: float,
        spacing_increment_mm: float,
    ) -> dict[str, Any]:
        area = legs * _bar_area(diameter_mm)
        spacing_limit = min(0.75 * d_mm, maximum_spacing_mm)
        required_spacing = area / required_asw_per_s if required_asw_per_s > 0 else spacing_limit
        spacing = math.floor(min(required_spacing, spacing_limit) / spacing_increment_mm) * spacing_increment_mm
        spacing = max(spacing_increment_mm, spacing)
        provided = area / spacing
        return {
            "diameter_mm": diameter_mm,
            "legs": legs,
            "spacing_mm": spacing,
            "provided_asw_per_s_mm2_per_mm": provided,
            "description": f"{legs}-leg T{diameter_mm:g} stirrups @ {spacing:.0f} mm",
        }

    @staticmethod
    def _deflection_by_unit_load(
        *,
        L_m: float,
        combination: Mapping[str, Any],
        E_mpa: float,
        I_mm4: float,
        segments: int,
    ) -> float:
        # Numerical virtual-work integration for midspan deflection.
        L = L_m * 1000.0
        w = float(combination["udl_kn_m"])  # kN/m == N/mm
        points = [
            {
                "load_n": float(item["load_kn"]) * 1000.0,
                "position_mm": float(item["position_m"]) * 1000.0,
            }
            for item in combination["point_loads"]
        ]
        RA = float(combination["reaction_a_kn"]) * 1000.0
        dx = L / segments
        total = 0.0
        for index in range(segments + 1):
            x = index * dx
            M = RA * x - w * x**2 / 2.0
            for item in points:
                if x >= item["position_mm"]:
                    M -= item["load_n"] * (x - item["position_mm"])
            # Unit load at midspan.
            m = 0.5 * x if x <= L / 2.0 else 0.5 * (L - x)
            coefficient = 0.5 if index in (0, segments) else 1.0
            total += coefficient * M * m / (E_mpa * I_mm4) * dx
        return total

    @staticmethod
    def _check(check_id: str, topic: str, passed: bool, evidence: str) -> dict[str, Any]:
        return {
            "check_id": check_id,
            "topic": topic,
            "passed": bool(passed),
            "evidence": evidence,
        }


class ReinforcedConcreteBeamDesignExporter:
    def __init__(self, result: Mapping[str, Any]):
        self.result = result

    def export_all(self, output_dir: str | Path) -> dict[str, Path]:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}
        paths["summary"] = self._write_json(root / "01_design_summary.json", self._summary())
        paths["inputs"] = self._write_csv(root / "02_input_register.csv", self._input_rows())
        paths["combinations"] = self._write_csv(root / "03_load_combinations.csv", self.result["load_combinations"])
        paths["stations"] = self._write_csv(root / "04_station_results.csv", self._station_rows())
        paths["reinforcement"] = self._write_csv(root / "05_reinforcement_design.csv", self._reinforcement_rows())
        paths["checks"] = self._write_csv(root / "06_design_checks.csv", self.result["checks"])
        paths["traceability"] = self._write_csv(root / "07_calculation_traceability.csv", self._traceability_rows())
        paths["limitations"] = self._write_json(root / "08_scope_and_limitations.json", {
            "status_label": self.result["status_label"],
            "limitations": self.result["limitations"],
            "next_gate": self.result["next_gate"],
        })
        paths["dashboard"] = self._write_html(root / "09_beam_design_dashboard.html")
        paths["workbook"] = self._write_xlsx(root / "10_reinforced_concrete_beam_design_workbook.xlsx")
        paths["report_docx"] = self._write_docx(root / "11_reinforced_concrete_beam_design_report.docx")
        paths["report_pdf"] = self._write_pdf(root / "12_reinforced_concrete_beam_design_report.pdf")
        paths["diagrams_svg"] = self._write_svg_diagrams(root / "13_load_shear_moment_diagrams.svg")
        paths["reinforcement_svg"] = self._write_svg_reinforcement(root / "14_reinforcement_detail.svg")
        paths["reinforcement_dxf"] = self._write_dxf(root / "15_reinforcement_detail.dxf")
        paths["markdown"] = self._write_markdown(root / "16_calculation_note.md")
        paths["checksums"] = self._write_checksums(paths, root / "checksums.sha256")
        paths["issue_package"] = self._write_issue_zip(paths, root / "PHOENIX_RC_BEAM_PRELIMINARY_DESIGN_v1_0_0.zip")
        return paths

    def _summary(self) -> dict[str, Any]:
        r = self.result
        return {
            "schema_version": r["schema_version"],
            "engine_version": r["engine_version"],
            "status": r["status"],
            "project_id": r["project_id"],
            "beam_id": r["beam_id"],
            "beam_name": r["beam_name"],
            "model_object_id": r["model_object_id"],
            "design_fingerprint_sha256": r["design_fingerprint_sha256"],
            "geometry": r["geometry"],
            "analysis": r["analysis"],
            "flexure": r["flexure"],
            "shear": r["shear"],
            "serviceability": r["serviceability"],
            "detailing": r["detailing"],
            "metrics": r["metrics"],
            "final_structural_release_allowed": False,
            "next_gate": r["next_gate"],
        }

    def _input_rows(self) -> list[dict[str, Any]]:
        r = self.result
        rows = []
        def add(input_id: str, category: str, name: str, value: Any, unit: str, source: str):
            rows.append({
                "input_id": input_id,
                "category": category,
                "name": name,
                "value": value,
                "unit": unit,
                "source": source,
                "status": "USER_CONFIGURABLE" if source == "input_config" else "DERIVED",
            })
        g = r["geometry"]
        m = r["materials"]
        l = r["loads"]
        add("IN-001", "geometry", "span", g["span_m"], "m", "input_config")
        add("IN-002", "geometry", "width", g["width_mm"], "mm", "input_config")
        add("IN-003", "geometry", "height", g["height_mm"], "mm", "input_config")
        add("IN-004", "geometry", "effective_depth", g["effective_depth_actual_mm"], "mm", "derived")
        add("IN-005", "material", "fck", m["fck_mpa"], "MPa", "input_config")
        add("IN-006", "material", "fyd", m["fyd_mpa"], "MPa", "derived")
        add("IN-007", "load", "self_weight", l["self_weight_kn_m"], "kN/m", "derived")
        add("IN-008", "load", "permanent_superimposed", l["permanent_superimposed_kn_m"], "kN/m", "input_config")
        add("IN-009", "load", "variable_udl", l["variable_udl_kn_m"], "kN/m", "input_config")
        for index, point in enumerate(l["point_loads"], start=10):
            add(f"IN-{index:03d}", "point_load", point["load_id"], point["characteristic_kn"], "kN", "input_config")
        return rows

    def _station_rows(self) -> list[dict[str, Any]]:
        rows = []
        for combo, values in self.result["stations"].items():
            for value in values:
                rows.append({
                    "combination_id": combo,
                    "x_m": value["x_m"],
                    "shear_kn": value["shear_kn"],
                    "moment_knm": value["moment_knm"],
                })
        return rows

    def _reinforcement_rows(self) -> list[dict[str, Any]]:
        r = self.result
        return [
            {
                "zone": "bottom_span",
                "reinforcement": r["detailing"]["bottom_reinforcement"],
                "required_area_mm2": r["flexure"]["design_steel_area_mm2"],
                "provided_area_mm2": r["flexure"]["provided_steel_area_mm2"],
                "status": "PRELIMINARY",
            },
            {
                "zone": "top_hanger",
                "reinforcement": r["detailing"]["top_hanger_reinforcement"],
                "required_area_mm2": "DETAILING_MINIMUM",
                "provided_area_mm2": "SEE_REINFORCEMENT",
                "status": "PRELIMINARY",
            },
            {
                "zone": "shear_full_span",
                "reinforcement": r["detailing"]["stirrups"],
                "required_area_mm2": r["shear"]["required_asw_per_s_mm2_per_mm"],
                "provided_area_mm2": r["shear"]["provided_asw_per_s_mm2_per_mm"],
                "status": "PRELIMINARY",
            },
        ]

    def _traceability_rows(self) -> list[dict[str, Any]]:
        r = self.result
        return [
            {"calculation_id": "CAL-STAT-01", "topic": "reactions", "inputs": "geometry, loads, combinations", "output": f"RA={r['analysis']['uls_reaction_a_kn']} kN; RB={r['analysis']['uls_reaction_b_kn']} kN", "drawing": "13_load_shear_moment_diagrams.svg"},
            {"calculation_id": "CAL-FLEX-01", "topic": "flexure", "inputs": "MEd, b, d, fcd, fyd", "output": r["detailing"]["bottom_reinforcement"], "drawing": "14_reinforcement_detail.svg"},
            {"calculation_id": "CAL-SHEAR-01", "topic": "shear", "inputs": "VEd, d, fck, fyd", "output": r["detailing"]["stirrups"], "drawing": "14_reinforcement_detail.svg"},
            {"calculation_id": "CAL-SLS-01", "topic": "deflection", "inputs": "SLS loads, Ecm, Ieff", "output": f"{r['serviceability']['estimated_deflection_mm']} mm", "drawing": "11_reinforced_concrete_beam_design_report.docx"},
            {"calculation_id": "CAL-SLS-02", "topic": "crack_width", "inputs": "Mqp, As, cover, bar diameter", "output": f"{r['serviceability']['estimated_crack_width_mm']} mm", "drawing": "11_reinforced_concrete_beam_design_report.docx"},
            {"calculation_id": "CAL-DET-01", "topic": "anchorage", "inputs": "bar diameter, bond strength, stress", "output": f"{r['detailing']['design_anchorage_length_mm']} mm", "drawing": "14_reinforcement_detail.svg"},
        ]

    @staticmethod
    def _write_json(path: Path, value: Any) -> Path:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        return path

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> Path:
        fields = list(rows[0].keys()) if rows else ["empty"]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\r\n")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path

    def _write_html(self, path: Path) -> Path:
        r = self.result
        checks = "".join(
            "<tr>"
            f"<td>{html.escape(item['check_id'])}</td>"
            f"<td>{html.escape(item['topic'])}</td>"
            f"<td>{'PASS' if item['passed'] else 'FAIL'}</td>"
            f"<td>{html.escape(item['evidence'])}</td>"
            "</tr>"
            for item in r["checks"]
        )
        content = f"""<!doctype html><html lang=\"nl\"><head><meta charset=\"utf-8\"><title>Phoenix RC Beam Design</title><style>
body{{font-family:Arial,sans-serif;max-width:1200px;margin:28px auto;color:#172033;background:#f4f7fb}}h1{{margin-bottom:4px}}.notice{{background:#fff3cd;border:1px solid #c99a00;padding:12px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}.card{{background:#fff;border:1px solid #cad3df;border-radius:8px;padding:14px}}.value{{font-size:24px;font-weight:700}}table{{border-collapse:collapse;width:100%;background:#fff}}th,td{{border:1px solid #ccd5df;padding:7px;text-align:left}}th{{background:#20364f;color:white}}</style></head><body>
<h1>Project Phoenix - Reinforced Concrete Beam Design</h1><p class=\"notice\"><strong>{html.escape(r['status_label'])}</strong><br>Standard profile: {html.escape(r['standard_profile']['profile_id'])}</p>
<div class=\"grid\"><div class=\"card\"><div>Beam</div><div class=\"value\">{r['beam_id']}</div><div>{r['geometry']['span_m']} m | {r['geometry']['width_mm']:.0f}x{r['geometry']['height_mm']:.0f} mm</div></div><div class=\"card\"><div>ULS moment</div><div class=\"value\">{r['analysis']['uls_max_moment_knm']} kNm</div><div>Utilization {r['flexure']['utilization']}</div></div><div class=\"card\"><div>Bottom steel</div><div class=\"value\">{html.escape(r['detailing']['bottom_reinforcement'])}</div><div>{html.escape(r['detailing']['stirrups'])}</div></div><div class=\"card\"><div>Checks</div><div class=\"value\">{r['metrics']['technical_checks_passed']}/{r['metrics']['technical_check_count']}</div><div>Final release: BLOCKED</div></div></div>
<table><thead><tr><th>ID</th><th>Topic</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{checks}</tbody></table></body></html>"""
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def _write_markdown(self, path: Path) -> Path:
        r = self.result
        lines = [
            "# Reinforced Concrete Beam Preliminary Calculation Note",
            "",
            f"Status: **{r['status_label']}**",
            "",
            f"Beam `{r['beam_id']}`: span {r['geometry']['span_m']} m, section {r['geometry']['width_mm']:.0f} x {r['geometry']['height_mm']:.0f} mm.",
            "",
            "## Results",
            "",
            f"- ULS support reactions: {r['analysis']['uls_reaction_a_kn']} kN and {r['analysis']['uls_reaction_b_kn']} kN.",
            f"- Maximum ULS moment: {r['analysis']['uls_max_moment_knm']} kNm.",
            f"- Bottom reinforcement: {r['detailing']['bottom_reinforcement']}.",
            f"- Stirrups: {r['detailing']['stirrups']}.",
            f"- Estimated deflection: {r['serviceability']['estimated_deflection_mm']} mm.",
            f"- Estimated crack width: {r['serviceability']['estimated_crack_width_mm']} mm.",
            "",
            "## Boundaries",
            "",
        ]
        lines.extend(f"- {item}" for item in r["limitations"])
        lines.extend(["", f"Next gate: {r['next_gate']}", ""])
        path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        return path

    def _write_svg_diagrams(self, path: Path) -> Path:
        r = self.result
        L = r["geometry"]["span_m"]
        rows = r["stations"]["ULS_STR"]
        width, height = 1200, 780
        x0, x1 = 80, 1140
        plot_w = x1 - x0
        def sx(x): return x0 + x / L * plot_w
        max_v = max(abs(row["shear_kn"]) for row in rows) or 1.0
        max_m = max(row["moment_knm"] for row in rows) or 1.0
        shear_y0 = 310
        moment_y0 = 650
        shear_points = " ".join(f"{sx(row['x_m']):.1f},{shear_y0-row['shear_kn']/max_v*120:.1f}" for row in rows)
        moment_points = " ".join(f"{sx(row['x_m']):.1f},{moment_y0-row['moment_knm']/max_m*160:.1f}" for row in rows)
        svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\"><rect width=\"100%\" height=\"100%\" fill=\"white\"/><style>text{{font-family:Arial,sans-serif;fill:#172033}}.axis{{stroke:#172033;stroke-width:2}}.beam{{stroke:#111;stroke-width:8}}.diagram{{fill:none;stroke:#1d4ed8;stroke-width:3}}</style><text x=\"60\" y=\"45\" font-size=\"28\" font-weight=\"bold\">Project Phoenix - RC Beam Load, Shear and Moment</text><text x=\"60\" y=\"75\" font-size=\"16\">{escape(r['status_label'])}</text><line class=\"beam\" x1=\"{x0}\" y1=\"140\" x2=\"{x1}\" y2=\"140\"/><polygon points=\"{x0-15},175 {x0+15},175 {x0},145\" fill=\"#444\"/><polygon points=\"{x1-15},175 {x1+15},175 {x1},145\" fill=\"#444\"/><text x=\"{x0}\" y=\"205\">A</text><text x=\"{x1}\" y=\"205\">B</text><text x=\"60\" y=\"255\" font-size=\"20\" font-weight=\"bold\">ULS shear V(x) [kN]</text><line class=\"axis\" x1=\"{x0}\" y1=\"{shear_y0}\" x2=\"{x1}\" y2=\"{shear_y0}\"/><polyline class=\"diagram\" points=\"{shear_points}\"/><text x=\"60\" y=\"560\" font-size=\"20\" font-weight=\"bold\">ULS moment M(x) [kNm]</text><line class=\"axis\" x1=\"{x0}\" y1=\"{moment_y0}\" x2=\"{x1}\" y2=\"{moment_y0}\"/><polyline class=\"diagram\" points=\"{moment_points}\"/><text x=\"60\" y=\"745\" font-size=\"15\">MEd,max = {r['analysis']['uls_max_moment_knm']} kNm | VEd,max = {r['analysis']['uls_max_abs_shear_kn']} kN</text></svg>"""
        path.write_text(svg, encoding="utf-8", newline="\n")
        return path

    def _write_svg_reinforcement(self, path: Path) -> Path:
        r = self.result
        L = r["geometry"]["span_m"]
        b = r["geometry"]["width_mm"]
        h = r["geometry"]["height_mm"]
        count = r["flexure"]["main_bar_count"]
        phi = r["flexure"]["main_bar_diameter_mm"]
        cover = r["detailing"]["nominal_cover_mm"]
        circles = "".join(f'<circle cx="{735 + (i-(count-1)/2)*35:.1f}" cy="535" r="{max(5,phi/2):.1f}" fill="#b91c1c"/>' for i in range(count))
        svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1200\" height=\"760\" viewBox=\"0 0 1200 760\"><rect width=\"100%\" height=\"100%\" fill=\"white\"/><style>text{{font-family:Arial,sans-serif;fill:#172033}}.concrete{{fill:#edf2f7;stroke:#172033;stroke-width:3}}.steel{{stroke:#b91c1c;stroke-width:8;fill:none}}.link{{stroke:#1d4ed8;stroke-width:3;fill:none}}</style><text x=\"50\" y=\"45\" font-size=\"28\" font-weight=\"bold\">Preliminary Reinforcement Detail - {escape(r['beam_id'])}</text><text x=\"50\" y=\"75\" font-size=\"16\">{escape(r['status_label'])}</text><rect class=\"concrete\" x=\"70\" y=\"150\" width=\"730\" height=\"260\"/><line class=\"steel\" x1=\"105\" y1=\"370\" x2=\"765\" y2=\"370\"/><line class=\"steel\" x1=\"105\" y1=\"190\" x2=\"765\" y2=\"190\" stroke-width=\"5\"/><path class=\"link\" d=\"M105 185 L105 375 L765 375 L765 185 Z\"/><text x=\"95\" y=\"450\" font-size=\"18\">Span {L:g} m | Section {b:.0f} x {h:.0f} mm</text><text x=\"95\" y=\"480\" font-size=\"18\">Bottom: {escape(r['detailing']['bottom_reinforcement'])}</text><text x=\"95\" y=\"510\" font-size=\"18\">Top: {escape(r['detailing']['top_hanger_reinforcement'])}</text><text x=\"95\" y=\"540\" font-size=\"18\">Links: {escape(r['detailing']['stirrups'])}</text><text x=\"95\" y=\"570\" font-size=\"18\">Nominal cover: {cover:g} mm | Anchorage: {r['detailing']['design_anchorage_length_mm']:.0f} mm</text><rect class=\"concrete\" x=\"620\" y=\"150\" width=\"270\" height=\"420\"/><rect class=\"link\" x=\"650\" y=\"180\" width=\"210\" height=\"360\"/>{circles}<circle cx=\"680\" cy=\"210\" r=\"6\" fill=\"#b91c1c\"/><circle cx=\"830\" cy=\"210\" r=\"6\" fill=\"#b91c1c\"/><text x=\"620\" y=\"620\" font-size=\"17\">Cross-section - preliminary</text><text x=\"50\" y=\"710\" font-size=\"16\">Bar curtailment, support-zone link spacing, laps, fire cover and constructability require engineer detailing.</text></svg>"""
        path.write_text(svg, encoding="utf-8", newline="\n")
        return path

    def _write_dxf(self, path: Path) -> Path:
        r = self.result
        L = r["geometry"]["span_m"] * 1000.0
        h = r["geometry"]["height_mm"]
        lines = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1015", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        def line(x1,y1,x2,y2,layer):
            lines.extend(["0","LINE","8",layer,"10",str(x1),"20",str(y1),"30","0","11",str(x2),"21",str(y2),"31","0"])
        line(0,0,L,0,"CONCRETE")
        line(0,h,L,h,"CONCRETE")
        line(0,0,0,h,"CONCRETE")
        line(L,0,L,h,"CONCRETE")
        line(150,60,L-150,60,"REBAR_BOTTOM")
        line(150,h-60,L-150,h-60,"REBAR_TOP")
        spacing=float(r["shear"]["stirrup_spacing_mm"])
        x=150.0
        while x<=L-150:
            line(x,40,x,h-40,"STIRRUPS")
            x+=spacing
        lines.extend(["0","ENDSEC","0","EOF"])
        path.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")
        return path

    def _write_pdf(self, path: Path) -> Path:
        r = self.result
        pages: list[list[str]] = []
        pages.append([
            "PROJECT PHOENIX",
            "REINFORCED CONCRETE BEAM PRELIMINARY DESIGN REPORT",
            "",
            f"Beam: {r['beam_id']} - {r['beam_name']}",
            f"Project: {r['project_id']}",
            f"Status: {r['status_label']}",
            "",
            f"Geometry: L={r['geometry']['span_m']} m, b={r['geometry']['width_mm']:.0f} mm, h={r['geometry']['height_mm']:.0f} mm",
            f"Materials: {r['materials']['concrete_class']} / {r['materials']['reinforcement_class']}",
            f"Standard profile: {r['standard_profile']['profile_id']}",
            "",
            "This report is not a signed structural calculation and is not approved for construction.",
        ])
        pages.append([
            "1. LOADS AND ANALYSIS",
            "",
            f"Self weight: {r['loads']['self_weight_kn_m']} kN/m",
            f"Total permanent UDL: {r['loads']['permanent_total_kn_m']} kN/m",
            f"Variable UDL: {r['loads']['variable_udl_kn_m']} kN/m",
            f"ULS reaction A: {r['analysis']['uls_reaction_a_kn']} kN",
            f"ULS reaction B: {r['analysis']['uls_reaction_b_kn']} kN",
            f"ULS maximum moment: {r['analysis']['uls_max_moment_knm']} kNm",
            f"ULS maximum shear: {r['analysis']['uls_max_abs_shear_kn']} kN",
            "",
            "Point loads:",
        ] + [f"- {p['load_id']}: {p['characteristic_kn']} kN at {p['position_m']} m" for p in r['loads']['point_loads']])
        pages.append([
            "2. FLEXURE AND SHEAR",
            "",
            f"Required steel: {r['flexure']['required_steel_area_mm2']} mm2",
            f"Provided steel: {r['flexure']['provided_steel_area_mm2']} mm2",
            f"Bottom reinforcement: {r['detailing']['bottom_reinforcement']}",
            f"Moment resistance: {r['flexure']['moment_resistance_knm']} kNm",
            f"Flexure utilization: {r['flexure']['utilization']}",
            "",
            f"Concrete shear resistance: {r['shear']['concrete_shear_resistance_kn']} kN",
            f"Stirrups: {r['detailing']['stirrups']}",
            f"Governing shear resistance: {r['shear']['governing_shear_resistance_kn']} kN",
            f"Shear utilization: {r['shear']['utilization']}",
        ])
        pages.append([
            "3. SERVICEABILITY AND DETAILING",
            "",
            f"Estimated deflection: {r['serviceability']['estimated_deflection_mm']} mm",
            f"Deflection limit: {r['serviceability']['deflection_limit_mm']} mm",
            f"Estimated crack width: {r['serviceability']['estimated_crack_width_mm']} mm",
            f"Crack width limit: {r['serviceability']['crack_width_limit_mm']} mm",
            f"Design anchorage length: {r['detailing']['design_anchorage_length_mm']:.0f} mm",
            f"Available anchorage length: {r['detailing']['available_anchorage_length_mm']:.0f} mm",
            "",
            "The serviceability calculations are preliminary estimates and require engineer confirmation.",
        ])
        pages.append(["4. DESIGN CHECKS", ""] + [f"{item['check_id']} | {item['topic']} | {'PASS' if item['passed'] else 'FAIL'} | {item['evidence']}" for item in r['checks']])
        pages.append(["5. LIMITATIONS AND NEXT GATE", ""] + [f"- {item}" for item in r['limitations']] + ["", "Next gate:", r["next_gate"]])
        self._simple_pdf(path, pages)
        return path

    @staticmethod
    def _simple_pdf(path: Path, pages: list[list[str]]) -> None:
        objects: list[bytes] = []
        def add(data: str | bytes) -> int:
            objects.append(data.encode("latin-1", "replace") if isinstance(data, str) else data)
            return len(objects)
        font_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        bold_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        page_entries = []
        for page_lines in pages:
            expanded_lines: list[str] = []
            for source_index, line in enumerate(page_lines):
                if source_index == 0 or not line:
                    expanded_lines.append(line)
                    continue
                subsequent_indent = "  " if line.startswith("- ") else ""
                expanded_lines.extend(
                    textwrap.wrap(
                        line,
                        width=88,
                        break_long_words=False,
                        break_on_hyphens=False,
                        subsequent_indent=subsequent_indent,
                    ) or [""]
                )
            commands = ["BT", "/F2 15 Tf", "50 790 Td"]
            for index, line in enumerate(expanded_lines):
                safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                if index == 0:
                    commands.extend([f"({safe}) Tj", "0 -26 Td", "/F1 9.5 Tf"])
                else:
                    commands.extend([f"({safe}) Tj", "0 -15 Td"])
            commands.append("ET")
            stream = "\n".join(commands).encode("latin-1", "replace")
            content_id = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
            page_id = add(f"<< /Type /Page /Parent PARENT /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R /F2 {bold_id} 0 R >> >> /Contents {content_id} 0 R >>")
            page_entries.append(page_id)
        kids = " ".join(f"{pid} 0 R" for pid in page_entries)
        pages_id = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_entries)} >>")
        for pid in page_entries:
            objects[pid-1] = objects[pid-1].replace(b"PARENT", f"{pages_id} 0 R".encode())
        catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode())
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref = len(output)
        output.extend(f"xref\n0 {len(objects)+1}\n".encode())
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        path.write_bytes(bytes(output))

    def _write_docx(self, path: Path) -> Path:
        r = self.result
        paragraphs = [
            ("Project Phoenix", "Title"),
            ("Reinforced Concrete Beam Preliminary Design Report", "Title"),
            (r["status_label"], "Warning"),
            (f"Beam {r['beam_id']} - {r['beam_name']}", "Heading1"),
            (f"Span {r['geometry']['span_m']} m; section {r['geometry']['width_mm']:.0f} x {r['geometry']['height_mm']:.0f} mm.", "Normal"),
            (f"Materials: {r['materials']['concrete_class']} concrete and {r['materials']['reinforcement_class']} reinforcement.", "Normal"),
            ("1. Loads and structural analysis", "Heading1"),
            (f"Self weight is {r['loads']['self_weight_kn_m']} kN/m. The maximum ULS moment is {r['analysis']['uls_max_moment_knm']} kNm and the maximum ULS shear is {r['analysis']['uls_max_abs_shear_kn']} kN.", "Normal"),
            ("2. Flexural design", "Heading1"),
            (f"The preliminary bottom reinforcement is {r['detailing']['bottom_reinforcement']}. The calculated moment resistance is {r['flexure']['moment_resistance_knm']} kNm, with utilization {r['flexure']['utilization']}.", "Normal"),
            ("3. Shear design", "Heading1"),
            (f"The preliminary shear reinforcement is {r['detailing']['stirrups']}. The governing resistance is {r['shear']['governing_shear_resistance_kn']} kN, with utilization {r['shear']['utilization']}.", "Normal"),
            ("4. Serviceability", "Heading1"),
            (f"Estimated deflection is {r['serviceability']['estimated_deflection_mm']} mm against a {r['serviceability']['deflection_limit_mm']} mm limit. Estimated crack width is {r['serviceability']['estimated_crack_width_mm']} mm against a {r['serviceability']['crack_width_limit_mm']} mm limit.", "Normal"),
            ("5. Detailing", "Heading1"),
            (f"Top hanger reinforcement: {r['detailing']['top_hanger_reinforcement']}. Design anchorage length: {r['detailing']['design_anchorage_length_mm']:.0f} mm. Nominal cover: {r['detailing']['nominal_cover_mm']} mm.", "Normal"),
            ("6. Checks", "Heading1"),
        ]
        paragraphs.extend((f"{item['check_id']} - {item['topic']}: {'PASS' if item['passed'] else 'FAIL'} - {item['evidence']}", "Normal") for item in r["checks"])
        paragraphs.append(("7. Limitations", "Heading1"))
        paragraphs.extend((f"- {item}", "Normal") for item in r["limitations"])
        paragraphs.append(("This document is not approved for permit, tender or execution use until signed by a competent structural engineer.", "Warning"))
        self._simple_docx(path, paragraphs)
        return path

    @staticmethod
    def _simple_docx(path: Path, paragraphs: Iterable[tuple[str, str]]) -> None:
        def p(text: str, style: str) -> str:
            style_map = {"Title": "Title", "Heading1": "Heading1", "Warning": "Warning", "Normal": "Normal"}
            return f'<w:p><w:pPr><w:pStyle w:val="{style_map.get(style,"Normal")}"/></w:pPr><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        body = "".join(p(text, style) for text, style in paragraphs)
        document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>'''
        styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="20"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="32"/></w:rPr><w:pPr><w:spacing w:after="180"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="26"/></w:rPr><w:pPr><w:spacing w:before="220" w:after="100"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Warning"><w:name w:val="Warning"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="9C0006"/><w:sz w:val="20"/></w:rPr><w:pPr><w:shd w:fill="FFC7CE"/><w:spacing w:before="100" w:after="100"/></w:pPr></w:style></w:styles>'''
        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
        root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
        doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in [
                ("[Content_Types].xml", content_types),
                ("_rels/.rels", root_rels),
                ("word/document.xml", document),
                ("word/styles.xml", styles),
                ("word/_rels/document.xml.rels", doc_rels),
            ]:
                info = ReinforcedConcreteBeamDesignExporter._canonical_info(name)
                archive.writestr(info, data.encode("utf-8"))

    def _write_xlsx(self, path: Path) -> Path:
        sheets = self._xlsx_sheets()
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            self._writestr(archive, "[Content_Types].xml", self._xlsx_content_types(len(sheets)))
            self._writestr(archive, "_rels/.rels", self._xlsx_root_rels())
            self._writestr(archive, "docProps/core.xml", self._xlsx_core_properties())
            self._writestr(archive, "docProps/app.xml", self._xlsx_app_properties([name for name, _ in sheets]))
            self._writestr(archive, "xl/workbook.xml", self._xlsx_workbook([name for name, _ in sheets]))
            self._writestr(archive, "xl/_rels/workbook.xml.rels", self._xlsx_workbook_rels(len(sheets)))
            self._writestr(archive, "xl/styles.xml", self._xlsx_styles())
            for index, (_, rows) in enumerate(sheets, start=1):
                self._writestr(archive, f"xl/worksheets/sheet{index}.xml", self._xlsx_worksheet(rows))
        return path

    def _xlsx_sheets(self) -> list[tuple[str, list[list[Any]]]]:
        r = self.result
        dashboard = [
            ["PROJECT PHOENIX - REINFORCED CONCRETE BEAM DESIGN"],
            [STATUS_LABEL],
            [],
            ["Metric", "Value", "Unit", "Status"],
            ["Beam ID", r["beam_id"], "", "LINKED"],
            ["Span", r["geometry"]["span_m"], "m", "INPUT"],
            ["Section", f"{r['geometry']['width_mm']:.0f} x {r['geometry']['height_mm']:.0f}", "mm", "INPUT"],
            ["ULS maximum moment", r["analysis"]["uls_max_moment_knm"], "kNm", "CALCULATED"],
            ["ULS maximum shear", r["analysis"]["uls_max_abs_shear_kn"], "kN", "CALCULATED"],
            ["Bottom reinforcement", r["detailing"]["bottom_reinforcement"], "", "PRELIMINARY"],
            ["Stirrups", r["detailing"]["stirrups"], "", "PRELIMINARY"],
            ["Technical checks", f"{r['metrics']['technical_checks_passed']}/{r['metrics']['technical_check_count']}", "", "PASS" if r['metrics']['all_technical_checks_passed'] else "FAIL"],
            ["Final structural release", "NO", "", "BLOCKED"],
        ]
        inputs = [
            ["INPUTS"], [STATUS_LABEL], [],
            ["Input", "Value", "Unit", "Source"],
            ["Span", r["geometry"]["span_m"], "m", "Configuration"],
            ["Width", r["geometry"]["width_mm"], "mm", "Configuration"],
            ["Height", r["geometry"]["height_mm"], "mm", "Configuration"],
            ["Nominal cover", r["detailing"]["nominal_cover_mm"], "mm", "Configuration"],
            ["fck", r["materials"]["fck_mpa"], "MPa", "Configuration"],
            ["fyd", r["materials"]["fyd_mpa"], "MPa", "Derived"],
            ["Self weight", r["loads"]["self_weight_kn_m"], "kN/m", "Derived"],
            ["Permanent total", r["loads"]["permanent_total_kn_m"], "kN/m", "Derived"],
            ["Variable UDL", r["loads"]["variable_udl_kn_m"], "kN/m", "Configuration"],
        ]
        analysis = [
            ["STRUCTURAL ANALYSIS"], [STATUS_LABEL], [],
            ["Result", "Formula", "Calculated value", "Unit"],
            ["ULS reaction A", "=Loads!B5*Inputs!B5/2+Loads!B6/2", {"formula": "Loads!B5*Inputs!B5/2+Loads!B6/2", "value": r["analysis"]["uls_reaction_a_kn"]}, "kN"],
            ["ULS reaction B", "=Loads!B5*Inputs!B5/2+Loads!B6/2", {"formula": "Loads!B5*Inputs!B5/2+Loads!B6/2", "value": r["analysis"]["uls_reaction_b_kn"]}, "kN"],
            ["ULS max moment", "=Loads!B5*Inputs!B5^2/8+Loads!B6*Inputs!B5/4", {"formula": "Loads!B5*Inputs!B5^2/8+Loads!B6*Inputs!B5/4", "value": r["analysis"]["uls_max_moment_knm"]}, "kNm"],
            ["ULS max shear", "=Loads!B5*Inputs!B5/2+Loads!B6/2", {"formula": "Loads!B5*Inputs!B5/2+Loads!B6/2", "value": r["analysis"]["uls_max_abs_shear_kn"]}, "kN"],
        ]
        point_uls = sum(item["load_kn"] for item in self._combination("ULS_STR")["point_loads"])
        loads = [
            ["LOADS AND COMBINATIONS"], [STATUS_LABEL], [],
            ["Load item", "Value", "Unit", "Status"],
            ["ULS distributed load", self._combination("ULS_STR")["udl_kn_m"], "kN/m", "CALCULATED"],
            ["ULS point-load total", point_uls, "kN", "CALCULATED"],
            ["SLS distributed load", self._combination("SLS_CHARACTERISTIC")["udl_kn_m"], "kN/m", "CALCULATED"],
        ]
        flexure = [
            ["FLEXURAL DESIGN"], [STATUS_LABEL], [],
            ["Parameter", "Value", "Unit", "Check"],
            ["MEd", r["analysis"]["uls_max_moment_knm"], "kNm", "INPUT"],
            ["As required", r["flexure"]["required_steel_area_mm2"], "mm2", "CALCULATED"],
            ["As minimum", r["flexure"]["minimum_steel_area_mm2"], "mm2", "CALCULATED"],
            ["As provided", r["flexure"]["provided_steel_area_mm2"], "mm2", r["detailing"]["bottom_reinforcement"]],
            ["MRd", r["flexure"]["moment_resistance_knm"], "kNm", "PASS" if r["flexure"]["utilization"] <= 1 else "FAIL"],
            ["Utilization", r["flexure"]["utilization"], "ratio", "<= 1.00"],
        ]
        shear = [
            ["SHEAR DESIGN"], [STATUS_LABEL], [],
            ["Parameter", "Value", "Unit", "Check"],
            ["VEd", r["shear"]["design_shear_kn"], "kN", "INPUT"],
            ["VRdc", r["shear"]["concrete_shear_resistance_kn"], "kN", "CALCULATED"],
            ["VRd provided", r["shear"]["governing_shear_resistance_kn"], "kN", r["detailing"]["stirrups"]],
            ["Utilization", r["shear"]["utilization"], "ratio", "<= 1.00"],
        ]
        sls = [
            ["SERVICEABILITY"], [STATUS_LABEL], [],
            ["Parameter", "Value", "Unit", "Check"],
            ["Deflection", r["serviceability"]["estimated_deflection_mm"], "mm", f"limit {r['serviceability']['deflection_limit_mm']} mm"],
            ["Deflection utilization", r["serviceability"]["deflection_utilization"], "ratio", "<= 1.00"],
            ["Crack width", r["serviceability"]["estimated_crack_width_mm"], "mm", f"limit {r['serviceability']['crack_width_limit_mm']} mm"],
            ["Crack utilization", r["serviceability"]["crack_width_utilization"], "ratio", "<= 1.00"],
        ]
        details = [
            ["DETAILING"], [STATUS_LABEL], [],
            ["Item", "Selection", "Value", "Unit"],
            ["Bottom reinforcement", r["detailing"]["bottom_reinforcement"], r["flexure"]["provided_steel_area_mm2"], "mm2"],
            ["Top hanger", r["detailing"]["top_hanger_reinforcement"], "", ""],
            ["Stirrups", r["detailing"]["stirrups"], r["shear"]["provided_asw_per_s_mm2_per_mm"], "mm2/mm"],
            ["Anchorage length", "lb,design", r["detailing"]["design_anchorage_length_mm"], "mm"],
        ]
        check_rows = [["DESIGN CHECKS"], [STATUS_LABEL], [], ["Check ID", "Topic", "Passed", "Evidence"]]
        check_rows.extend([[c["check_id"], c["topic"], c["passed"], c["evidence"]] for c in r["checks"]])
        station_rows = [["ULS STATION RESULTS"], [STATUS_LABEL], [], ["x", "Shear", "Moment", "Combination"]]
        station_rows.extend([[row["x_m"], row["shear_kn"], row["moment_knm"], "ULS_STR"] for row in r["stations"]["ULS_STR"]])
        limits = [["LIMITATIONS"], [STATUS_LABEL], [], ["ID", "Limitation"]]
        limits.extend([[index, item] for index, item in enumerate(r["limitations"], start=1)])
        return [
            ("Dashboard", dashboard), ("Inputs", inputs), ("Loads", loads),
            ("Analysis", analysis), ("Flexure", flexure), ("Shear", shear),
            ("Serviceability", sls), ("Detailing", details), ("Stations", station_rows),
            ("QA", check_rows), ("Limitations", limits),
        ]

    def _combination(self, combination_id: str) -> dict[str, Any]:
        combo = next(item for item in self.result["load_combinations"] if item["combination_id"] == combination_id)
        # Rebuild point-load list for workbook formulas only.
        points = []
        for point in self.result["loads"]["point_loads"]:
            factor = 1.5 if combination_id == "ULS_STR" and point["category"] != "permanent" else (1.35 if combination_id == "ULS_STR" else (point["psi2"] if combination_id == "SLS_QUASI_PERMANENT" else 1.0))
            points.append({"load_kn": point["characteristic_kn"] * factor})
        return {"udl_kn_m": combo["udl_kn_m"], "point_loads": points}

    @staticmethod
    def _cell_ref(row: int, col: int) -> str:
        letters = ""
        n = col
        while n:
            n, remainder = divmod(n - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row}"

    def _xlsx_worksheet(self, rows: list[list[Any]]) -> str:
        max_cols = max((len(row) for row in rows), default=1)
        parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">', '<sheetViews><sheetView workbookViewId="0"><pane ySplit="4" topLeftCell="A5" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>', '<cols>']
        widths = [24, 32, 18, 48, 18, 18]
        for i in range(1, max_cols + 1):
            width = widths[i - 1] if i <= len(widths) else 18
            parts.append(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>')
        parts.append('</cols><sheetData>')
        for r_index, row in enumerate(rows, start=1):
            height = 28 if r_index == 1 else (24 if r_index in (2, 4) else 19)
            parts.append(f'<row r="{r_index}" ht="{height}" customHeight="1">')
            for c_index, value in enumerate(row, start=1):
                ref = self._cell_ref(r_index, c_index)
                style = 1 if r_index == 1 else 2 if r_index == 2 else 3 if r_index == 4 else 7 if isinstance(value, (int, float)) else 10
                if isinstance(value, dict) and "formula" in value:
                    parts.append(f'<c r="{ref}" s="7"><f>{escape(str(value["formula"]))}</f><v>{value["value"]}</v></c>')
                elif isinstance(value, bool):
                    style = 8 if value else 9
                    parts.append(f'<c r="{ref}" s="{style}" t="b"><v>{1 if value else 0}</v></c>')
                elif isinstance(value, (int, float)):
                    parts.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
                elif value is not None:
                    parts.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
            parts.append('</row>')
        parts.append('</sheetData>')
        if max_cols > 1:
            parts.append(f'<mergeCells count="2"><mergeCell ref="A1:{self._cell_ref(1,max_cols)}"/><mergeCell ref="A2:{self._cell_ref(2,max_cols)}"/></mergeCells>')
        parts.append('<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.2" footer="0.2"/><pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/></worksheet>')
        return ''.join(parts)

    @staticmethod
    def _xlsx_styles() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="5"><font><sz val="10"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="16"/><name val="Aptos Display"/></font><font><b/><color rgb="FF0F172A"/><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Aptos"/></font><font><color rgb="FF334155"/><sz val="10"/><name val="Aptos"/></font></fonts><fills count="7"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF17324D"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFE9A8"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1D4ED8"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDCFCE7"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFC7CE"/></patternFill></fill></fills><borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="11"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/><xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/><xf numFmtId="0" fontId="3" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"/><xf numFmtId="2" fontId="4" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="5" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''

    @staticmethod
    def _xlsx_content_types(count: int) -> str:
        sheets = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, count+1))
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>{sheets}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'''

    @staticmethod
    def _xlsx_root_rels() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'''

    @staticmethod
    def _xlsx_workbook(names: list[str]) -> str:
        sheets = ''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(names, start=1))
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="14000"/></bookViews><sheets>{sheets}</sheets><calcPr calcId="191029" calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/></workbook>'''

    @staticmethod
    def _xlsx_workbook_rels(count: int) -> str:
        rels = ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, count+1))
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}<Relationship Id="rId{count+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''

    @staticmethod
    def _xlsx_core_properties() -> str:
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>Project Phoenix Reinforced Concrete Beam Design</dc:title><dc:creator>Project Phoenix</dc:creator><cp:lastModifiedBy>Project Phoenix</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">2026-07-28T00:00:00Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">2026-07-28T00:00:00Z</dcterms:modified></cp:coreProperties>'''

    @staticmethod
    def _xlsx_app_properties(names: list[str]) -> str:
        titles = ''.join(f'<vt:lpstr>{escape(name)}</vt:lpstr>' for name in names)
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Project Phoenix</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>{len(names)}</vt:i4></vt:variant></vt:vector></HeadingPairs><TitlesOfParts><vt:vector size="{len(names)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts><Company>A. Brewster Architects.sr</Company><AppVersion>1.0</AppVersion></Properties>'''

    @staticmethod
    def _canonical_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = 20
        info.external_attr = 0o100644 << 16
        info.extra = b""
        info.comment = b""
        return info

    @classmethod
    def _writestr(cls, archive: zipfile.ZipFile, name: str, data: str | bytes) -> None:
        archive.writestr(cls._canonical_info(name), data.encode("utf-8") if isinstance(data, str) else data)

    @staticmethod
    def _write_checksums(paths: Mapping[str, Path], destination: Path) -> Path:
        lines = [
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
            for key, path in sorted(paths.items())
            if key not in {"checksums", "issue_package"}
        ]
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return destination

    @classmethod
    def _write_issue_zip(cls, paths: Mapping[str, Path], destination: Path) -> Path:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            for key, source in sorted(paths.items()):
                if key == "issue_package":
                    continue
                archive.writestr(cls._canonical_info(source.name), source.read_bytes())
        return destination
