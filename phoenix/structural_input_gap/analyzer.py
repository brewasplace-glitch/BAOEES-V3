#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple


ENGINE_VERSION = "1.0.0"
PROJECT_ID = "PHX-RP-ANIJSTRAAT-616"
PRELIMINARY_PASS = "PASS_PRELIMINARY_STRUCTURAL_DERIVATION_AUTHORIZED"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u00d8", "Ø").replace("\u2300", "Ø")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pdf_text(path: Path) -> Tuple[str, int, Dict[str, Any]]:
    errors: List[str] = []

    try:
        import pdfplumber  # type: ignore
        pages = []
        with pdfplumber.open(str(path)) as pdf:
            for p in pdf.pages:
                pages.append(p.extract_text(x_tolerance=2, y_tolerance=3) or "")
            return "\n".join(pages), len(pdf.pages), {
                "backend": "pdfplumber",
                "backend_version": getattr(pdfplumber, "__version__", "unknown"),
                "license": "MIT",
                "fallback_used": False,
            }
    except Exception as exc:
        errors.append(f"pdfplumber: {exc}")

    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(str(path))
        pages = [(p.extract_text() or "") for p in reader.pages]
        return "\n".join(pages), len(reader.pages), {
            "backend": "pypdf",
            "backend_version": getattr(pypdf, "__version__", "unknown"),
            "license": "BSD-style upstream license",
            "fallback_used": True,
            "primary_error": errors[0] if errors else None,
        }
    except Exception as exc:
        errors.append(f"pypdf: {exc}")

    raise RuntimeError(
        "No usable PDF parser. Phoenix tried pdfplumber then pypdf. "
        + " | ".join(errors)
    )


def _has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None


def _fact(fid: str, label: str, value: Any, authority: str, confidence: str = "HIGH") -> Dict[str, Any]:
    return {
        "id": fid,
        "label": label,
        "value": value,
        "authority": authority,
        "confidence": confidence,
    }


def analyze(pdf: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    raw_text, page_count, backend = extract_pdf_text(pdf)
    text = _norm(raw_text)
    upper = text.upper()

    required_sheet_markers = {
        "floor_plan": r"PLATTEGROND",
        "foundation_plan": r"FUNDERING",
        "roof_plan": r"KAPPLAN",
        "sections": r"DOORSNEDEN",
        "details": r"DETAILS",
        "site_plan": r"SITUATIE",
    }
    sheets = {name: _has(upper, pattern) for name, pattern in required_sheet_markers.items()}

    if page_count < int(config["source_contract"]["minimum_pages"]):
        raise RuntimeError(f"Source PDF has only {page_count} pages; expected a complete design set.")
    missing_sheets = [k for k, v in sheets.items() if not v]
    if missing_sheets:
        raise RuntimeError("Required source sheets not proven in PDF: " + ", ".join(missing_sheets))

    facts: List[Dict[str, Any]] = []
    facts.append(_fact("SRC-001", "Source document", pdf.name, "PDF"))
    facts.append(_fact("SRC-002", "PDF pages", page_count, "PDF"))
    facts.append(_fact("SRC-003", "Project identity", "WOONHUIS / ANIJSTRAAT #616", "PDF"))
    facts.append(_fact("SRC-004", "Complete sheet set markers", sheets, "PDF"))

    # Structural proposal facts are SOURCE INPUT ONLY, never accepted design proof.
    source_checks = [
        ("STR-FOUND-001", "Proposed strip footing", r"strook\s*fundering\s*800\s*x\s*200|strook\s*800\s*x\s*200", "800 x 200 mm"),
        ("STR-FOUND-002", "Proposed pad footing", r"schotel(?:fundering)?\s*1000\s*x\s*1000\s*x\s*200", "1000 x 1000 x 200 mm"),
        ("STR-COL-001", "Proposed column", r"kolom\s*:?\s*200\s*x\s*200", "200 x 200 mm"),
        ("STR-FLOOR-001", "Proposed concrete floor slab", r"betonvloer\s*150\s*mm", "150 mm"),
        ("STR-BEAM-001", "Proposed floor beam", r"vloerbalk\s*150\s*x\s*250", "150 x 250 mm"),
        ("STR-RIB-001", "Proposed T-rib", r"T-?rib\s*150\s*x\s*410", "150 x 410 mm"),
        ("STR-BEAM-002", "Proposed terrace beam", r"ringbalk\s*terras\s*200\s*x\s*400", "200 x 400 mm"),
        ("STR-ROOF-001", "Proposed timber purlins", r"gording(?:en)?\s*:?\s*2[\"”]\s*x\s*3[\"”]", '2" x 3"'),
        ("STR-ROOF-002", "Proposed timber rafters", r"kapbeen\s*:?\s*2[\"”]\s*x\s*4[\"”]", '2" x 4"'),
        ("STR-ROOF-003", "Proposed timber ties", r"trekbalk\s*:?\s*2[\"”]\s*x\s*4[\"”]", '2" x 4"'),
    ]
    proposal_presence = {}
    for fid, label, pat, value in source_checks:
        ok = _has(text, pat)
        proposal_presence[fid] = ok
        if ok:
            facts.append(_fact(fid, label, value, "PDF / UNVERIFIED_PROPOSAL"))

    user = config["user_authority"]
    tank_volume = float(user["durotank"]["volume_m3"])
    water_unit_weight = float(config["calculation_constants"]["water_unit_weight_kN_m3"])
    tank_water_weight = round(tank_volume * water_unit_weight, 3)
    facts.append(_fact("USR-TANK-001", "Durotank volume", tank_volume, "USER"))
    facts.append(_fact("USR-TANK-002", "Durotank position", "ELEVATED", "USER"))
    facts.append(_fact("DER-TANK-001", "Stored-water characteristic weight", tank_water_weight, "DERIVED_FROM_USER_INPUT", "HIGH"))

    conflicts: List[Dict[str, Any]] = []
    if _has(text, r"ringbalk\s*:?\s*100\s*x\s*200") and _has(text, r"ringbalk\s*:?\s*100\s*x\s*150"):
        conflicts.append({
            "id": "CONFLICT-RINGBEAM-001",
            "topic": "ring_beam_section",
            "values": ["100 x 200 mm", "100 x 150 mm"],
            "disposition": "NEXT_STAGE_MUST_SELECT_AUTHORITATIVE_SECTION_BY_STRUCTURAL_DESIGN; DO_NOT_SILENTLY_ACCEPT_EITHER",
        })
    if _has(text, r"4[\"”]\s*metselwerk|metselwerk\s*4[\"”]") and _has(text, r"6[\"”]\s*metselwerk|muren\s*:?\s*6[\"”]"):
        conflicts.append({
            "id": "CONFLICT-MASONRY-001",
            "topic": "masonry_wall_thickness",
            "values": ['4"', '6"'],
            "disposition": "NEXT_STAGE_MUST_CLASSIFY_LOADBEARING_VS_NONLOADBEARING_WALLS",
        })
    if (_has(text, r"binnenplafond.*2700") or _has(text, r"plafond.*2700")) and _has(text, r"plafond\s*\+\s*3430|o\.?k\.?\s*plafond\s*\+\s*3430"):
        conflicts.append({
            "id": "CONFLICT-HEIGHT-001",
            "topic": "ceiling_or_structural_height",
            "values": ["2700 mm architectural ceiling note", "3430 mm section underside ceiling"],
            "disposition": "NEXT_STAGE_MUST_DISTINGUISH FINISH CEILING FROM STRUCTURAL/RINGBEAM HEIGHT",
        })

    assumptions = [
        {
            "id": "ASM-SOIL-001",
            "topic": "geotechnical_model",
            "known": False,
            "user_authority_to_estimate": bool(user["geotechnical"]["phoenix_may_estimate_preliminary"]),
            "preliminary_action": "BUILD_CONSERVATIVE_REGIONAL_SOIL_AND_GROUNDWATER_MODEL_WITH_SENSITIVITY_CASES",
            "confidence": "LOW_UNTIL_SITE_INVESTIGATION",
            "release_blocker": True,
        },
        {
            "id": "ASM-WOOD-001",
            "topic": "timber_species_and_strength_class",
            "known": False,
            "user_authority_to_estimate": bool(user["timber"]["phoenix_may_estimate_preliminary"]),
            "preliminary_action": "SELECT_DOCUMENTED_PRELIMINARY_TIMBER_STRENGTH_CLASS_AND_VERIFY_ALL_ROOF_MEMBERS",
            "confidence": "LOW_TO_MEDIUM_UNTIL_SUPPLY_SPEC_CONFIRMED",
            "release_blocker": True,
        },
        {
            "id": "ASM-CODE-001",
            "topic": "structural_code_basis",
            "known": False,
            "user_authority_to_estimate": True,
            "preliminary_action": "RESEARCH_AND_DOCUMENT_APPLICABLE_SURINAME/PARAMARIBO_CODE_HIERARCHY; MARK ASSUMED_CODE_BASIS",
            "confidence": "MEDIUM_AFTER_RESEARCH; PROFESSIONAL_CONFIRMATION_REQUIRED",
            "release_blocker": True,
        },
        {
            "id": "ASM-TANK-001",
            "topic": "elevated_tank_support_geometry",
            "known": False,
            "user_authority_to_estimate": True,
            "preliminary_action": "DERIVE_PRELIMINARY_SUPPORT_FRAME_GEOMETRY_IF DRAWING DOES NOT PROVE IT; INCLUDE WIND, STABILITY, ANCHORAGE, FOUNDATION",
            "confidence": "MEDIUM_AFTER_GEOMETRY_DERIVATION",
            "release_blocker": True,
        },
    ]

    release_blockers = [
        "SITE_SPECIFIC_GEOTECHNICAL_INVESTIGATION_NOT_AVAILABLE",
        "FINAL_STRUCTURAL_CODE_BASIS_NOT_PROFESSIONALLY_CONFIRMED",
        "TIMBER_SPECIES_STRENGTH_CLASS_NOT_MATERIAL_CERTIFIED",
        "EXACT_ELEVATED_DUROTANK_SUPPORT_GEOMETRY_NOT_YET_PROVEN",
        "PROFESSIONAL_STRUCTURAL_REVIEW_REQUIRED",
    ]

    auto_next = [
        "derive structural topology from architectural geometry",
        "classify loadbearing and non-loadbearing walls",
        "research preliminary code basis for Paramaribo/Suriname",
        "derive dead, imposed, wind and tank actions",
        "create conservative preliminary geotechnical model with sensitivity cases",
        "select preliminary timber strength class and verify roof members",
        "verify all existing proposed concrete/foundation member sizes rather than inherit them",
        "resolve drawing conflicts explicitly",
        "build solver-ready structural model",
    ]

    result = {
        "schema": "PHOENIX_STRUCTURAL_INPUT_GAP_ANALYSIS_1.0",
        "engine_version": ENGINE_VERSION,
        "project_id": PROJECT_ID,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "path": str(pdf),
            "name": pdf.name,
            "sha256": sha256_file(pdf),
            "page_count": page_count,
            "pdf_backend": backend,
        },
        "project_context": config["project_context"],
        "source_facts": facts,
        "proposal_presence": proposal_presence,
        "authority_conflicts": conflicts,
        "assumptions_required": assumptions,
        "release_blockers": release_blockers,
        "blocking_for_preliminary_structural_derivation": [],
        "autonomous_next_actions": auto_next,
        "tank": {
            "volume_m3": tank_volume,
            "elevated": True,
            "water_unit_weight_kN_m3": water_unit_weight,
            "stored_water_weight_kN": tank_water_weight,
            "note": "Tank self-weight and support-frame self-weight are additional and must be derived next.",
        },
        "governance": {
            "existing_structural_dimensions_status": "UNVERIFIED_PROPOSALS_TO_BE_RECALCULATED",
            "preliminary_not_for_construction": True,
            "professional_structural_review_required": True,
            "for_construction_release": "LOCKED",
        },
        "status": PRELIMINARY_PASS,
        "next_stage_contract": {
            "proceed": True,
            "stage": "PHOENIX_4.41_REAL_PROJECT_STRUCTURAL_DERIVATION_AND_LOAD_MODEL",
            "project": "ANIJSTRAAT_616",
            "must_preserve": [
                "source PDF SHA256 evidence",
                "user-authority assumptions",
                "authority conflict log",
                "PRELIMINARY_NOT_FOR_CONSTRUCTION lock",
                "professional structural review lock",
            ],
        },
    }
    return result


def render_markdown(data: Dict[str, Any]) -> str:
    lines = [
        "# PHOENIX 4.41 — Structural Input + Gap Analysis",
        "",
        f"**Project:** {data['project_id']}",
        f"**Status:** `{data['status']}`",
        f"**Source:** `{data['source']['name']}` ({data['source']['page_count']} pages)",
        f"**Source SHA256:** `{data['source']['sha256']}`",
        "",
        "## Decision",
        "",
        "Phoenix has enough information to proceed to **preliminary structural derivation and load modelling**.",
        "For-construction release remains locked.",
        "",
        "## User-authority inputs",
        "",
        f"- No geotechnical investigation available; Phoenix is authorized to create a conservative preliminary estimate.",
        f"- Timber species / strength class unknown; Phoenix is authorized to select a preliminary class and verify the roof.",
        f"- Elevated durotank: **{data['tank']['volume_m3']:.1f} m³**.",
        f"- Stored water characteristic weight: **{data['tank']['stored_water_weight_kN']:.2f} kN** before tank/support self-weight.",
        "",
        "## Drawing conflicts requiring explicit resolution",
        "",
    ]
    if data["authority_conflicts"]:
        for c in data["authority_conflicts"]:
            lines.append(f"- **{c['id']}** — {c['topic']}: {', '.join(c['values'])}")
    else:
        lines.append("- None detected by current rule set.")
    lines += [
        "",
        "## Release blockers (do not block preliminary calculation)",
        "",
    ]
    for b in data["release_blockers"]:
        lines.append(f"- {b}")
    lines += [
        "",
        "## Next stage",
        "",
        f"`{data['next_stage_contract']['stage']}`",
        "",
        "**PRELIMINARY / NOT FOR CONSTRUCTION**",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(data: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "structural_input_gap_analysis.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "structural_input_gap_analysis.md").write_text(
        render_markdown(data), encoding="utf-8"
    )
    (output_dir / "assumptions_log.json").write_text(
        json.dumps(data["assumptions_required"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "authority_conflicts.json").write_text(
        json.dumps(data["authority_conflicts"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "next_stage_contract.json").write_text(
        json.dumps(data["next_stage_contract"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {}
    for p in sorted(output_dir.glob("*")):
        if p.is_file():
            manifest[p.name] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    (output_dir / "evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def verify_output(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == PRELIMINARY_PASS
    assert data["next_stage_contract"]["proceed"] is True
    assert data["governance"]["preliminary_not_for_construction"] is True
    assert data["governance"]["for_construction_release"] == "LOCKED"
    assert data["tank"]["volume_m3"] == 2.0
    assert data["tank"]["elevated"] is True
    assert abs(float(data["tank"]["stored_water_weight_kN"]) - 19.62) < 0.01
    assert data["source"]["page_count"] >= 15
    ids = {x["id"] for x in data["authority_conflicts"]}
    assert "CONFLICT-RINGBEAM-001" in ids
    assert "CONFLICT-MASONRY-001" in ids
    asm = {x["id"]: x for x in data["assumptions_required"]}
    assert asm["ASM-SOIL-001"]["user_authority_to_estimate"] is True
    assert asm["ASM-WOOD-001"]["user_authority_to_estimate"] is True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path)
    ap.add_argument("--config", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--verify-output", type=Path)
    args = ap.parse_args()

    if args.verify_output:
        verify_output(args.verify_output)
        print("PHOENIX_4_41_STRUCTURAL_GAP_OUTPUT_VERIFY=PASS")
        return 0

    if not (args.pdf and args.config and args.output):
        ap.error("--pdf, --config and --output are required")

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    data = analyze(args.pdf, cfg)
    write_outputs(data, args.output)

    print(f"PROJECT_ID={PROJECT_ID}")
    print(f"PDF_BACKEND={data['source']['pdf_backend']['backend']}")
    print(f"PDF_PAGES={data['source']['page_count']}")
    print(f"SOURCE_SHA256={data['source']['sha256']}")
    print(f"TANK_WATER_WEIGHT_KN={data['tank']['stored_water_weight_kN']}")
    print(f"AUTHORITY_CONFLICTS={len(data['authority_conflicts'])}")
    print(f"RELEASE_BLOCKERS={len(data['release_blockers'])}")
    print("PRELIMINARY_NOT_FOR_CONSTRUCTION=TRUE")
    print("PROFESSIONAL_STRUCTURAL_REVIEW_REQUIRED=TRUE")
    print(f"STRUCTURAL_INPUT_GAP_STATUS={data['status']}")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
