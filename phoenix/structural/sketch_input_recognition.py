"""Sketch upload recognition and confirmation engine for RC beam input.

The engine accepts image/PDF uploads and uses the first available text source:
1. explicit OCR text, 2. sidecar .txt, 3. Tesseract, 4. Windows OCR, 5. PDF text.
Recognized values remain candidates until the user confirmation gate is passed.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pdf"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
CRITICAL_FIELDS = (
    "span_m", "width_mm", "height_mm", "concrete_class", "reinforcement_class",
    "nominal_cover_mm", "support_a", "support_b"
)


def _number(raw: str) -> float:
    return float(raw.strip().replace(" ", "").replace(",", "."))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class SketchInputRecognitionEngine:
    VERSION = "1.0.0"

    def __init__(self, repository_root: Path | None = None):
        self.repository_root = Path(repository_root) if repository_root else None

    def validate_upload(self, sketch_path: Path) -> None:
        sketch_path = Path(sketch_path)
        if not sketch_path.is_file():
            raise FileNotFoundError(sketch_path)
        if sketch_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported sketch type: {sketch_path.suffix}")
        if sketch_path.stat().st_size > MAX_UPLOAD_BYTES:
            raise ValueError("Sketch exceeds 25 MB upload limit")

    def acquire_text(self, sketch_path: Path, explicit_text: str | None = None) -> tuple[str, str, list[str]]:
        warnings: list[str] = []
        if explicit_text and explicit_text.strip():
            return explicit_text.strip(), "EXPLICIT_OCR_TEXT", warnings
        sidecar = sketch_path.with_suffix(sketch_path.suffix + ".txt")
        alternate = sketch_path.with_suffix(".txt")
        for candidate in (sidecar, alternate):
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip(), "SIDECAR_TEXT", warnings
        if sketch_path.suffix.lower() == ".pdf":
            text = self._pdf_text(sketch_path)
            if text:
                return text, "PDF_TEXT_LAYER", warnings
            warnings.append("PDF has no readable text layer; export the sketch page as PNG/JPG or provide manual OCR text.")
            return "", "NO_TEXT_BACKEND", warnings
        text = self._tesseract_text(sketch_path)
        if text:
            return text, "TESSERACT_OCR", warnings
        text = self._windows_ocr_text(sketch_path)
        if text:
            return text, "WINDOWS_OCR", warnings
        warnings.append("No OCR backend produced text. Manual confirmation input is required.")
        return "", "NO_TEXT_BACKEND", warnings

    def _pdf_text(self, path: Path) -> str:
        for module_name in ("pypdf", "PyPDF2"):
            try:
                module = __import__(module_name)
                reader = module.PdfReader(str(path))
                return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            except Exception:
                continue
        return ""

    def _tesseract_text(self, path: Path) -> str:
        exe = shutil.which("tesseract")
        if not exe:
            return ""
        try:
            result = subprocess.run([exe, str(path), "stdout", "--psm", "6"], capture_output=True, text=True, timeout=60, shell=False)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _windows_ocr_text(self, path: Path) -> str:
        if os.name != "nt" or self.repository_root is None:
            return ""
        script = self.repository_root / "scripts/phoenix_structural_sketch/INVOKE_WINDOWS_OCR.ps1"
        if not script.is_file():
            return ""
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            return ""
        try:
            result = subprocess.run([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-ImagePath", str(path)], capture_output=True, text=True, timeout=90, shell=False)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def parse_text(self, text: str) -> dict[str, Any]:
        compact = text.replace("×", "x").replace("–", "-").replace("—", "-")
        fields: dict[str, dict[str, Any]] = {}

        def set_field(name: str, value: Any, confidence: float, evidence: str):
            current = fields.get(name)
            row = {"value": value, "confidence": round(confidence, 3), "evidence": evidence}
            if current is None or row["confidence"] > current["confidence"]:
                fields[name] = row

        patterns = [
            (r"(?:overspanning|span|\bL)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)\s*m\b", "span_m", 0.97),
            (r"(?:balk|beam)?\s*(\d{2,4})\s*[xX]\s*(\d{2,4})\s*mm\b", "section", 0.96),
            (r"\bb\s*[:=]\s*(\d{2,4})\s*mm\b", "width_mm", 0.92),
            (r"\bh\s*[:=]\s*(\d{2,4})\s*mm\b", "height_mm", 0.92),
            (r"(?:dekking|cover|cnom|c_nom|\bc\b)\s*[:=]?\s*(\d{1,3})\s*mm\b", "nominal_cover_mm", 0.9),
        ]
        for pattern, field, conf in patterns:
            for match in re.finditer(pattern, compact, flags=re.I):
                if field == "section":
                    set_field("width_mm", int(match.group(1)), conf, match.group(0))
                    set_field("height_mm", int(match.group(2)), conf, match.group(0))
                else:
                    value = _number(match.group(1))
                    if field.endswith("_mm"):
                        value = int(round(value))
                    set_field(field, value, conf, match.group(0))

        concrete = re.search(r"\bC\s*(\d{2})\s*/\s*(\d{2})\b", compact, flags=re.I)
        if concrete:
            set_field("concrete_class", f"C{concrete.group(1)}/{concrete.group(2)}", 0.99, concrete.group(0))
        steel = re.search(r"\bB\s*(\d{3})\s*([A-C])?\b", compact, flags=re.I)
        if steel:
            set_field("reinforcement_class", f"B{steel.group(1)}{(steel.group(2) or 'B').upper()}", 0.97, steel.group(0))

        q_loads = []
        for m in re.finditer(r"\b([gq])(?:\s*[_-]?[a-z0-9]+)?\s*[:=]\s*(\d+(?:[\.,]\d+)?)\s*kN\s*/\s*m\b", compact, flags=re.I):
            category = "permanent" if m.group(1).lower() == "g" else "variable"
            q_loads.append({"load_id": f"{m.group(1).upper()}-{len(q_loads)+1:02d}", "category": category, "characteristic_kn_m": _number(m.group(2)), "evidence": m.group(0), "confidence": 0.98})
        for m in re.finditer(r"(?:verdeelde\s+last|udl|\bq\b)\s*[:=]?\s*(\d+(?:[\.,]\d+)?)\s*kN\s*/\s*m\b", compact, flags=re.I):
            if not any(abs(row["characteristic_kn_m"] - _number(m.group(1))) < 1e-9 for row in q_loads):
                q_loads.append({"load_id": f"Q-{len(q_loads)+1:02d}", "category": "variable", "characteristic_kn_m": _number(m.group(1)), "evidence": m.group(0), "confidence": 0.95})

        point_loads = []
        point_pattern = re.compile(r"\bP\s*(\d+)?\s*[:=]?\s*(\d+(?:[\.,]\d+)?)\s*kN(?:\s*(?:@|op|at|x\s*=?)\s*(\d+(?:[\.,]\d+)?)\s*m)?", flags=re.I)
        for idx, m in enumerate(point_pattern.finditer(compact), start=1):
            point_loads.append({
                "load_id": f"P-{int(m.group(1) or idx):02d}",
                "category": "variable",
                "characteristic_kn": _number(m.group(2)),
                "position_m": _number(m.group(3)) if m.group(3) else None,
                "evidence": m.group(0),
                "confidence": 0.97 if m.group(3) else 0.72,
            })

        support_a = "PIN" if re.search(r"(?:support|oplegging|steunpunt)\s*A.*?(?:scharnier|pin)", compact, flags=re.I | re.S) else None
        support_b = "ROLLER" if re.search(r"(?:support|oplegging|steunpunt)\s*B.*?(?:rol|roller)", compact, flags=re.I | re.S) else None
        if re.search(r"scharnier\s*\+\s*(?:rol|roller)|pin\s*\+\s*roller", compact, flags=re.I):
            support_a, support_b = "PIN", "ROLLER"
        if support_a:
            set_field("support_a", support_a, 0.92, "support A text")
        if support_b:
            set_field("support_b", support_b, 0.92, "support B text")

        warnings = []
        for load in point_loads:
            if load["position_m"] is None:
                warnings.append(f"{load['load_id']} position is missing")
        if not q_loads and not point_loads:
            warnings.append("No distributed or point load recognized")
        return {"fields": fields, "distributed_loads": q_loads, "point_loads": point_loads, "warnings": warnings}

    def apply_confirmation(self, candidate: Mapping[str, Any], confirmation: Mapping[str, Any] | None) -> dict[str, Any]:
        values = {name: row["value"] for name, row in candidate.get("fields", {}).items()}
        distributed = [dict(x) for x in candidate.get("distributed_loads", [])]
        points = [dict(x) for x in candidate.get("point_loads", [])]
        confirmation = dict(confirmation or {})
        values.update({k: v for k, v in confirmation.get("fields", {}).items() if v not in (None, "")})
        if "distributed_loads" in confirmation:
            distributed = [dict(x) for x in confirmation["distributed_loads"]]
        if "point_loads" in confirmation:
            points = [dict(x) for x in confirmation["point_loads"]]
        errors = []
        for field in CRITICAL_FIELDS:
            if values.get(field) in (None, ""):
                errors.append(f"critical field missing: {field}")
        if not distributed and not points:
            errors.append("at least one distributed or point load is required")
        span = float(values.get("span_m") or 0)
        for row in points:
            pos = row.get("position_m")
            if pos is None:
                errors.append(f"point load position missing: {row.get('load_id', 'P')}")
            elif not 0 < float(pos) < span:
                errors.append(f"point load outside span: {row.get('load_id', 'P')}")
        confirmed = bool(confirmation.get("confirmed_by_user")) and not errors
        return {"values": values, "distributed_loads": distributed, "point_loads": points, "confirmed_by_user": bool(confirmation.get("confirmed_by_user")), "confirmed": confirmed, "errors": errors, "confirmation_note": confirmation.get("confirmation_note", "")}

    def recognize(self, sketch_path: Path, jurisdiction_code: str, explicit_text: str | None = None, confirmation: Mapping[str, Any] | None = None) -> dict[str, Any]:
        sketch_path = Path(sketch_path)
        self.validate_upload(sketch_path)
        text, source, warnings = self.acquire_text(sketch_path, explicit_text)
        parsed = self.parse_text(text)
        resolved = self.apply_confirmation(parsed, confirmation)
        return {
            "schema_version": "phoenix.structural-sketch-recognition/1.0",
            "engine_version": self.VERSION,
            "jurisdiction_code": jurisdiction_code.upper(),
            "sketch": {"filename": sketch_path.name, "extension": sketch_path.suffix.lower(), "size_bytes": sketch_path.stat().st_size, "sha256": _sha(sketch_path), "mime_type": mimetypes.guess_type(sketch_path.name)[0] or "application/octet-stream"},
            "text_source": source,
            "ocr_text": text,
            "candidate": parsed,
            "resolved": resolved,
            "warnings": warnings + parsed.get("warnings", []),
            "input_ready": resolved["confirmed"],
            "final_structural_release_allowed": False,
        }

    def to_beam_config(self, recognition: Mapping[str, Any], profile: Mapping[str, Any], engineer_confirmation: Mapping[str, Any], base_config: Mapping[str, Any]) -> dict[str, Any]:
        if not recognition.get("input_ready"):
            raise ValueError("Recognition is not user-confirmed and input-ready")
        values = recognition["resolved"]["values"]
        cfg = json.loads(json.dumps(base_config))
        cfg["project_id"] = engineer_confirmation.get("project_id", "PHX-SKETCH-INPUT-001")
        cfg["beam"]["beam_id"] = engineer_confirmation.get("beam_id", "RCB-SKETCH-001")
        cfg["beam"]["name"] = engineer_confirmation.get("beam_name", "Beam from uploaded sketch")
        cfg["beam"]["model_object_id"] = engineer_confirmation.get("model_object_id", "UNASSIGNED-SKETCH-BEAM")
        cfg["beam"]["span_m"] = float(values["span_m"])
        cfg["beam"]["width_mm"] = int(values["width_mm"])
        cfg["beam"]["height_mm"] = int(values["height_mm"])
        cfg["beam"]["nominal_cover_mm"] = int(values["nominal_cover_mm"])
        cfg["materials"]["concrete_class"] = str(values["concrete_class"])
        m = re.match(r"C(\d{2})/(\d{2})", str(values["concrete_class"]))
        if m:
            fck = float(m.group(1)); cfg["materials"]["fck_mpa"] = fck
            known = {20: 2.2, 25: 2.6, 30: 2.9, 35: 3.2, 40: 3.5, 45: 3.8, 50: 4.1}
            cfg["materials"]["fctm_mpa"] = known.get(int(fck), round(0.3 * fck ** (2/3), 2))
            cfg["materials"]["fctk_005_mpa"] = round(0.7 * cfg["materials"]["fctm_mpa"], 2)
        cfg["materials"]["reinforcement_class"] = str(values["reinforcement_class"])
        ms = re.match(r"B(\d{3})", str(values["reinforcement_class"]))
        if ms:
            cfg["materials"]["fyk_mpa"] = float(ms.group(1))
        permanent = sum(float(x["characteristic_kn_m"]) for x in recognition["resolved"]["distributed_loads"] if x.get("category") == "permanent")
        variable = sum(float(x["characteristic_kn_m"]) for x in recognition["resolved"]["distributed_loads"] if x.get("category") != "permanent")
        cfg["loads"]["permanent_udl_kn_m"] = permanent
        cfg["loads"]["variable_udl_kn_m"] = variable
        cfg["loads"]["point_loads"] = [{"load_id": row.get("load_id", f"P-{i:02d}"), "characteristic_kn": float(row["characteristic_kn"]), "position_m": float(row["position_m"]), "category": row.get("category", "variable"), "psi2": float(row.get("psi2", 0.3))} for i, row in enumerate(recognition["resolved"]["point_loads"], start=1)]
        cfg["standard_profile"]["profile_id"] = f"{profile['profile_id']}__{engineer_confirmation['design_standard_reference']}"
        cfg["standard_profile"]["base_standard"] = engineer_confirmation["design_standard_reference"]
        cfg["standard_profile"]["national_annex"] = engineer_confirmation.get("national_annex_or_local_basis", "PROJECT-SPECIFIC")
        cfg["regional_profile"] = {"jurisdiction_code": profile["jurisdiction_code"], "jurisdiction": profile["jurisdiction"], "profile_id": profile["profile_id"], "structural_standard_status": profile["structural_standard_status"], "engineer_confirmation": dict(engineer_confirmation), "final_release_policy": profile["final_release_policy"]}
        cfg["scope"]["fire_design_included"] = False
        return cfg


def render_preview_svg(recognition: Mapping[str, Any]) -> str:
    values = recognition["resolved"]["values"]
    span = float(values.get("span_m") or 1.0)
    width = 1100; x0 = 140; x1 = 960; y = 300
    point_parts = []
    for row in recognition["resolved"]["point_loads"]:
        if row.get("position_m") is None: continue
        x = x0 + (x1-x0) * float(row["position_m"]) / span
        point_parts.append(f'<line x1="{x:.1f}" y1="100" x2="{x:.1f}" y2="260" stroke="#b91c1c" stroke-width="5"/><polygon points="{x-10:.1f},245 {x+10:.1f},245 {x:.1f},270" fill="#b91c1c"/><text x="{x:.1f}" y="80" text-anchor="middle" font-size="24">{escape(str(row.get("load_id")))} = {row.get("characteristic_kn")} kN @ {row.get("position_m")} m</text>')
    q = sum(float(r["characteristic_kn_m"]) for r in recognition["resolved"]["distributed_loads"])
    q_arrows = ''
    if q:
        for x in range(x0, x1+1, 80):
            q_arrows += f'<line x1="{x}" y1="165" x2="{x}" y2="260" stroke="#1d4ed8" stroke-width="3"/><polygon points="{x-7},248 {x+7},248 {x},266" fill="#1d4ed8"/>'
    status = 'INPUT READY' if recognition.get('input_ready') else 'CONFIRMATION REQUIRED'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="620" viewBox="0 0 {width} 620"><rect width="100%" height="100%" fill="white"/><text x="40" y="45" font-size="28" font-weight="bold">Phoenix sketch interpretation preview</text><text x="40" y="82" font-size="18">Jurisdiction: {escape(recognition['jurisdiction_code'])} | Status: {status}</text><text x="550" y="135" text-anchor="middle" font-size="24" fill="#1d4ed8">q total = {q:.3f} kN/m</text>{q_arrows}{''.join(point_parts)}<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="#111827" stroke-width="12"/><polygon points="{x0-30},{y+70} {x0+30},{y+70} {x0},{y+8}" fill="none" stroke="#111827" stroke-width="5"/><circle cx="{x1-18}" cy="{y+68}" r="13" fill="none" stroke="#111827" stroke-width="4"/><circle cx="{x1+18}" cy="{y+68}" r="13" fill="none" stroke="#111827" stroke-width="4"/><line x1="{x1-35}" y1="{y+85}" x2="{x1+35}" y2="{y+85}" stroke="#111827" stroke-width="4"/><line x1="{x0}" y1="{y+135}" x2="{x1}" y2="{y+135}" stroke="#374151" stroke-width="2"/><line x1="{x0}" y1="{y+120}" x2="{x0}" y2="{y+150}" stroke="#374151" stroke-width="2"/><line x1="{x1}" y1="{y+120}" x2="{x1}" y2="{y+150}" stroke="#374151" stroke-width="2"/><text x="550" y="{y+180}" text-anchor="middle" font-size="24">L = {span:.3f} m</text><text x="40" y="550" font-size="20">Section: {values.get('width_mm','?')} x {values.get('height_mm','?')} mm | Concrete: {escape(str(values.get('concrete_class','?')))} | Steel: {escape(str(values.get('reinforcement_class','?')))} | Cover: {values.get('nominal_cover_mm','?')} mm</text><text x="40" y="590" font-size="17" fill="#b45309">Recognition candidates must be confirmed before calculation. Final structural release always requires local engineer approval.</text></svg>"""
