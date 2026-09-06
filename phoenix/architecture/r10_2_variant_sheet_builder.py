from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List
import json


def build_variant_sheet(variant_code: str, design: Dict[str, Any], evaluation: Dict[str, Any], qa: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "variant_code": variant_code,
        "variant_identity": design.get("variant_identity"),
        "design_status": design.get("design_status"),
        "qa_overall_pass": qa.get("overall_pass", False),
        "review_focus": evaluation.get("review_focus", []),
        "required_views": evaluation.get("required_views", []),
        "failures": qa.get("failures", {}),
    }


def build_comparison_sheet(sheets: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for sheet in sheets:
        rows.append({
            "variant_code": sheet.get("variant_code"),
            "variant_identity": sheet.get("variant_identity"),
            "qa_overall_pass": sheet.get("qa_overall_pass"),
            "failure_count": len(sheet.get("failures", {})),
        })
    return {
        "schema": "PHOENIX_R10_2_VARIANT_COMPARISON_1.0",
        "rows": rows,
    }


def write_json(path: str | Path, payload: Dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding='utf-8')
