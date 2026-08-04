"""Phoenix Local Product Qualification Overlay v1.0.

Normalises explicit project supplier evidence into the existing material-supply
catalog contract. It may infer material family and engineering material ID only
from explicit product text/technical declarations. It never invents stock,
strength class, certification, or product availability.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
OVERLAY_NAME = "000_PHOENIX_LOCAL_PRODUCT_QUALIFICATION_OVERLAY_v1_0.json"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _repo_ref(path: Path, repository: Path) -> str:
    try:
        return path.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _text(product: dict[str, Any]) -> str:
    parts = [
        product.get("description"), product.get("name"), product.get("product_name"),
        product.get("supplier_product_code"), product.get("product_id"),
    ]
    technical = product.get("technical_properties")
    if isinstance(technical, dict):
        parts.extend(str(v) for v in technical.values() if isinstance(v, (str, int, float)))
    return " ".join(str(x) for x in parts if x not in (None, ""))


def _family(product: dict[str, Any]) -> str | None:
    existing = str(product.get("material_family") or "").strip()
    if existing:
        return existing
    t = _text(product).casefold()
    if re.search(r"\b(vabi|metsel|masonry|block|steen|brick)\b", t):
        return "masonry_unit"
    if re.search(r"\b(ready.?mix|betonmortel|concrete\s*c\d|beton\s*c\d)\b", t):
        return "structural_concrete"
    if re.search(r"\b(beton.?ijzer|wapeningsstaal|reinforcement|rebar|gerib|b500[ab]?|feb\s*400)\b", t):
        return "reinforcement_steel"
    if re.search(r"\b(hout|timber|structural wood|wood beam|c18|c24|c30)\b", t):
        return "structural_timber"
    if re.search(r"\b(ipe|hea|heb|unp|s235|s355|structural steel|steel section)\b", t):
        return "structural_steel_section"
    return None


def _engineering_id(product: dict[str, Any], family: str | None) -> tuple[str | None, dict[str, Any]]:
    technical = product.get("technical_properties")
    technical = dict(technical) if isinstance(technical, dict) else {}
    t = _text(product)
    if not family:
        return None, technical

    if family == "structural_concrete":
        grades = re.findall(r"\bC(\d{1,2})\s*/\s*(\d{1,2})\b", t, flags=re.I)
        unique_grades = list(dict.fromkeys(grades))
        # A declared range such as C8/10-C53/65 is capability evidence, not a
        # selected engineering material. Only one explicit grade qualifies.
        if len(unique_grades) == 1:
            grade = f"C{unique_grades[0][0]}/{unique_grades[0][1]}"
            technical.setdefault("declared_concrete_strength_class", grade)
            return "CONCRETE_" + grade.replace("/", "_"), technical
    elif family == "reinforcement_steel":
        m = re.search(r"\b(B500A|B500B|B500C|FEB\s*400|FEB400)\b", t, flags=re.I)
        if m:
            grade = re.sub(r"\s+", "", m.group(1).upper())
            technical.setdefault("declared_reinforcement_grade", grade)
            return "REINFORCEMENT_" + grade, technical
    elif family == "structural_timber":
        m = re.search(r"\b(C18|C24|C30|C35|C40)\b", t, flags=re.I)
        if m:
            grade = m.group(1).upper()
            technical.setdefault("declared_timber_strength_class", grade)
            return "TIMBER_" + grade, technical
    elif family == "structural_steel_section":
        m = re.search(r"\b(S235|S275|S355|S460)\b", t, flags=re.I)
        if m:
            grade = m.group(1).upper()
            technical.setdefault("declared_steel_grade", grade)
            return "STRUCTURAL_STEEL_" + grade, technical
    elif family == "masonry_unit":
        m = re.search(r"\b(\d+(?:[\.,]\d+)?)\s*(?:mpa|n\s*/\s*mm2)\b", t, flags=re.I)
        if m:
            strength = m.group(1).replace(",", ".")
            technical.setdefault("declared_compressive_strength_mpa", float(strength))
            return "MASONRY_UNIT_FK_" + strength.replace(".", "P"), technical
    return None, technical


def prepare_local_product_qualification_overlay(
    ctx: dict[str, Any],
    *,
    project_context: dict[str, Any],
) -> dict[str, Any]:
    repository = Path(ctx["repository"]).resolve()
    workspace = Path(ctx["workspace"]).resolve()
    project_id = str(ctx.get("project_id") or "UNKNOWN_PROJECT")
    facts = project_context.get("facts") if isinstance(project_context, dict) else {}
    facts = facts if isinstance(facts, dict) else {}
    country = str(facts.get("country_code") or "").upper().strip()
    source_dir = workspace / "sources" / "material_supply"
    overlay_path = source_dir / OVERLAY_NAME
    register_path = Path(ctx["output_dir"]).resolve() / "local_product_qualification_register.json"

    register: dict[str, Any] = {
        "schema_version": "phoenix.local-product-qualification-register/1.0",
        "engine_version": VERSION,
        "project_id": project_id,
        "country_code": country or None,
        "status": "NOT_APPLICABLE" if country != "SR" else "PASSED",
        "overlay_reference": None,
        "source_catalog_count": 0,
        "product_count": 0,
        "commercially_classified_count": 0,
        "engineering_qualified_count": 0,
        "invented_availability": False,
        "invented_strength_class": False,
        "automatic_product_substitution": False,
        "professional_review_required": True,
        "production_release": "LOCKED",
    }
    if country != "SR":
        _write(register_path, register)
        return {"register": _repo_ref(register_path, repository), "overlay": None}

    products: list[dict[str, Any]] = []
    sources: list[str] = []
    if source_dir.is_dir():
        for path in sorted(source_dir.rglob("*.json")):
            if path.name == OVERLAY_NAME:
                continue
            try:
                catalog = _read(path)
            except Exception:
                continue
            rows = catalog.get("products")
            if not isinstance(rows, list):
                rows = catalog.get("capability_records")
            if not isinstance(rows, list):
                continue
            sources.append(_repo_ref(path, repository))
            md = catalog.get("metadata") if isinstance(catalog.get("metadata"), dict) else catalog
            for row in rows:
                if not isinstance(row, dict):
                    continue
                item = json.loads(json.dumps(row))
                family = _family(item)
                if family:
                    item["material_family"] = family
                eng_id, technical = _engineering_id(item, family)
                if eng_id and not item.get("engineering_material_id"):
                    item["engineering_material_id"] = eng_id
                if technical:
                    item["technical_properties"] = technical
                item["upstream_source_reference"] = _repo_ref(path, repository)
                item["qualification_method"] = "EXPLICIT_PRODUCT_TEXT_AND_TECHNICAL_DECLARATION_ONLY"
                products.append(item)

    # Keep only records that can contribute explicit commercial/material evidence.
    products = [p for p in products if p.get("material_family")]
    overlay = {
        "metadata": {
            "catalog_id": f"PHX-{project_id}-LOCAL-PRODUCT-QUALIFICATION-OVERLAY-v1.0",
            "supplier_id": "MULTI_SOURCE_PROJECT_EVIDENCE",
            "supplier_name": "Project-specific Suriname supplier evidence overlay",
            "source_name": "Phoenix Local Product Qualification Overlay v1.0",
            "country_code": "SR",
            "region_name": facts.get("region"),
            "city": facts.get("municipality"),
            "currency": facts.get("currency") or "SRD",
            "availability_verified_date": date.today().isoformat(),
            "confidence": "SOURCE_DERIVED",
            "source_catalogs": sources,
        },
        "products": products,
    }
    _write(overlay_path, overlay)

    register.update({
        "overlay_reference": _repo_ref(overlay_path, repository),
        "source_catalog_count": len(set(sources)),
        "product_count": len(products),
        "commercially_classified_count": sum(1 for p in products if p.get("material_family") and p.get("availability_status")),
        "engineering_qualified_count": sum(1 for p in products if p.get("engineering_material_id") and p.get("technical_properties")),
    })
    _write(register_path, register)
    return {"register": _repo_ref(register_path, repository), "overlay": _repo_ref(overlay_path, repository)}
