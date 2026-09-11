#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STATUS = "PASS_PRELIMINARY_STRUCTURAL_DESIGN_CONSOLIDATION_AND_DRAWINGS"
NEXT_STAGE = "PHOENIX_4.41_REAL_PROJECT_3D_STRUCTURAL_MODEL_AND_CALCULATION_REPORT"
ENGINE_VERSION = "1.0.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def section_rect(b_mm: float, h_mm: float) -> Dict[str, float]:
    return {
        "A_mm2": b_mm * h_mm,
        "I_mm4": b_mm * h_mm ** 3 / 12.0,
        "W_mm3": b_mm * h_mm ** 2 / 6.0,
    }


def timber_utilization(span_m: float, b_mm: float, h_mm: float, spacing_m: float,
                       gk_kN_m2: float, qk_kN_m2: float,
                       E_mpa: float, fmk_mpa: float, kmod: float, gamma_m: float,
                       deflection_ratio: float) -> Dict[str, float | str]:
    fmd = kmod * fmk_mpa / gamma_m
    w_uls = (1.35 * gk_kN_m2 + 1.50 * qk_kN_m2) * spacing_m
    w_sls = (gk_kN_m2 + qk_kN_m2) * spacing_m
    L = span_m * 1000.0
    sec = section_rect(b_mm, h_mm)
    stress = w_uls * L ** 2 / 8.0 / sec["W_mm3"]
    delta = 5.0 * w_sls * L ** 4 / (384.0 * E_mpa * sec["I_mm4"])
    limit = L / deflection_ratio
    su = stress / fmd
    du = delta / limit
    return {
        "span_m": span_m,
        "section_mm": [b_mm, h_mm],
        "strength_utilization": round(su, 3),
        "deflection_utilization": round(du, 3),
        "governing_utilization": round(max(su, du), 3),
        "status": "PASS" if max(su, du) <= 1.0 else "FAIL",
    }


def rc_flexure_proxy(b_mm: float, h_mm: float, bottom_bars: int, bar_dia_mm: float,
                     cover_mm: float, fyk_mpa: float, gamma_s: float) -> Dict[str, float]:
    As = bottom_bars * math.pi * bar_dia_mm ** 2 / 4.0
    d = h_mm - cover_mm - bar_dia_mm / 2.0
    z = 0.9 * d
    fyd = fyk_mpa / gamma_s
    mrd = 0.87 * fyd * As * z / 1e6
    return {
        "As_bottom_mm2": round(As, 1),
        "effective_depth_mm": round(d, 1),
        "M_Rd_proxy_kNm": round(mrd, 3),
    }


def svg_text(x: float, y: float, text: str, size: float = 4.0, weight: str = "normal",
             anchor: str = "start") -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" '
        f'font-size="{size:.2f}" font-weight="{weight}" text-anchor="{anchor}">'
        f'{html.escape(str(text))}</text>'
    )


def svg_line(x1: float, y1: float, x2: float, y2: float, width: float = 0.4,
             dash: str | None = None) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="black" stroke-width="{width:.2f}"{extra}/>'


def svg_rect(x: float, y: float, w: float, h: float, width: float = 0.5,
             fill: str = "none", dash: str | None = None) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="black" stroke-width="{width:.2f}"{extra}/>'


def svg_circle(cx: float, cy: float, r: float, width: float = 0.4, fill: str = "none") -> str:
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" stroke="black" stroke-width="{width:.2f}"/>'


def sheet(title: str, subtitle: str, body: Iterable[str]) -> str:
    items = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">',
        '<rect x="5" y="5" width="410" height="287" fill="white" stroke="black" stroke-width="0.7"/>',
        svg_text(12, 15, title, 6.0, "bold"),
        svg_text(12, 22, subtitle, 3.6),
        svg_line(10, 26, 410, 26, 0.5),
    ]
    items.extend(body)
    items.extend([
        svg_line(10, 280, 410, 280, 0.5),
        svg_text(12, 286, "PHOENIX 4.41 • PRELIMINARY / NOT FOR CONSTRUCTION", 3.2, "bold"),
        svg_text(408, 286, "Professional structural review required", 3.0, anchor="end"),
        '</svg>'
    ])
    return "\n".join(items)


def make_s01(design: Dict[str, Any]) -> str:
    body: List[str] = []
    body.append(svg_text(12, 35, "DESIGN BASIS", 4.5, "bold"))
    basis = [
        f"Source PDF SHA256: {design['source_sha256'][:28]}…",
        "Structural status: preliminary; legal Suriname code basis not yet confirmed",
        "Primary executed solver evidence: PyNiteFEA PASS; OpenSees preferred runtime blocked on Windows",
        "Foundation checks: gravity-bearing only; settlement/geotechnical design remains HOLD",
        "Wind: sensitivity only; no confirmed legal design wind parameter",
    ]
    y = 42
    for t in basis:
        body.append(svg_text(15, y, "• " + t, 3.4))
        y += 6

    body.append(svg_text(12, 78, "PRELIMINARY ELEMENT SCHEDULE", 4.5, "bold"))
    headers = ["ID", "Element", "Preliminary consolidated choice", "Status"]
    x = [12, 35, 105, 315]
    for i, h in enumerate(headers):
        body.append(svg_text(x[i], 86, h, 3.3, "bold"))
    body.append(svg_line(12, 89, 408, 89, 0.5))

    y = 96
    for row in design["element_schedule"]:
        vals = [row["id"], row["element"], row["choice"], row["status"]]
        body.append(svg_text(x[0], y, vals[0], 3.0))
        body.append(svg_text(x[1], y, vals[1], 3.0))
        # wrap long choice
        choice = vals[2]
        if len(choice) > 68:
            parts = [choice[:68], choice[68:136], choice[136:]]
        else:
            parts = [choice]
        for j, part in enumerate([p for p in parts if p]):
            body.append(svg_text(x[2], y + j*4, part, 2.8))
        body.append(svg_text(x[3], y, vals[3], 2.8, "bold"))
        y += max(11, 4*len([p for p in parts if p]) + 4)
        body.append(svg_line(12, y-5, 408, y-5, 0.2))

    body.append(svg_text(12, 264, "Release lock:", 3.5, "bold"))
    body.append(svg_text(45, 264, "FOR_CONSTRUCTION_RELEASE = LOCKED", 3.5, "bold"))
    return sheet("S-01 STRUCTURAL DESIGN BASIS + ELEMENT SCHEDULE",
                 "Woonhuis Anijstraat #616 • Phoenix design consolidation", body)


def make_s02(design: Dict[str, Any]) -> str:
    body: List[str] = []
    ox, oy = 42.0, 52.0
    scale = 9.2  # mm on sheet per metre
    W = 18.20 * scale
    H = 14.05 * scale

    body.append(svg_text(12, 35, "PRELIMINARY STRUCTURAL GRID / FOUNDATION ENVELOPE", 4.5, "bold"))
    body.append(svg_rect(ox, oy, W, H, 1.8))
    body.append(svg_text(ox + W/2, oy + H + 12, "800 × 200 mm perimeter strip-footing envelope — gravity bearing PASS / geotech HOLD", 3.0, anchor="middle"))

    gx = design["geometry"]["x_coordinates"]
    gy = design["geometry"]["y_coordinates"]
    xlabels = design["geometry"]["x_axis_labels"]
    ylabels = design["geometry"]["y_axis_labels"]
    xoff = (18.20 - 18.10)/2.0
    yoff = (14.05 - 13.70)/2.0

    for lab, xm in zip(xlabels, gx):
        px = ox + (xoff + xm)*scale
        body.append(svg_line(px, oy-8, px, oy+H+8, 0.25, "3,2"))
        body.append(svg_circle(px, oy-5, 3.2, 0.35))
        body.append(svg_text(px, oy-3.8, lab, 2.8, "bold", "middle"))
    for lab, ym in zip(ylabels, gy):
        py = oy + (yoff + ym)*scale
        body.append(svg_line(ox-8, py, ox+W+8, py, 0.25, "3,2"))
        body.append(svg_circle(ox-5, py, 3.2, 0.35))
        body.append(svg_text(ox-5, py+1.0, lab, 2.5, "bold", "middle"))

    note_x = 250
    body.append(svg_text(note_x, 50, "CONTROL NOTES", 4.0, "bold"))
    notes = [
        "1. Perimeter shown as source-derived structural envelope.",
        "2. Interior loadbearing wall / column vectors are NOT silently invented.",
        "3. Source foundation sheet is exported as reference snapshot where renderer is available.",
        "4. 1000×1000×200 pad footing: modeled gravity bearing PASS; bending/punching HOLD.",
        "5. Ground-bearing slab: 150 mm source geometry retained; reinforcement remains source/provisional.",
        "6. Tank foundation: 1×1 m gravity envelope passes modeled soil cases; overturning/wind HOLD.",
    ]
    y = 59
    for n in notes:
        body.append(svg_text(note_x, y, n, 3.0))
        y += 7

    body.append(svg_rect(250, 110, 65, 65, 0.9))
    body.append(svg_text(282.5, 143, "1000×1000", 3.2, "bold", "middle"))
    body.append(svg_text(282.5, 151, "PAD • 200 THK", 3.0, anchor="middle"))
    body.append(svg_text(250, 186, "PAD DETAIL STATUS: HOLD reinforcement / punching / settlement", 3.0))

    body.append(svg_rect(250, 205, 100, 18, 0.9))
    body.append(svg_text(300, 216, "STRIP 800 W × 200 THK — preliminary geometry", 3.0, "bold", "middle"))

    return sheet("S-02 PRELIMINARY STRUCTURAL GRID / FOUNDATION CONCEPT",
                 "Reference grid derived from architectural/foundation dimension chains", body)


def make_s03(design: Dict[str, Any]) -> str:
    body: List[str] = []
    body.append(svg_text(12, 35, "ROOF FRAMING — SPAN-CONTROLLED CONSOLIDATION", 4.5, "bold"))

    y = 55
    cases = design["roof_span_rules"]
    for case in cases:
        x1, x2 = 35, 210
        body.append(svg_line(x1, y, x2, y, 1.2))
        body.append(svg_line(x1, y-6, x1, y+6, 0.8))
        body.append(svg_line(x2, y-6, x2, y+6, 0.8))
        body.append(svg_text((x1+x2)/2, y-8, f"{case['span_m']:.2f} m unsupported span", 3.2, "bold", "middle"))
        body.append(svg_text(230, y-4, f"Source member: {case['source_member']}", 3.0))
        body.append(svg_text(230, y+2, f"Source status: {case['source_status']}", 3.0, "bold"))
        body.append(svg_text(230, y+8, f"Conservative provisional choice: {case['conservative_choice']}", 3.0))
        y += 45

    body.append(svg_text(12, 205, "CONSOLIDATED RULE", 4.0, "bold"))
    rules = [
        "• 2×3 source purlin @ 900 mm may only be retained where the actual unsupported span is proven ≤ 1.55 m.",
        "• 2×4 source rafter may only be retained where the actual unsupported span is proven ≤ 2.00 m.",
        "• Where support topology is not yet proven and span may reach 3.40 m, use 50×150 mm C18-proxy for preliminary coordination.",
        "• 50×150 @ 3.40 m proxy: governing utilization < 1.00 under current gravity model; grade, moisture, connections and wind remain HOLD.",
    ]
    y = 214
    for t in rules:
        body.append(svg_text(15, y, t, 3.0))
        y += 9

    return sheet("S-03 PRELIMINARY ROOF FRAMING / SPAN RULES",
                 "No roof member is accepted solely because it appears on the architectural drawing", body)


def make_s04(design: Dict[str, Any]) -> str:
    body: List[str] = []
    body.append(svg_text(12, 35, "TYPICAL PRELIMINARY DETAILS", 4.5, "bold"))

    # Ring beam detail
    body.append(svg_text(20, 48, "D1 • RC RING BEAM", 3.8, "bold"))
    body.append(svg_rect(30, 55, 30, 40, 1.0))
    for cx, cy in [(36,62),(54,62),(36,88),(54,88)]:
        body.append(svg_circle(cx, cy, 1.5, 0.6))
    body.append(svg_rect(34, 59, 22, 32, 0.5))
    body.append(svg_text(68, 64, "150 × 200 mm preliminary preferred geometry", 3.0))
    body.append(svg_text(68, 71, "2Ø12 top + 2Ø12 bottom; Ø8-150 ties — PRELIMINARY", 3.0))
    body.append(svg_text(68, 78, f"MEd proxy = {design['ringbeam']['MEd_kNm']:.2f} kNm", 3.0))
    body.append(svg_text(68, 85, f"MRd proxy = {design['ringbeam']['M_Rd_proxy_kNm']:.2f} kNm", 3.0))
    body.append(svg_text(68, 92, "Anchorage, shear, joints and final code basis: HOLD", 3.0, "bold"))

    # Column
    body.append(svg_text(220, 48, "D2 • RC COLUMN", 3.8, "bold"))
    body.append(svg_rect(235, 55, 40, 40, 1.0))
    for cx, cy in [(242,62),(268,62),(242,88),(268,88)]:
        body.append(svg_circle(cx, cy, 1.5, 0.6))
    body.append(svg_rect(240,60,30,30,0.5))
    body.append(svg_text(285, 64, "200 × 200 mm; 4Ø12; Ø8-150 ties", 3.0))
    body.append(svg_text(285, 72, f"Axial utilization proxy = {design['column']['axial_utilization']:.3f}", 3.0))
    body.append(svg_text(285, 80, "Combined N-M, second-order and lateral system: HOLD", 3.0, "bold"))

    # Footings
    body.append(svg_text(20, 120, "D3 • STRIP FOOTING", 3.8, "bold"))
    body.append(svg_rect(25, 132, 120, 20, 1.0))
    body.append(svg_text(85, 145, "800 W × 200 THK", 3.3, "bold", "middle"))
    body.append(svg_text(20, 162, f"Modeled service pressure ≈ {design['foundation']['strip_pressure_kPa']:.1f} kPa", 3.0))
    body.append(svg_text(20, 170, "Bearing PASS for qa 75/100/150 kPa; reinforcement/settlement HOLD", 3.0, "bold"))

    body.append(svg_text(220, 120, "D4 • PAD FOOTING", 3.8, "bold"))
    body.append(svg_rect(240, 130, 80, 40, 1.0))
    body.append(svg_text(280, 151, "1000 × 1000 × 200", 3.3, "bold", "middle"))
    body.append(svg_text(220, 181, f"Modeled service pressure ≈ {design['foundation']['pad_pressure_kPa']:.1f} kPa", 3.0))
    body.append(svg_text(220, 189, "Bearing PASS; punching/flexure/settlement HOLD", 3.0, "bold"))

    # Tank
    body.append(svg_text(20, 210, "D5 • ELEVATED 2.0 m³ TANK SUPPORT", 3.8, "bold"))
    body.append(svg_rect(25, 220, 60, 28, 0.8))
    body.append(svg_text(55, 237, "23.54 kN gravity envelope", 3.0, "bold", "middle"))
    body.append(svg_line(35, 248, 35, 266, 1.0))
    body.append(svg_line(75, 248, 75, 266, 1.0))
    body.append(svg_rect(22, 266, 66, 8, 1.0))
    body.append(svg_text(100, 230, "Concept only: dedicated support frame + dedicated foundation", 3.0))
    body.append(svg_text(100, 238, "Wind, overturning, anchorage, actual height and frame section: HOLD", 3.0, "bold"))

    return sheet("S-04 TYPICAL PRELIMINARY STRUCTURAL DETAILS",
                 "Details are coordination-level; they are not for construction", body)


def make_s05(design: Dict[str, Any]) -> str:
    body: List[str] = []
    body.append(svg_text(12, 35, "RELEASE HOLDS + SOURCE TRACEABILITY", 4.5, "bold"))
    y = 48
    for item in design["release_holds"]:
        body.append(svg_rect(14, y-5, 5, 5, 0.5))
        body.append(svg_text(24, y, item["id"], 3.0, "bold"))
        body.append(svg_text(55, y, item["hold"], 3.0))
        body.append(svg_text(300, y, item["required_for_release"], 2.8))
        y += 13

    body.append(svg_text(12, 205, "SOURCE CONFLICTS CARRIED FORWARD", 4.0, "bold"))
    y = 216
    for a in design["authority_decisions"]:
        body.append(svg_text(15, y, f"{a['id']}: {a['preliminary_model_choice']} — {a['final_status']}", 3.0))
        y += 9

    body.append(svg_text(12, 258, "FOR_CONSTRUCTION_RELEASE = LOCKED", 4.0, "bold"))
    return sheet("S-05 RELEASE HOLD / TRACEABILITY MATRIX",
                 "Every unresolved input remains explicit; no silent reconciliation", body)


def ensure_ezdxf():
    import ezdxf  # type: ignore
    return ezdxf


def dxf_setup():
    ezdxf = ensure_ezdxf()
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for layer in ["PHX_GRID","PHX_STRUCTURE","PHX_TEXT","PHX_HOLD","PHX_REFERENCE"]:
        if layer not in doc.layers:
            doc.layers.add(layer)
    return doc


def add_text(msp, text: str, x: float, y: float, h: float = 250.0, layer: str = "PHX_TEXT"):
    msp.add_text(str(text), dxfattribs={"height": h, "layer": layer}).set_placement((x,y))


def make_dxf_plan(path: Path, design: Dict[str, Any]):
    doc = dxf_setup()
    msp = doc.modelspace()
    W, H = 18200.0, 14050.0
    # perimeter structural envelope
    pts = [(0,0),(W,0),(W,H),(0,H),(0,0)]
    msp.add_lwpolyline(pts, dxfattribs={"layer":"PHX_STRUCTURE","lineweight":100})
    gx = design["geometry"]["x_coordinates"]
    gy = design["geometry"]["y_coordinates"]
    xoff, yoff = 50.0, 175.0
    for lab, xm in zip(design["geometry"]["x_axis_labels"], gx):
        x = xoff + xm*1000
        msp.add_line((x,-800),(x,H+800),dxfattribs={"layer":"PHX_GRID"})
        add_text(msp, lab, x-120, -650, 250)
    for lab, ym in zip(design["geometry"]["y_axis_labels"], gy):
        y = yoff + ym*1000
        msp.add_line((-800,y),(W+800,y),dxfattribs={"layer":"PHX_GRID"})
        add_text(msp, lab, -650, y-100, 220)
    add_text(msp, "S-02 PRELIMINARY STRUCTURAL GRID / FOUNDATION ENVELOPE", 0, H+1400, 350)
    add_text(msp, "PERIMETER STRIP FOOTING ENVELOPE 800x200 - GRAVITY PASS / GEOTECH HOLD", 0, -1400, 250, "PHX_HOLD")
    add_text(msp, "INTERIOR LOADBEARING WALL/COLUMN VECTORS NOT YET ACCEPTED - REFER SOURCE FOUNDATION SNAPSHOT", 0, -1900, 220, "PHX_HOLD")
    doc.saveas(path)


def make_dxf_roof(path: Path, design: Dict[str, Any]):
    doc = dxf_setup()
    msp = doc.modelspace()
    y = 0.0
    for case in design["roof_span_rules"]:
        L = case["span_m"]*1000
        msp.add_line((0,y),(L,y),dxfattribs={"layer":"PHX_STRUCTURE"})
        msp.add_line((0,y-200),(0,y+200),dxfattribs={"layer":"PHX_STRUCTURE"})
        msp.add_line((L,y-200),(L,y+200),dxfattribs={"layer":"PHX_STRUCTURE"})
        add_text(msp, f"{case['span_m']:.2f} m | {case['source_member']} | {case['source_status']}", L+500, y, 220)
        add_text(msp, f"PRELIM: {case['conservative_choice']}", L+500, y-350, 200, "PHX_HOLD")
        y -= 1500
    add_text(msp, "S-03 ROOF FRAMING SPAN RULES - PRELIMINARY", 0, 1200, 320)
    doc.saveas(path)


def make_dxf_details(path: Path, design: Dict[str, Any]):
    doc = dxf_setup()
    msp = doc.modelspace()
    # Ringbeam 150x200 at 1:1
    x0,y0 = 0,0
    msp.add_lwpolyline([(x0,y0),(x0+150,y0),(x0+150,y0+200),(x0,y0+200),(x0,y0)],dxfattribs={"layer":"PHX_STRUCTURE"})
    for x,y in [(30,35),(120,35),(30,165),(120,165)]:
        msp.add_circle((x0+x,y0+y),6,dxfattribs={"layer":"PHX_STRUCTURE"})
    add_text(msp, "D1 RINGBEAM 150x200 2D12 TOP/BOTTOM; LINKS D8-150 PRELIM", 250, 100, 60)
    # Column
    x0,y0 = 0,-700
    msp.add_lwpolyline([(x0,y0),(x0+200,y0),(x0+200,y0+200),(x0,y0+200),(x0,y0)],dxfattribs={"layer":"PHX_STRUCTURE"})
    for x,y in [(35,35),(165,35),(35,165),(165,165)]:
        msp.add_circle((x0+x,y0+y),6,dxfattribs={"layer":"PHX_STRUCTURE"})
    add_text(msp, "D2 COLUMN 200x200 4D12; LINKS D8-150 PRELIM", 300, -600, 60)
    # Strip and pad
    msp.add_lwpolyline([(0,-1500),(800,-1500),(800,-1300),(0,-1300),(0,-1500)],dxfattribs={"layer":"PHX_STRUCTURE"})
    add_text(msp, "D3 STRIP 800x200 - REBAR/SETTLEMENT HOLD", 1000, -1400, 60, "PHX_HOLD")
    msp.add_lwpolyline([(0,-2600),(1000,-2600),(1000,-1600),(0,-1600),(0,-2600)],dxfattribs={"layer":"PHX_STRUCTURE"})
    add_text(msp, "D4 PAD 1000x1000x200 - PUNCHING/FLEXURE/SETTLEMENT HOLD", 1200, -2100, 60, "PHX_HOLD")
    add_text(msp, "S-04 PRELIMINARY STRUCTURAL DETAILS - NOT FOR CONSTRUCTION", 0, 650, 100)
    doc.saveas(path)


def render_source_snapshots(pdf_path: Path, out: Path) -> Dict[str, Any]:
    result = {"status":"NOT_ATTEMPTED","files":[]}
    try:
        import pypdfium2 as pdfium  # type: ignore
        pdf = pdfium.PdfDocument(str(pdf_path))
        refs = [(1,"source_page_02_foundation.png"),(5,"source_page_06_roof.png"),(6,"source_page_07_section.png"),(7,"source_page_08_details.png")]
        for idx,name in refs:
            page = pdf[idx]
            bitmap = page.render(scale=1.25)
            pil = bitmap.to_pil()
            target = out/name
            pil.save(target)
            result["files"].append(name)
        result["status"]="PASS"
    except Exception as exc:
        result={"status":"SKIPPED_RENDERER_UNAVAILABLE","error":str(exc),"files":[]}
    return result


def consolidate(solver: Dict[str, Any], derivation: Dict[str, Any], cfg: Dict[str, Any], source_sha: str) -> Dict[str, Any]:
    if solver["status"] not in (
        "PASS_REAL_OPEN_SOURCE_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION",
        "PASS_PRIMARY_SOLVER_EXECUTED_PRELIMINARY_ELEMENT_VERIFICATION",
    ):
        raise RuntimeError("Solver prerequisite is not PASS")
    if solver["source_sha256"] != source_sha:
        raise RuntimeError("Solver source SHA mismatch")
    if derivation["source"]["sha256"] != source_sha:
        raise RuntimeError("Derivation source SHA mismatch")

    roof_gk = float(derivation["load_model"]["roof"]["gk_total_kN_m2"])
    roof_qk = float(derivation["load_model"]["roof"]["nonaccessible_roof_imposed_qk_kN_m2"])
    tcfg = cfg["timber_proxy"]
    conservative = timber_utilization(
        cfg["unproven_roof_span_m"], 50.0, 150.0, tcfg["spacing_m"],
        roof_gk, roof_qk, tcfg["E_mpa"], tcfg["fmk_mpa"], tcfg["kmod"],
        tcfg["gamma_m"], tcfg["deflection_limit_ratio"]
    )
    if conservative["status"] != "PASS":
        raise RuntimeError("Configured conservative 50x150 roof proxy does not pass")

    ring_src = solver["element_verification"]["rc_ringbeam_100x200"]
    worst_ring = max(ring_src["span_sensitivity"], key=lambda x: x["MEd_kNm"])
    ring = rc_flexure_proxy(
        150.0, 200.0, 2, 12.0, cfg["ringbeam"]["cover_mm"],
        cfg["materials"]["fyk_mpa"], cfg["materials"]["gamma_s"]
    )
    ring["MEd_kNm"] = float(worst_ring["MEd_kNm"])
    ring["utilization_proxy"] = round(ring["MEd_kNm"]/ring["M_Rd_proxy_kNm"],3)
    if ring["utilization_proxy"] > 1.0:
        raise RuntimeError("Proposed ring-beam flexure proxy does not pass")

    col = solver["element_verification"]["rc_column_200x200_4D12"]
    strip = solver["element_verification"]["strip_800x200"]
    pad = solver["element_verification"]["pad_1000x1000x200"]

    schedule = [
        {"id":"F01","element":"Ground-bearing slab","choice":"150 mm source geometry; source shrinkage mesh note retained, structural slab behavior not assumed","status":"PROVISIONAL"},
        {"id":"F02","element":"Strip footing","choice":"800×200 mm source geometry retained because modeled gravity bearing passes qa 75/100/150 kPa","status":"GEOTECH/REBAR HOLD"},
        {"id":"F03","element":"Pad footing","choice":"1000×1000×200 mm source geometry retained; modeled gravity bearing passes","status":"PUNCHING/REBAR/SETTLEMENT HOLD"},
        {"id":"C01","element":"RC column","choice":"200×200 mm, 4Ø12, Ø8-150 ties retained provisionally","status":"AXIAL PASS; N-M HOLD"},
        {"id":"B01","element":"Primary ring beam","choice":"150×200 mm preferred Phoenix coordination section; 2Ø12 top + 2Ø12 bottom; Ø8-150 ties provisional","status":"FLEXURE PROXY PASS"},
        {"id":"R01","element":"Purlin","choice":"Source 2×3 @900 only if unsupported span ≤1.55 m; otherwise 50×150 mm C18-proxy for ≤3.40 m","status":"SPAN/GRADE/CONNECTION HOLD"},
        {"id":"R02","element":"Rafter","choice":"Source 2×4 only if unsupported span ≤2.00 m; otherwise 50×150 mm C18-proxy for ≤3.40 m","status":"SPAN/GRADE/CONNECTION HOLD"},
        {"id":"T01","element":"Elevated 2 m³ tank","choice":"23.54 kN gravity envelope; dedicated support frame and foundation required","status":"WIND/FRAME/ANCHORAGE HOLD"},
    ]

    release_holds = [
        {"id":"H01","hold":"Confirm legally applicable Suriname structural code hierarchy and wind parameter","required_for_release":"MANDATORY"},
        {"id":"H02","hold":"Site-specific geotechnical investigation incl. settlement / groundwater","required_for_release":"MANDATORY"},
        {"id":"H03","hold":"Map and approve actual loadbearing wall/column vectors from source plan","required_for_release":"MANDATORY"},
        {"id":"H04","hold":"Confirm timber species, grade, dressed dimensions, moisture/service class","required_for_release":"MANDATORY"},
        {"id":"H05","hold":"Design roof connections, anchorage and wind uplift load path","required_for_release":"MANDATORY"},
        {"id":"H06","hold":"Complete RC N-M/shear/anchorage/punching/reinforcement detailing","required_for_release":"MANDATORY"},
        {"id":"H07","hold":"Confirm elevated tank support height/geometry; check wind/overturning/anchorage","required_for_release":"MANDATORY"},
        {"id":"H08","hold":"Professional structural review and signed release","required_for_release":"MANDATORY"},
    ]

    roof_rules = [
        {"span_m":1.55,"source_member":"2×3 purlin @900","source_status":"PASS under current C18 proxy","conservative_choice":"retain source size only when actual span is proven ≤1.55 m"},
        {"span_m":2.00,"source_member":"2×4 rafter","source_status":"PASS under current C18 proxy","conservative_choice":"retain source size only when actual span is proven ≤2.00 m"},
        {"span_m":3.40,"source_member":"source 2×3 / 2×4","source_status":"FAIL under current C18 proxy","conservative_choice":"50×150 mm C18-proxy preliminary coordination size"},
    ]

    return {
        "schema":"PHOENIX_STRUCTURAL_DESIGN_CONSOLIDATION_1.0",
        "engine_version":ENGINE_VERSION,
        "generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "project_id":solver["project_id"],
        "source_sha256":source_sha,
        "solver_status":solver["status"],
        "executed_solver":solver["primary_solver"]["engine"],
        "geometry":{
            "outer_envelope_m":derivation["geometry"]["overall_outer_faces_m"],
            "x_axis_labels":derivation["geometry"]["structural_reference_grid_m"]["x_axis_labels"],
            "x_coordinates":derivation["geometry"]["structural_reference_grid_m"]["x_coordinates"],
            "y_axis_labels":derivation["geometry"]["structural_reference_grid_m"]["y_axis_labels"],
            "y_coordinates":derivation["geometry"]["structural_reference_grid_m"]["y_coordinates"],
        },
        "roof_conservative_50x150_check":conservative,
        "roof_span_rules":roof_rules,
        "ringbeam":ring,
        "column":{
            "section_mm":[200,200],
            "reinforcement":"4Ø12; Ø8-150 ties provisional",
            "axial_utilization":float(col["axial_utilization"]),
            "status":"AXIAL_ONLY_PASS; COMBINED N-M / SLENDERNESS / LATERAL HOLD",
        },
        "foundation":{
            "strip_mm":[800,200],
            "strip_pressure_kPa":float(strip["modeled_bearing_pressure_kPa"]),
            "pad_mm":[1000,1000,200],
            "pad_pressure_kPa":float(pad["modeled_bearing_pressure_kPa"]),
            "status":"GRAVITY_BEARING_PASS_IN_MODELED_QA_CASES; GEOTECH/SETTLEMENT/REINFORCEMENT HOLD",
        },
        "tank":{
            "gravity_envelope_kN":float(solver["element_verification"]["elevated_tank"]["gravity_envelope_kN"]),
            "status":"GRAVITY FOUNDATION ENVELOPE ONLY; FRAME/WIND/ANCHORAGE HOLD",
        },
        "element_schedule":schedule,
        "release_holds":release_holds,
        "authority_decisions":derivation["authority_decisions"],
        "drawing_policy":{
            "source_plan_not_silently_redrawn":True,
            "interior_loadbearing_vectors_finalized":False,
            "foundation_plan_output":"GRID_AND_PERIMETER_ENVELOPE_CONCEPT_ONLY",
            "source_reference_snapshots":"ATTEMPTED_SEPARATELY",
        },
        "governance":{
            "preliminary_not_for_construction":True,
            "professional_structural_review_required":True,
            "for_construction_release":"LOCKED",
        },
        "status":STATUS,
        "next_stage":NEXT_STAGE,
    }


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k:row.get(k,"") for k in fields})


def write_outputs(design: Dict[str, Any], out: Path, source_pdf: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    drawings = out/"drawings"
    drawings.mkdir(exist_ok=True)
    refs = out/"source_reference"
    refs.mkdir(exist_ok=True)

    (out/"structural_design_consolidation.json").write_text(json.dumps(design,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"element_schedule.json").write_text(json.dumps(design["element_schedule"],indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"release_holds.json").write_text(json.dumps(design["release_holds"],indent=2,ensure_ascii=False),encoding="utf-8")
    write_csv(out/"element_schedule.csv",design["element_schedule"],["id","element","choice","status"])
    write_csv(out/"release_holds.csv",design["release_holds"],["id","hold","required_for_release"])

    svgs = {
        "S-01_structural_basis_schedule.svg":make_s01(design),
        "S-02_structural_grid_foundation_concept.svg":make_s02(design),
        "S-03_roof_framing_span_rules.svg":make_s03(design),
        "S-04_typical_structural_details.svg":make_s04(design),
        "S-05_release_hold_traceability.svg":make_s05(design),
    }
    for name,data in svgs.items():
        (drawings/name).write_text(data,encoding="utf-8")

    make_dxf_plan(drawings/"S-02_structural_grid_foundation_concept.dxf",design)
    make_dxf_roof(drawings/"S-03_roof_framing_span_rules.dxf",design)
    make_dxf_details(drawings/"S-04_typical_structural_details.dxf",design)

    snapshot_result = render_source_snapshots(source_pdf,refs)
    (out/"source_reference_rendering.json").write_text(json.dumps(snapshot_result,indent=2),encoding="utf-8")

    index = [
        {"sheet":"S-01","title":"Structural design basis + element schedule","svg":"drawings/S-01_structural_basis_schedule.svg","dxf":""},
        {"sheet":"S-02","title":"Structural grid / foundation concept","svg":"drawings/S-02_structural_grid_foundation_concept.svg","dxf":"drawings/S-02_structural_grid_foundation_concept.dxf"},
        {"sheet":"S-03","title":"Roof framing span rules","svg":"drawings/S-03_roof_framing_span_rules.svg","dxf":"drawings/S-03_roof_framing_span_rules.dxf"},
        {"sheet":"S-04","title":"Typical structural details","svg":"drawings/S-04_typical_structural_details.svg","dxf":"drawings/S-04_typical_structural_details.dxf"},
        {"sheet":"S-05","title":"Release hold / traceability matrix","svg":"drawings/S-05_release_hold_traceability.svg","dxf":""},
    ]
    write_csv(out/"drawing_index.csv",index,["sheet","title","svg","dxf"])
    (out/"drawing_index.json").write_text(json.dumps(index,indent=2),encoding="utf-8")

    # Lightweight HTML viewer for DE TV / browser review.
    cards = []
    for item in index:
        cards.append(
            f'<section><h2>{html.escape(item["sheet"]+" — "+item["title"])}</h2>'
            f'<object data="{html.escape(item["svg"])}" type="image/svg+xml" style="width:100%;height:720px;border:1px solid #999"></object>'
            f'<p>DXF: {html.escape(item["dxf"] or "n/a")}</p></section>'
        )
    viewer = f"""<!doctype html><html><head><meta charset="utf-8"><title>PHOENIX Anijstraat #616 Structural Drawings</title>
<style>body{{font-family:Arial,sans-serif;max-width:1400px;margin:auto;padding:20px}}section{{margin-bottom:40px}}.hold{{font-weight:bold}}</style>
</head><body><h1>PHOENIX 4.41 — Anijstraat #616</h1>
<p class="hold">PRELIMINARY / NOT FOR CONSTRUCTION — FOR_CONSTRUCTION_RELEASE = LOCKED</p>
{''.join(cards)}</body></html>"""
    (out/"structural_drawings_viewer.html").write_text(viewer,encoding="utf-8")

    # Verify SVG and DXF now.
    for name in svgs:
        ET.parse(drawings/name)
    ezdxf = ensure_ezdxf()
    for name in ["S-02_structural_grid_foundation_concept.dxf","S-03_roof_framing_span_rules.dxf","S-04_typical_structural_details.dxf"]:
        ezdxf.readfile(drawings/name)

    manifest = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="evidence_manifest.json":
            manifest[p.relative_to(out).as_posix()]={"sha256":sha256_file(p),"bytes":p.stat().st_size}
    (out/"evidence_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")


def verify_output(path: Path) -> None:
    d = json.loads(path.read_text(encoding="utf-8"))
    out = path.parent
    assert d["status"] == STATUS
    assert d["governance"]["preliminary_not_for_construction"] is True
    assert d["governance"]["for_construction_release"] == "LOCKED"
    assert d["drawing_policy"]["source_plan_not_silently_redrawn"] is True
    assert d["roof_conservative_50x150_check"]["status"] == "PASS"
    assert d["ringbeam"]["utilization_proxy"] < 1.0
    assert d["column"]["axial_utilization"] < 1.0
    required = [
        "drawings/S-01_structural_basis_schedule.svg",
        "drawings/S-02_structural_grid_foundation_concept.svg",
        "drawings/S-03_roof_framing_span_rules.svg",
        "drawings/S-04_typical_structural_details.svg",
        "drawings/S-05_release_hold_traceability.svg",
        "drawings/S-02_structural_grid_foundation_concept.dxf",
        "drawings/S-03_roof_framing_span_rules.dxf",
        "drawings/S-04_typical_structural_details.dxf",
        "drawing_index.csv",
        "structural_drawings_viewer.html",
        "evidence_manifest.json",
    ]
    for rel in required:
        assert (out/rel).exists(), rel
    print("PHOENIX_4_41_STRUCTURAL_DESIGN_CONSOLIDATION_OUTPUT_VERIFY=PASS")


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--solver-json",type=Path)
    ap.add_argument("--derivation-json",type=Path)
    ap.add_argument("--source-pdf",type=Path)
    ap.add_argument("--config",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--verify-output",type=Path)
    args=ap.parse_args()

    if args.verify_output:
        verify_output(args.verify_output)
        return 0
    if not all([args.solver_json,args.derivation_json,args.source_pdf,args.config,args.output]):
        ap.error("--solver-json --derivation-json --source-pdf --config --output required")

    source_sha=sha256_file(args.source_pdf)
    solver=json.loads(args.solver_json.read_text(encoding="utf-8"))
    derivation=json.loads(args.derivation_json.read_text(encoding="utf-8"))
    cfg=json.loads(args.config.read_text(encoding="utf-8"))
    design=consolidate(solver,derivation,cfg,source_sha)
    write_outputs(design,args.output,args.source_pdf)

    print(f"PROJECT_ID={design['project_id']}")
    print(f"SOURCE_SHA256={design['source_sha256']}")
    print(f"EXECUTED_SOLVER_EVIDENCE={design['executed_solver']}")
    print(f"ROOF_50x150_3P4M_UTIL={design['roof_conservative_50x150_check']['governing_utilization']}")
    print(f"RINGBEAM_150x200_FLEXURE_UTIL={design['ringbeam']['utilization_proxy']}")
    print(f"COLUMN_AXIAL_UTIL={design['column']['axial_utilization']}")
    print("SVG_DRAWINGS=5")
    print("DXF_DRAWINGS=3")
    print("FOR_CONSTRUCTION_RELEASE=LOCKED")
    print("PRELIMINARY_NOT_FOR_CONSTRUCTION=TRUE")
    print(f"STRUCTURAL_DESIGN_CONSOLIDATION_STATUS={design['status']}")
    print(f"NEXT_STAGE={design['next_stage']}")
    print(f"OUTPUT={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
