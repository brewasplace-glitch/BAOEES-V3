"""PROJECT PHOENIX analytical structural verification expansion v1.0."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import argparse
import json
import math
from pathlib import Path

VERSION = "1.0.0"
ENGINE_ID = "PHX-STRUCTURAL-ANALYTICAL-VERIFICATION"

PASS = "ANALYTICAL_REFERENCE_VALIDATED"
INPUT_REQUIRED = "ANALYTICAL_INPUT_REQUIRED"
SCOPE_NOT_SUPPORTED = "ANALYTICAL_SCOPE_NOT_SUPPORTED"
FAILED = "ANALYTICAL_REFERENCE_FAILED"

SAFETY = {
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "automatic_normative_acceptance_limits": False,
    "automatic_project_scope_inference": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def _positive(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name}: numeric value required")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name}: positive finite value required")
    return value


def simply_supported_beam_udl(q_N_per_m: float, L_m: float) -> dict[str, float]:
    q = _positive("q_N_per_m", q_N_per_m)
    L = _positive("L_m", L_m)
    return {
        "total_load_N": q * L,
        "reaction_each_N": q * L / 2.0,
        "max_moment_Nm": q * L * L / 8.0,
    }


def cantilever_end_point_load(
    P_N: float, L_m: float, E_Pa: float | None = None, I_m4: float | None = None
) -> dict[str, float | None]:
    P = _positive("P_N", P_N)
    L = _positive("L_m", L_m)
    tip = None
    if (E_Pa is None) ^ (I_m4 is None):
        raise ValueError("E_Pa and I_m4 must be supplied together.")
    if E_Pa is not None and I_m4 is not None:
        E = _positive("E_Pa", E_Pa)
        I = _positive("I_m4", I_m4)
        tip = P * L**3 / (3.0 * E * I)
    return {
        "reaction_N": P,
        "fixed_end_moment_Nm": P * L,
        "tip_deflection_m": tip,
    }


def axial_bar(P_N: float, L_m: float, E_Pa: float, A_m2: float) -> dict[str, float]:
    P = _positive("P_N", P_N)
    L = _positive("L_m", L_m)
    E = _positive("E_Pa", E_Pa)
    A = _positive("A_m2", A_m2)
    return {
        "axial_stress_Pa": P / A,
        "elongation_m": P * L / (E * A),
    }


def evaluate(case_type: str, inputs: dict[str, Any]) -> dict[str, Any]:
    kind = str(case_type).strip().upper()
    try:
        if kind == "SIMPLY_SUPPORTED_BEAM_UDL":
            outputs = simply_supported_beam_udl(inputs.get("q_N_per_m"), inputs.get("L_m"))
        elif kind == "CANTILEVER_END_POINT_LOAD":
            outputs = cantilever_end_point_load(
                inputs.get("P_N"), inputs.get("L_m"),
                inputs.get("E_Pa"), inputs.get("I_m4")
            )
        elif kind == "AXIAL_BAR":
            outputs = axial_bar(
                inputs.get("P_N"), inputs.get("L_m"),
                inputs.get("E_Pa"), inputs.get("A_m2")
            )
        else:
            return {
                "status": SCOPE_NOT_SUPPORTED,
                "case_type": kind,
                "supported": [
                    "SIMPLY_SUPPORTED_BEAM_UDL",
                    "CANTILEVER_END_POINT_LOAD",
                    "AXIAL_BAR",
                ],
                "safety": dict(SAFETY),
            }
    except (ValueError, TypeError) as exc:
        return {
            "status": INPUT_REQUIRED,
            "case_type": kind,
            "error": str(exc),
            "safety": dict(SAFETY),
        }
    return {
        "status": PASS,
        "case_type": kind,
        "inputs": inputs,
        "outputs": outputs,
        "safety": dict(SAFETY),
    }


def golden_beam_check() -> dict[str, Any]:
    result = evaluate("SIMPLY_SUPPORTED_BEAM_UDL", {"q_N_per_m": 1000.0, "L_m": 5.0})
    expected = {
        "total_load_N": 5000.0,
        "reaction_each_N": 2500.0,
        "max_moment_Nm": 3125.0,
    }
    errors = {}
    for key, value in expected.items():
        actual = result["outputs"][key]
        if abs(actual - value) > 1e-12:
            errors[key] = {"actual": actual, "expected": value}
    return {
        "status": PASS if not errors else FAILED,
        "reference_model_id": "PHX-GOLDEN-SCIA-BEAM-001",
        "reference_case": "SIMPLY_SUPPORTED_BEAM_UDL",
        "computed": result["outputs"],
        "expected": expected,
        "errors": errors,
        "tolerance_scope": "EXACT_FORMULA_SOFTWARE_TEST_ONLY",
        "safety": dict(SAFETY),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--case-type", required=True)
    ev.add_argument("--input-json", required=True)
    ev.add_argument("--output", required=True)
    gb = sub.add_parser("golden-beam")
    gb.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.action == "evaluate":
        inputs = json.loads(Path(args.input_json).read_text(encoding="utf-8-sig"))
        result = evaluate(args.case_type, inputs)
    else:
        result = golden_beam_check()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["status"] in {FAILED}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
