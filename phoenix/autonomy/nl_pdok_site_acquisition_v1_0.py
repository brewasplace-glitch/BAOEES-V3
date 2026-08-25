"""Project Phoenix NL PDOK Site Acquisition Bridge v1.0.

Extends the existing site/parcel intelligence path with Netherlands-only open-data
acquisition when project input contains an explicit location but no validated site
geometry.

Primary chain:
- PDOK Location API (address geocoding)
- BRK Kadastrale Kaart OGC API (indicative parcel geometry)

Fallback/context:
- PDOK Locatieserver (address geocoding fallback)
- BAG OGC API (building context)

Safety:
- never treats BRK map geometry as a legal/cadastral validation;
- never invents a parcel when containment is ambiguous;
- network/source failure returns the existing site context unchanged;
- professional approval and production release remain locked.
"""

from __future__ import annotations

import copy
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

VERSION = "1.0.0"
USER_AGENT = "Project-Phoenix/4.2 NL-PDOK-Site-Acquisition-v1.0"

LOCATION_API = "https://api.pdok.nl/kadaster/location-api/v1/search"
LOCATIESERVER = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
BRK_PARCELS = "https://api.pdok.nl/kadaster/brk-kadastrale-kaart/ogc/v1/collections/perceel/items"
BAG_BUILDINGS = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items"


@dataclass
class PdokSiteAcquisitionResult:
    applied: bool
    status: str
    site_context: dict[str, Any]
    evidence_register: dict[str, Any]
    warnings: list[str]
    output_files: list[Path]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _fetch_json(url: str, timeout: int = 30) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/geo+json, application/json;q=0.9, */*;q=0.1",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    value = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("PDOK response root must be a JSON object")
    return value


def _query(base: str, params: list[tuple[str, str]]) -> str:
    return base + "?" + urllib.parse.urlencode(params)


def _parse_point_text(value: Any) -> tuple[float, float] | None:
    text = str(value or "").strip()
    upper = text.upper()
    if not upper.startswith("POINT") or "(" not in text or ")" not in text:
        return None
    body = text[text.find("(") + 1 : text.find(")")].strip().split()
    if len(body) < 2:
        return None
    try:
        lon, lat = float(body[0]), float(body[1])
    except (TypeError, ValueError):
        return None
    if -180 <= lon <= 180 and -90 <= lat <= 90:
        return lon, lat
    return None


def _location_point(payload: dict[str, Any]) -> tuple[float, float, dict[str, Any]] | None:
    features = payload.get("features")
    if isinstance(features, list) and features:
        feature = features[0]
        if isinstance(feature, dict):
            geom = feature.get("geometry")
            if isinstance(geom, dict) and geom.get("type") == "Point":
                coords = geom.get("coordinates")
                if isinstance(coords, list) and len(coords) >= 2:
                    try:
                        lon, lat = float(coords[0]), float(coords[1])
                    except (TypeError, ValueError):
                        lon = lat = 999.0
                    if -180 <= lon <= 180 and -90 <= lat <= 90:
                        return lon, lat, feature
            props = feature.get("properties")
            if isinstance(props, dict):
                for key in ("centroide_ll", "centroide", "point"):
                    parsed = _parse_point_text(props.get(key))
                    if parsed:
                        return parsed[0], parsed[1], feature

    response = payload.get("response")
    if isinstance(response, dict):
        docs = response.get("docs")
        if isinstance(docs, list) and docs:
            doc = docs[0]
            if isinstance(doc, dict):
                for key in ("centroide_ll", "centroide", "point"):
                    parsed = _parse_point_text(doc.get(key))
                    if parsed:
                        return parsed[0], parsed[1], doc
    return None


def _rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    typ = geometry.get("type")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list):
        return []
    if typ == "Polygon":
        return [coords]
    if typ == "MultiPolygon":
        return [poly for poly in coords if isinstance(poly, list)]
    return []


def _point_on_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float, eps: float = 1e-12
) -> bool:
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > eps:
        return False
    return (
        min(x1, x2) - eps <= px <= max(x1, x2) + eps
        and min(y1, y2) - eps <= py <= max(y1, y2) + eps
    )


def _point_in_ring(px: float, py: float, ring: list[Any]) -> tuple[bool, bool]:
    pts: list[tuple[float, float]] = []
    for pair in ring:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            try:
                pts.append((float(pair[0]), float(pair[1])))
            except (TypeError, ValueError):
                pass
    if len(pts) < 3:
        return False, False

    inside = False
    j = len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if _point_on_segment(px, py, xi, yi, xj, yj):
            return True, True
        if (yi > py) != (yj > py):
            denom = yj - yi
            if abs(denom) > 1e-15:
                xcross = (xj - xi) * (py - yi) / denom + xi
                if px < xcross:
                    inside = not inside
        j = i
    return inside, False


def _point_in_geometry(px: float, py: float, geometry: dict[str, Any]) -> tuple[bool, bool]:
    for polygon in _rings(geometry):
        if not polygon:
            continue
        outer, boundary = _point_in_ring(px, py, polygon[0])
        if not outer:
            continue
        if boundary:
            return True, True
        in_hole = False
        for hole in polygon[1:]:
            hit, hole_boundary = _point_in_ring(px, py, hole)
            if hole_boundary:
                return True, True
            if hit:
                in_hole = True
                break
        if not in_hole:
            return True, False
    return False, False


def _geometry_points(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for polygon in _rings(geometry):
        for ring in polygon:
            for pair in ring:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    try:
                        points.append((float(pair[0]), float(pair[1])))
                    except (TypeError, ValueError):
                        pass
    return points


def _bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    points = _geometry_points(geometry)
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _dimensions_m(
    geometry: dict[str, Any], latitude: float
) -> tuple[float, float] | None:
    bbox = _bbox(geometry)
    if not bbox:
        return None
    minx, miny, maxx, maxy = bbox
    width = (maxx - minx) * 111320.0 * math.cos(math.radians(latitude))
    depth = (maxy - miny) * 110540.0
    if width <= 0 or depth <= 0:
        return None
    return round(width, 3), round(depth, 3)


def _outer_boundary(geometry: dict[str, Any]) -> list[list[float]] | None:
    polygons = _rings(geometry)
    if not polygons or not polygons[0]:
        return None
    ring = polygons[0][0]
    result: list[list[float]] = []
    for pair in ring:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            try:
                result.append([float(pair[0]), float(pair[1])])
            except (TypeError, ValueError):
                pass
    return result if len(result) >= 3 else None


def _country_code(project_context: dict[str, Any]) -> str:
    facts = project_context.get("facts")
    if isinstance(facts, dict):
        value = facts.get("country_code")
        if value:
            return str(value).strip().upper()
    value = project_context.get("country_code")
    return str(value or "").strip().upper()


def _location(project_context: dict[str, Any]) -> str:
    facts = project_context.get("facts")
    if isinstance(facts, dict):
        for key in ("project_location", "address", "location"):
            value = facts.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("project_location", "address", "location"):
        value = project_context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def acquire_nl_pdok_site_evidence(
    *,
    project_id: str,
    project_context: dict[str, Any],
    base_site_context: dict[str, Any],
    existing_evidence_register: dict[str, Any] | None,
    output_dir: Path,
    fetch_json: Callable[[str], dict[str, Any]] | None = None,
) -> PdokSiteAcquisitionResult:
    """Acquire an indicative NL parcel candidate only when containment is unambiguous."""

    base = copy.deepcopy(base_site_context)
    register = copy.deepcopy(existing_evidence_register or {})
    warnings: list[str] = []
    output_files: list[Path] = []

    if _country_code(project_context) != "NL":
        return PdokSiteAcquisitionResult(
            False, "NOT_APPLICABLE_COUNTRY", base, register, warnings, output_files
        )
    if str(base.get("status") or "") != "SCHEMATIC_ASSUMPTION":
        return PdokSiteAcquisitionResult(
            False, "EXISTING_SITE_EVIDENCE_PRESERVED", base, register, warnings, output_files
        )

    location = _location(project_context)
    if not location:
        return PdokSiteAcquisitionResult(
            False, "EXPLICIT_LOCATION_REQUIRED", base, register, warnings, output_files
        )

    fetch = fetch_json or _fetch_json
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    location_payload: dict[str, Any] | None = None
    point: tuple[float, float, dict[str, Any]] | None = None
    geocoder = "PDOK_LOCATION_API"

    primary_url = _query(
        LOCATION_API,
        [
            ("q", location),
            ("adres[version]", "1"),
            ("adres[relevance]", "0.8"),
            ("limit", "10"),
            ("f", "geojson"),
        ],
    )
    try:
        location_payload = fetch(primary_url)
        point = _location_point(location_payload)
    except Exception as exc:
        warnings.append(f"PDOK_LOCATION_API_FAILED:{type(exc).__name__}:{exc}")

    if point is None:
        geocoder = "PDOK_LOCATIESERVER_FALLBACK"
        fallback_url = _query(
            LOCATIESERVER,
            [("q", location), ("fq", "type:adres"), ("rows", "10")],
        )
        try:
            location_payload = fetch(fallback_url)
            point = _location_point(location_payload)
        except Exception as exc:
            warnings.append(f"PDOK_LOCATIESERVER_FAILED:{type(exc).__name__}:{exc}")

    if point is None or location_payload is None:
        warnings.append("PDOK_ADDRESS_GEOCODE_UNRESOLVED")
        return PdokSiteAcquisitionResult(
            False, "GEOCODE_UNRESOLVED", base, register, warnings, output_files
        )

    lon, lat, location_feature = point
    location_path = out / "pdok_location_evidence.geojson"
    _write_json(location_path, location_payload)
    output_files.append(location_path)

    delta = 0.001
    bbox = ",".join(
        f"{value:.12f}"
        for value in (lon - delta, lat - delta, lon + delta, lat + delta)
    )
    parcel_url = _query(
        BRK_PARCELS,
        [("bbox", bbox), ("limit", "100"), ("f", "json")],
    )
    try:
        parcel_payload = fetch(parcel_url)
    except Exception as exc:
        warnings.append(f"PDOK_BRK_REQUEST_FAILED:{type(exc).__name__}:{exc}")
        return PdokSiteAcquisitionResult(
            False, "BRK_REQUEST_FAILED", base, register, warnings, output_files
        )

    parcel_path = out / "pdok_brk_parcel_bbox_evidence.geojson"
    _write_json(parcel_path, parcel_payload)
    output_files.append(parcel_path)

    features = parcel_payload.get("features")
    if not isinstance(features, list):
        features = []

    containing: list[dict[str, Any]] = []
    boundary_hits = 0
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            continue
        hit, boundary = _point_in_geometry(lon, lat, geometry)
        if hit:
            containing.append(feature)
            if boundary:
                boundary_hits += 1

    if len(containing) != 1 or boundary_hits:
        warnings.append(
            f"PDOK_BRK_CONTAINMENT_NOT_UNAMBIGUOUS:count={len(containing)}:boundary_hits={boundary_hits}"
        )
        return PdokSiteAcquisitionResult(
            False, "AMBIGUOUS_OR_NO_CONTAINING_PARCEL", base, register, warnings, output_files
        )

    selected = containing[0]
    geometry = selected.get("geometry") or {}
    dims = _dimensions_m(geometry, lat)
    boundary = _outer_boundary(geometry)
    if not dims or not boundary:
        warnings.append("PDOK_BRK_SELECTED_PARCEL_GEOMETRY_INVALID")
        return PdokSiteAcquisitionResult(
            False, "SELECTED_PARCEL_GEOMETRY_INVALID", base, register, warnings, output_files
        )

    selected_path = out / "pdok_selected_parcel.geojson"
    _write_json(selected_path, {"type": "FeatureCollection", "features": [selected]})
    output_files.append(selected_path)

    # BAG is corroborating context only. Failure never invalidates the BRK parcel candidate.
    bag_containing: list[dict[str, Any]] = []
    bag_url = _query(
        BAG_BUILDINGS,
        [("bbox", bbox), ("limit", "100"), ("f", "json")],
    )
    try:
        bag_payload = fetch(bag_url)
        bag_path = out / "pdok_bag_building_bbox_evidence.geojson"
        _write_json(bag_path, bag_payload)
        output_files.append(bag_path)
        bag_features = bag_payload.get("features")
        if isinstance(bag_features, list):
            for feature in bag_features:
                if not isinstance(feature, dict):
                    continue
                geom = feature.get("geometry")
                if isinstance(geom, dict) and _point_in_geometry(lon, lat, geom)[0]:
                    bag_containing.append(feature)
        if len(bag_containing) == 1:
            bag_selected_path = out / "pdok_selected_bag_building.geojson"
            _write_json(
                bag_selected_path,
                {"type": "FeatureCollection", "features": bag_containing},
            )
            output_files.append(bag_selected_path)
    except Exception as exc:
        warnings.append(f"PDOK_BAG_CONTEXT_FAILED:{type(exc).__name__}:{exc}")

    width_m, depth_m = dims
    site = copy.deepcopy(base)
    site["schema_version"] = "phoenix.site-context/1.2"
    site["status"] = "PDOK_BRK_SITE_EVIDENCE"
    site["location"] = location
    site["site_evidence_source"] = "PDOK_BRK_KADASTRALE_KAART_OGC_API"
    site["site_evidence_type"] = "OPEN_DATA_INDICATIVE_PARCEL_GEOMETRY"
    site["plot"] = {
        "width_m": width_m,
        "depth_m": depth_m,
        "source": "PDOK_BRK_KADASTRALE_KAART_INDICATIVE",
        "legal_boundary": False,
        "boundary_coordinates": boundary,
    }
    site["orientation"] = {
        "value": "NORTH_UP_GEOGRAPHIC",
        "north_angle_deg": 0.0,
        "source": "CRS84_GEOGRAPHIC_NORTH",
    }
    site["cadastral_validation"] = False
    site["planning_validation"] = False
    site["professional_review_required"] = True
    site["production_release"] = "LOCKED"

    props = selected.get("properties")
    if not isinstance(props, dict):
        props = {}
    parcel_identity = {
        "kadastrale_gemeente_waarde": props.get("kadastrale_gemeente_waarde"),
        "kadastrale_gemeente_code": props.get("kadastrale_gemeente_code"),
        "sectie": props.get("sectie"),
        "perceelnummer": props.get("perceelnummer"),
        "kadastrale_grootte_waarde": props.get("kadastrale_grootte_waarde"),
    }

    evidence = register.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    evidence.append(
        {
            "source": "PDOK / Kadaster",
            "dataset": "BRK Kadastrale Kaart",
            "collection": "perceel",
            "status": "PARSED_AND_ADDRESS_POINT_CONTAINMENT_CONFIRMED",
            "geocoder": geocoder,
            "location_query": location,
            "address_point": {"longitude": lon, "latitude": lat},
            "parcel_identity": parcel_identity,
            "license": "CC BY 4.0",
            "legal_boundary": False,
            "cadastral_validation": False,
            "planning_validation": False,
            "professional_review_required": True,
        }
    )

    if len(bag_containing) == 1:
        bag_props = bag_containing[0].get("properties")
        if not isinstance(bag_props, dict):
            bag_props = {}
        evidence.append(
            {
                "source": "PDOK / Kadaster",
                "dataset": "BAG",
                "collection": "pand",
                "status": "ADDRESS_POINT_BUILDING_CONTAINMENT_CONFIRMED",
                "building_identification": bag_props.get("identificatie"),
                "building_status": bag_props.get("status"),
                "legal_boundary": False,
                "professional_review_required": True,
            }
        )

    register.update(
        {
            "schema_version": "phoenix.site-parcel-evidence-register/1.1",
            "engine_version": VERSION,
            "project_id": project_id,
            "evidence": evidence,
            "warnings": list(register.get("warnings") or []) + warnings,
            "selected_source": "PDOK_BRK_KADASTRALE_KAART_OGC_API",
            "selected_parcel": parcel_identity,
            "address_point_containment_confirmed": True,
            "cadastral_validation": False,
            "planning_validation": False,
            "automatic_legal_boundary_claim": False,
            "professional_review_required": True,
            "production_release": "LOCKED",
            "acquired_utc": datetime.now(timezone.utc).isoformat(),
        }
    )

    return PdokSiteAcquisitionResult(
        True,
        "PDOK_BRK_CONTAINING_PARCEL_CONFIRMED",
        site,
        register,
        warnings,
        output_files,
    )
