from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PHOENIX_IFC_CANONICAL_IDENTITY_MANIFEST_V1"


def _unique(items: list[Any], expected_name: str, kind: str) -> Any:
    found = [item for item in items if getattr(item, "Name", None) == expected_name]
    if len(found) != 1:
        raise ValueError(f"R15_IDENTITY_{kind}_COUNT:{expected_name}:{len(found)}")
    if not getattr(found[0], "GlobalId", None):
        raise ValueError(f"R15_IDENTITY_{kind}_NO_GLOBAL_ID:{expected_name}")
    return found[0]


def build_manifest(model: Any, layout: Mapping[str, Any], ifc_path: Path) -> dict[str, Any]:
    """Bind authored canonical IDs to IFC GlobalIds using exact names AND IFC relationships.

    A model identity record does not assert structural role, swing direction, or approval.
    """
    walls = list(model.by_type("IfcWall"))
    openings = list(model.by_type("IfcOpeningElement"))
    fills = list(model.by_type("IfcDoor")) + list(model.by_type("IfcWindow"))
    voids = list(model.by_type("IfcRelVoidsElement"))
    filling_rels = list(model.by_type("IfcRelFillsElement"))
    source_walls = list(layout["walls"])
    source_ops = list(layout["openings"])
    if len({w["wall_key"] for w in source_walls}) != len(source_walls):
        raise ValueError("R15_DUPLICATE_SOURCE_WALL_KEYS")
    if len({op["opening_id"] for op in source_ops}) != len(source_ops):
        raise ValueError("R15_DUPLICATE_SOURCE_OPENING_IDS")
    wall_records = []
    wall_by_key = {}
    for wall in source_walls:
        key = str(wall["wall_key"])
        name = ("External" if wall["external"] else "Internal") + " " + key
        ent = _unique(walls, name, "WALL")
        wall_by_key[key] = ent
        wall_records.append({"wall_key": key, "ifc_global_id": ent.GlobalId, "ifc_name": name,
                             "storey_index": int(wall["storey_index"]),
                             "structural_role": "NOT_VERIFIED"})
    opening_records = []
    for op in source_ops:
        oid = str(op["opening_id"])
        key = str(op["host_wall_key"])
        if key not in wall_by_key:
            raise ValueError("R15_HOST_WALL_MISSING:" + oid)
        opening = _unique(openings, oid, "OPENING")
        suffix = "_DOOR" if op["kind"] == "door" else "_WINDOW"
        filler = _unique(fills, oid + suffix, "FILLER")
        v = [rel for rel in voids if rel.RelatedOpeningElement == opening
             and rel.RelatingBuildingElement == wall_by_key[key]]
        f = [rel for rel in filling_rels if rel.RelatingOpeningElement == opening
             and rel.RelatedBuildingElement == filler]
        if len(v) != 1 or len(f) != 1:
            raise ValueError(f"R15_IFC_RELATION_MISMATCH:{oid}:voids={len(v)}:fills={len(f)}")
        opening_records.append({"opening_id": oid, "host_wall_key": key,
                                "opening_ifc_global_id": opening.GlobalId,
                                "filler_ifc_global_id": filler.GlobalId,
                                "filler_ifc_class": filler.is_a(),
                                "ifc_relation_verified": True,
                                "door_swing": "NOT_VERIFIED"})
    ifc_hash = hashlib.sha256(Path(ifc_path).read_bytes()).hexdigest()
    return {"schema": SCHEMA, "variant_id": str(layout["variant_id"]),
            "ifc_sha256": ifc_hash, "walls": wall_records, "openings": opening_records,
            "wall_count": len(wall_records), "opening_count": len(opening_records),
            "identity_only": True, "structural_approval": False,
            "door_clearance_approval": False, "geometry_repair_authorized": False,
            "programme_acceptance": "OPEN", "production_release": "LOCKED"}


def write_manifest(model: Any, layout: Mapping[str, Any], ifc_path: Path) -> tuple[Path, dict[str, Any]]:
    data = build_manifest(model, layout, ifc_path)
    path = Path(str(ifc_path) + ".identity.json")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path, data
