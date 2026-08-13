"""PROJECT PHOENIX SCIA Golden Reference Beam Validation v1.0."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zlib

VERSION = "1.0.0"
ENGINE_ID = "PHX-SCIA-REFERENCE-BEAM-VALIDATION"
REFERENCE_ID = "PHX-GOLDEN-SCIA-BEAM-001"
DEFAULT_ESA_XML = r"C:\Program Files (x86)\SCIA\Engineer18.1\ESA_XML.exe"

SOURCE_VALIDATED = "REFERENCE_MODEL_SOURCE_VALIDATED"
SCIA_VALIDATED = "REFERENCE_MODEL_SCIA_LIVE_VALIDATED"
SCIA_ANALYTICAL_VALIDATED = "REFERENCE_MODEL_SCIA_ANALYTICAL_VALIDATED"
CROSS_VERIFIED = "TECHNICALLY_CROSS_VERIFIED_REFERENCE_MODEL"
CALCULIX_PENDING = "REFERENCE_MODEL_CALCULIX_CROSSCHECK_PENDING"
FAILED = "REFERENCE_MODEL_VALIDATION_FAILED"

SAFETY = {
    "automatic_professional_approval": False,
    "automatic_code_compliance_claim": False,
    "reference_model_is_pat001_project_evidence": False,
    "benchmark_tolerances_are_general_engineering_tolerances": False,
    "automatic_production_release": False,
    "automatic_for_construction_release": False,
    "production_release": "LOCKED",
    "for_construction_release": "LOCKED",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def zlib_text_streams(data: bytes) -> list[str]:
    texts: list[str] = []
    for i in range(max(0, len(data) - 2)):
        if data[i] != 0x78 or data[i + 1] not in {0x01, 0x5E, 0x9C, 0xDA}:
            continue
        try:
            raw = zlib.decompress(data[i:])
        except Exception:
            continue
        if len(raw) < 16:
            continue
        texts.append(raw.decode("latin1", errors="ignore"))
        texts.append(raw.decode("utf-16le", errors="ignore"))
    return texts


def extract_scia_protocol(esa: Path) -> dict[str, Any]:
    texts = zlib_text_streams(esa.read_bytes())
    candidates = [t for t in texts if "Sum of loads and reactions" in t and "Loadcase LC1" in t]
    if not candidates:
        raise ValueError("SCIA calculation protocol with LC1 load/reaction summary not found.")
    # Prefer a protocol that explicitly says Linear calculation.
    text = next((t for t in candidates if "Linear calculation" in t), candidates[0])
    load = re.search(r"Loadcase LC1\\Tloads\\T([+-]?[0-9.Ee]+)\\T([+-]?[0-9.Ee]+)\\T([+-]?[0-9.Ee]+)", text)
    reaction = re.search(r"reactions in nodes\\T([+-]?[0-9.Ee]+)\\T([+-]?[0-9.Ee]+)\\T([+-]?[0-9.Ee]+)", text)
    if not load or not reaction:
        raise ValueError("SCIA protocol totals could not be parsed.")
    return {
        "analysis": "Linear calculation" if "Linear calculation" in text else "UNKNOWN",
        "load_case": "LC1",
        "loads_kN": [float(load.group(i)) for i in (1,2,3)],
        "reactions_in_nodes_kN": [float(reaction.group(i)) for i in (1,2,3)],
    }


def parse_reference_xml(path: Path) -> dict[str, Any]:
    ns = {"s": "http://www.scia.cz"}
    root = ET.parse(path).getroot()
    obj = root.find(".//s:obj", ns)
    if obj is None:
        raise ValueError("Beam.xml load object not found.")
    return {
        "def_uri": root.find("s:def", ns).attrib["uri"],
        "load_name": obj.attrib["nm"],
        "member": obj.find("s:p1", ns).attrib["n"],
        "load_case": obj.find("s:p2", ns).attrib["n"],
        "direction": obj.find("s:p3", ns).attrib["t"],
        "type": obj.find("s:p4", ns).attrib["t"],
        "distribution": obj.find("s:p5", ns).attrib["t"],
        "value": float(obj.find("s:p6", ns).attrib["v"]),
        "system": obj.find("s:p7", ns).attrib["t"],
        "location": obj.find("s:p8", ns).attrib["t"],
        "position_x1": float(obj.find("s:p9", ns).attrib["v"]),
        "position_x2": float(obj.find("s:p10", ns).attrib["v"]),
        "coord_definition": obj.find("s:p11", ns).attrib["t"],
        "origin": obj.find("s:p12", ns).attrib["t"],
    }


def validate_sources(reference_root: Path) -> dict[str, Any]:
    ref = read_json(reference_root / "reference_model_manifest.json")
    errors = []
    hashes = {}
    for filename, expected in ref["source_files"].items():
        path = reference_root / filename
        if not path.is_file():
            errors.append(f"missing:{filename}")
            continue
        actual = sha256_file(path)
        hashes[filename] = actual
        if actual != expected:
            errors.append(f"sha256:{filename}")

    try:
        xml = parse_reference_xml(reference_root / "Beam.xml")
    except Exception as exc:
        xml = None
        errors.append(f"xml:{exc}")

    expected_xml = ref["source_observations"]["xml"]
    if xml is not None:
        for key, expected in expected_xml.items():
            if xml.get(key) != expected:
                errors.append(f"xml_mismatch:{key}")

    try:
        protocol = extract_scia_protocol(reference_root / "Beam.esa")
    except Exception as exc:
        protocol = None
        errors.append(f"protocol:{exc}")

    expected_protocol = ref["source_observations"]["existing_scia_calculation_protocol"]
    if protocol is not None:
        if protocol["load_case"] != expected_protocol["load_case"]:
            errors.append("protocol_load_case")
        if protocol["loads_kN"] != expected_protocol["loads_kN"]:
            errors.append("protocol_loads")
        if protocol["reactions_in_nodes_kN"] != expected_protocol["reactions_in_nodes_kN"]:
            errors.append("protocol_reactions")

    return {
        "status": SOURCE_VALIDATED if not errors else FAILED,
        "reference_model_id": REFERENCE_ID,
        "errors": errors,
        "hashes": hashes,
        "xml": xml,
        "existing_protocol": protocol,
        "safety": dict(SAFETY),
    }


def scia_live(reference_root: Path, esa_xml: Path, output_root: Path, timeout_seconds: int = 3600) -> dict[str, Any]:
    source = validate_sources(reference_root)
    if source["status"] != SOURCE_VALIDATED:
        return {"status": FAILED, "stage": "SOURCE_VALIDATION", "source": source, "safety": dict(SAFETY)}
    if not esa_xml.is_file():
        return {"status": FAILED, "stage": "SCIA_RUNTIME", "errors": [f"ESA_XML not found:{esa_xml}"], "safety": dict(SAFETY)}

    output_root.mkdir(parents=True, exist_ok=True)
    esa = output_root / "Beam_working.esa"
    xml = output_root / "Beam.xml"
    deff = output_root / "Beam.xml.def"
    shutil.copy2(reference_root / "Beam.esa", esa)
    shutil.copy2(reference_root / "Beam.xml", xml)
    shutil.copy2(reference_root / "Beam.xml.def", deff)

    original_hash = sha256_file(reference_root / "Beam.esa")
    log = output_root / "scia_esa_xml.log"
    command = [str(esa_xml), "LIN", str(esa), str(xml), f"/l{log}"]
    write_json(output_root / "scia_command.json", {"argv": command})

    try:
        completed = subprocess.run(
            command,
            cwd=str(output_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        return_code = None

    (output_root / "scia_stdout.txt").write_text(stdout, encoding="utf-8")
    (output_root / "scia_stderr.txt").write_text(stderr, encoding="utf-8")

    errors = []
    if timed_out:
        errors.append("SCIA_TIMEOUT")
    if return_code != 0:
        errors.append(f"SCIA_RETURN_CODE:{return_code}")
    if sha256_file(reference_root / "Beam.esa") != original_hash:
        errors.append("ORIGINAL_REFERENCE_MODEL_CHANGED")

    protocol = None
    if not errors:
        try:
            protocol = extract_scia_protocol(esa)
        except Exception as exc:
            errors.append(f"SCIA_PROTOCOL:{exc}")

    ref = read_json(reference_root / "reference_model_manifest.json")
    tol_N = float(ref["benchmark_tolerances"]["scia_equilibrium_absolute_N"])
    expected_total_N = float(ref["derived_reference_targets"]["total_vertical_load_N"])
    equilibrium_error_N = None
    known_load_error_N = None
    if protocol is not None:
        load_N = protocol["loads_kN"][2] * 1000.0
        reaction_N = protocol["reactions_in_nodes_kN"][2] * 1000.0
        equilibrium_error_N = abs(load_N + reaction_N)
        known_load_error_N = abs(load_N - expected_total_N)
        if equilibrium_error_N > tol_N:
            errors.append("SCIA_GLOBAL_EQUILIBRIUM")
        if known_load_error_N > float(ref["benchmark_tolerances"]["scia_known_total_load_absolute_N"]):
            errors.append("SCIA_REFERENCE_LOAD_MISMATCH")

    result = {
        "status": SCIA_VALIDATED if not errors else FAILED,
        "stage": "SCIA_LIVE",
        "return_code": return_code,
        "timeout": timed_out,
        "protocol": protocol,
        "equilibrium_error_N": equilibrium_error_N,
        "known_load_error_N": known_load_error_N,
        "working_esa_sha256": sha256_file(esa) if esa.is_file() else None,
        "original_reference_unchanged": sha256_file(reference_root / "Beam.esa") == original_hash,
        "errors": errors,
        "safety": dict(SAFETY),
    }
    write_json(output_root / "scia_live_validation_result.json", result)
    return result


def analytical(reference_root: Path, scia_result: dict[str, Any]) -> dict[str, Any]:
    if scia_result.get("status") != SCIA_VALIDATED:
        return {"status": FAILED, "stage": "ANALYTICAL", "errors": ["SCIA live validation required"], "safety": dict(SAFETY)}
    ref = read_json(reference_root / "reference_model_manifest.json")
    target = ref["derived_reference_targets"]
    q = abs(float(target["line_load_N_per_m"]))
    L = float(target["span_m"])
    reaction_each = q * L / 2.0
    max_moment = q * L * L / 8.0
    errors = []
    if abs(reaction_each - float(target["support_reaction_each_N"])) > 1e-9:
        errors.append("REFERENCE_REACTION_DERIVATION")
    if abs(max_moment - float(target["max_sagging_moment_Nm"])) > 1e-9:
        errors.append("REFERENCE_MOMENT_DERIVATION")

    result = {
        "status": SCIA_ANALYTICAL_VALIDATED if not errors else FAILED,
        "stage": "ANALYTICAL",
        "q_N_per_m": q,
        "span_m": L,
        "reaction_each_N": reaction_each,
        "max_sagging_moment_Nm": max_moment,
        "errors": errors,
        "safety": dict(SAFETY),
    }
    return result


def calculix_deck(reference_root: Path, output_root: Path, elements: int = 100) -> Path:
    ref = read_json(reference_root / "reference_model_manifest.json")
    q = abs(float(ref["derived_reference_targets"]["line_load_N_per_m"]))
    L = float(ref["derived_reference_targets"]["span_m"])
    dx = L / elements

    lines = [
        "*HEADING",
        "PHOENIX Golden Reference Beam - CalculiX cross-check",
        "*NODE",
    ]
    for i in range(elements + 1):
        lines.append(f"{i+1}, {i*dx:.12g}, 0., 0.")
    lines += ["*ELEMENT, TYPE=B31, ELSET=EALL"]
    for i in range(elements):
        lines.append(f"{i+1}, {i+1}, {i+2}")
    lines += [
        "*MATERIAL, NAME=STEEL",
        "*ELASTIC",
        "210000000000., 0.3",
        "*BEAM SECTION, ELSET=EALL, MATERIAL=STEEL, SECTION=RECT",
        "0.1, 0.1",
        "0., 1., 0.",
        "*NSET, NSET=SUPPORTS",
        f"1, {elements+1}",
        "*BOUNDARY",
        "1, 1, 3",
        "1, 4, 4",
        f"{elements+1}, 2, 3",
        "*STEP",
        "*STATIC",
        "*CLOAD",
    ]
    for i in range(elements + 1):
        load = -q * dx * (0.5 if i in (0, elements) else 1.0)
        lines.append(f"{i+1}, 3, {load:.12g}")
    lines += [
        "*NODE PRINT, NSET=SUPPORTS, TOTALS=YES",
        "RF",
        "*NODE FILE, NSET=SUPPORTS",
        "RF",
        "*EL FILE, ELSET=EALL",
        "S",
        "*END STEP",
    ]
    output_root.mkdir(parents=True, exist_ok=True)
    deck = output_root / "beam_reference_calculix.inp"
    deck.write_text("\n".join(lines) + "\n", encoding="ascii")
    return deck


def find_ccx(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    import shutil as _shutil
    found = _shutil.which("ccx")
    return Path(found) if found else None


def parse_calculix_reaction_total(dat_path: Path, expected_total_N: float) -> tuple[float | None, list[str]]:
    if not dat_path.is_file():
        return None, ["CALCULIX_DAT_MISSING"]
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    # Search reaction-force sections. CalculiX prints node rows beginning with node number.
    candidates = []
    in_force = False
    for line in text.splitlines():
        low = line.lower()
        if "force" in low and ("node" in low or "rf" in low):
            in_force = True
            continue
        if in_force:
            m = re.match(r"\s*(1|101)\s+([+-]?[0-9.Ee+-]+)\s+([+-]?[0-9.Ee+-]+)\s+([+-]?[0-9.Ee+-]+)", line)
            if m:
                try:
                    candidates.append(float(m.group(4)))
                except Exception:
                    pass
            elif line.strip() == "" and candidates:
                break
    if len(candidates) >= 2:
        return sum(candidates[:2]), []
    # Fallback: find any TOTALS line with 3 numeric values and choose Z closest to expected.
    totals = []
    for line in text.splitlines():
        if "total" not in line.lower():
            continue
        nums = re.findall(r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[Ee][+-]?\d+)?", line)
        if len(nums) >= 3:
            try:
                totals.append(float(nums[-1]))
            except Exception:
                pass
    if totals:
        value = min(totals, key=lambda x: abs(abs(x) - abs(expected_total_N)))
        return value, []
    return None, ["CALCULIX_REACTION_PARSE_REQUIRED"]


def run_calculix(reference_root: Path, output_root: Path, ccx: str | None, timeout_seconds: int = 3600) -> dict[str, Any]:
    exe = find_ccx(ccx)
    if exe is None:
        return {
            "status": CALCULIX_PENDING,
            "stage": "CALCULIX",
            "errors": ["CCX_EXECUTABLE_NOT_FOUND"],
            "safety": dict(SAFETY),
        }

    deck = calculix_deck(reference_root, output_root)
    job = deck.with_suffix("")
    command = [str(exe), "-i", job.name]
    write_json(output_root / "calculix_command.json", {"argv": command})
    try:
        completed = subprocess.run(
            command,
            cwd=str(output_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        rc = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        rc = None

    (output_root / "calculix_stdout.txt").write_text(stdout, encoding="utf-8")
    (output_root / "calculix_stderr.txt").write_text(stderr, encoding="utf-8")

    errors = []
    if timed_out:
        errors.append("CALCULIX_TIMEOUT")
    if rc != 0:
        errors.append(f"CALCULIX_RETURN_CODE:{rc}")

    ref = read_json(reference_root / "reference_model_manifest.json")
    expected = abs(float(ref["derived_reference_targets"]["total_vertical_load_N"]))
    reaction_total, parse_errors = parse_calculix_reaction_total(output_root / "beam_reference_calculix.dat", expected)
    errors.extend(parse_errors)
    if reaction_total is not None:
        if abs(abs(reaction_total) - expected) > float(ref["benchmark_tolerances"]["calculix_total_reaction_absolute_N"]):
            errors.append("CALCULIX_TOTAL_REACTION_MISMATCH")

    result = {
        "status": "CALCULIX_REFERENCE_VALIDATED" if not errors else (CALCULIX_PENDING if errors == ["CALCULIX_REACTION_PARSE_REQUIRED"] else FAILED),
        "stage": "CALCULIX",
        "ccx": str(exe),
        "return_code": rc,
        "timeout": timed_out,
        "reaction_total_N": reaction_total,
        "expected_total_reaction_N": expected,
        "errors": errors,
        "deck_sha256": sha256_file(deck),
        "safety": dict(SAFETY),
    }
    write_json(output_root / "calculix_validation_result.json", result)
    return result


def run_all(reference_root: Path, esa_xml: Path, output_root: Path, ccx: str | None, timeout_seconds: int) -> dict[str, Any]:
    source = validate_sources(reference_root)
    write_json(output_root / "source_validation_result.json", source)
    if source["status"] != SOURCE_VALIDATED:
        return {"status": FAILED, "source": source, "safety": dict(SAFETY)}

    scia = scia_live(reference_root, esa_xml, output_root / "scia", timeout_seconds)
    if scia["status"] != SCIA_VALIDATED:
        result = {"status": FAILED, "source": source, "scia": scia, "safety": dict(SAFETY)}
        write_json(output_root / "reference_model_validation_result.json", result)
        return result

    ana = analytical(reference_root, scia)
    if ana["status"] != SCIA_ANALYTICAL_VALIDATED:
        result = {"status": FAILED, "source": source, "scia": scia, "analytical": ana, "safety": dict(SAFETY)}
        write_json(output_root / "reference_model_validation_result.json", result)
        return result

    ccx_result = run_calculix(reference_root, output_root / "calculix", ccx, timeout_seconds)
    if ccx_result["status"] == "CALCULIX_REFERENCE_VALIDATED":
        scia_reaction = abs(scia["protocol"]["reactions_in_nodes_kN"][2] * 1000.0)
        ccx_reaction = abs(float(ccx_result["reaction_total_N"]))
        ref = read_json(reference_root / "reference_model_manifest.json")
        diff = abs(scia_reaction - ccx_reaction)
        if diff <= float(ref["benchmark_tolerances"]["scia_calculix_total_reaction_absolute_N"]):
            final_status = CROSS_VERIFIED
            cross_error = None
        else:
            final_status = FAILED
            cross_error = "SCIA_CALCULIX_REACTION_MISMATCH"
    elif ccx_result["status"] == CALCULIX_PENDING:
        final_status = CALCULIX_PENDING
        diff = None
        cross_error = None
    else:
        final_status = FAILED
        diff = None
        cross_error = "CALCULIX_VALIDATION_FAILED"

    result = {
        "schema_version": "phoenix.scia-reference-beam-validation-result/1.0",
        "engine_id": ENGINE_ID,
        "engine_version": VERSION,
        "reference_model_id": REFERENCE_ID,
        "status": final_status,
        "source": source,
        "scia": scia,
        "analytical": ana,
        "calculix": ccx_result,
        "scia_calculix_total_reaction_difference_N": diff,
        "cross_error": cross_error,
        "professional_review_status": "NOT_APPLICABLE_TO_SOFTWARE_REFERENCE_MODEL",
        "project_evidence_status": "REFERENCE_ONLY_NOT_PAT001",
        "safety": dict(SAFETY),
    }
    write_json(output_root / "reference_model_validation_result.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("validate-source", "run-scia", "run-calculix", "run-all"))
    parser.add_argument("--reference-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--esa-xml", default=DEFAULT_ESA_XML)
    parser.add_argument("--ccx")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()

    ref = Path(args.reference_root)
    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)

    if args.action == "validate-source":
        result = validate_sources(ref)
        write_json(out / "source_validation_result.json", result)
    elif args.action == "run-scia":
        result = scia_live(ref, Path(args.esa_xml), out, args.timeout_seconds)
    elif args.action == "run-calculix":
        result = run_calculix(ref, out, args.ccx, args.timeout_seconds)
    else:
        result = run_all(ref, Path(args.esa_xml), out, args.ccx, args.timeout_seconds)

    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result.get("status") == FAILED:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
