from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict


def _imports():
    import numpy as np
    import ifcopenshell
    import ifcopenshell.api.aggregate
    import ifcopenshell.api.context
    import ifcopenshell.api.feature
    import ifcopenshell.api.geometry
    import ifcopenshell.api.project
    import ifcopenshell.api.root
    import ifcopenshell.api.spatial
    import ifcopenshell.api.unit
    return np, ifcopenshell


def _matrix(np, x: float, y: float, z: float, angle_deg: float = 0.0):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    m = np.identity(4)
    m[0, 0] = c
    m[0, 1] = -s
    m[1, 0] = s
    m[1, 1] = c
    m[0, 3] = x
    m[1, 3] = y
    m[2, 3] = z
    return m


def author_ifc4(project: Dict[str, Any], layout: Dict[str, Any], output_path: Path) -> Dict[str, Any]:
    np, ifcopenshell = _imports()
    import ifcopenshell.api.aggregate
    import ifcopenshell.api.context
    import ifcopenshell.api.feature
    import ifcopenshell.api.geometry
    import ifcopenshell.api.project
    import ifcopenshell.api.root
    import ifcopenshell.api.spatial
    import ifcopenshell.api.unit

    model = ifcopenshell.api.project.create_file(version="IFC4")
    ifc_project = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcProject", name=f"PROJECT PHOENIX {project['project_id']}"
    )
    ifcopenshell.api.unit.assign_unit(model)

    model_context = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        model, context_type="Model", context_identifier="Body",
        target_view="MODEL_VIEW", parent=model_context
    )

    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Project Site")
    building = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcBuilding",
        name=f"Tropical Residential Variant {layout['variant_id']}"
    )
    ifcopenshell.api.aggregate.assign_object(model, relating_object=ifc_project, products=[site])
    ifcopenshell.api.aggregate.assign_object(model, relating_object=site, products=[building])

    raised = float(layout["elevation"]["raised_floor_m"])
    storey_h = float(layout["storey_height_m"])
    storeys = []
    for s in range(int(layout["storeys"])):
        storey = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcBuildingStorey", name=f"Storey {s+1}"
        )
        ifcopenshell.api.aggregate.assign_object(model, relating_object=building, products=[storey])
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=storey, matrix=_matrix(np, 0, 0, raised + s*storey_h)
        )
        storeys.append(storey)

    # Floor slabs.
    fw = float(layout["footprint"]["width_m"])
    fd = float(layout["footprint"]["depth_m"])
    footprint_polyline = [(0.0, 0.0), (fw, 0.0), (fw, fd), (0.0, fd)]
    slab_count = 0
    for s, storey in enumerate(storeys):
        slab = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcSlab", predefined_type="FLOOR", name=f"Floor Slab S{s+1}"
        )
        rep = ifcopenshell.api.geometry.add_slab_representation(
            model, context=body, depth=0.20, polyline=footprint_polyline
        )
        ifcopenshell.api.geometry.assign_representation(model, product=slab, representation=rep)
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=slab, matrix=_matrix(np, 0, 0, raised + s*storey_h - 0.20)
        )
        ifcopenshell.api.spatial.assign_container(model, relating_structure=storey, products=[slab])
        slab_count += 1

    # Walls.
    wall_entities = {}
    wall_meta = {}
    for wall in layout["walls"]:
        s = int(wall["storey_index"])
        x1, y1, x2, y2 = map(float, (wall["x1"], wall["y1"], wall["x2"], wall["y2"]))
        length = math.hypot(x2-x1, y2-y1)
        angle = math.degrees(math.atan2(y2-y1, x2-x1))
        thickness = float(wall["thickness_m"])
        ent = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcWall",
            name=("External" if wall["external"] else "Internal") + " " + wall["wall_key"]
        )
        rep = ifcopenshell.api.geometry.add_wall_representation(
            model, context=body, length=length, height=storey_h,
            thickness=thickness
        )
        ifcopenshell.api.geometry.assign_representation(model, product=ent, representation=rep)
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=ent,
            matrix=_matrix(np, x1, y1, raised + s*storey_h, angle)
        )
        ifcopenshell.api.spatial.assign_container(model, relating_structure=storeys[s], products=[ent])
        wall_entities[wall["wall_key"]] = ent
        wall_meta[wall["wall_key"]] = {
            "x1": x1, "y1": y1, "angle": angle, "thickness": thickness, "storey": s
        }

    # Spatial rooms as real 3D IfcSpace volumes.
    space_count = 0
    for room in layout["rooms"]:
        s = int(room["storey_index"])
        space = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcSpace", name=room["name"]
        )
        rep = ifcopenshell.api.geometry.add_wall_representation(
            model, context=body,
            length=float(room["width"]), height=storey_h-0.10,
            thickness=float(room["depth"])
        )
        ifcopenshell.api.geometry.assign_representation(model, product=space, representation=rep)
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=space,
            matrix=_matrix(np, float(room["x"]), float(room["y"]), raised + s*storey_h)
        )
        ifcopenshell.api.aggregate.assign_object(model, relating_object=storeys[s], products=[space])
        space_count += 1

    # Real opening + filling relationships for doors and windows.
    door_count = window_count = opening_count = 0
    for op in layout["openings"]:
        host = wall_entities.get(op["host_wall_key"])
        if host is None:
            continue
        meta = wall_meta[op["host_wall_key"]]
        s = int(op["storey_index"])
        opening = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcOpeningElement", name=op["opening_id"]
        )
        rep = ifcopenshell.api.geometry.add_wall_representation(
            model, context=body, length=float(op["width_m"]),
            height=float(op["height_m"]), thickness=float(meta["thickness"]) + 0.10
        )
        ifcopenshell.api.geometry.assign_representation(model, product=opening, representation=rep)
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=opening,
            matrix=_matrix(
                np, float(op["x"]), float(op["y"]),
                raised + s*storey_h + float(op["sill_m"]), float(op["angle_deg"])
            )
        )
        ifcopenshell.api.feature.add_feature(model, feature=opening, element=host)
        opening_count += 1

        if op["kind"] == "door":
            filler = ifcopenshell.api.root.create_entity(
                model, ifc_class="IfcDoor", name=op["opening_id"] + "_DOOR"
            )
            door_count += 1
        else:
            filler = ifcopenshell.api.root.create_entity(
                model, ifc_class="IfcWindow", name=op["opening_id"] + "_WINDOW"
            )
            window_count += 1

        fill_rep = ifcopenshell.api.geometry.add_wall_representation(
            model, context=body, length=float(op["width_m"]),
            height=float(op["height_m"]), thickness=0.05
        )
        ifcopenshell.api.geometry.assign_representation(model, product=filler, representation=fill_rep)
        ifcopenshell.api.geometry.edit_object_placement(
            model, product=filler,
            matrix=_matrix(
                np, float(op["x"]), float(op["y"]),
                raised + s*storey_h + float(op["sill_m"]), float(op["angle_deg"])
            )
        )
        ifcopenshell.api.feature.add_filling(model, opening=opening, element=filler)
        ifcopenshell.api.spatial.assign_container(model, relating_structure=storeys[s], products=[filler])

    # Simplified roof volume: authoritative metadata carries the intended tropical pitch.
    roof = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcRoof", name=f"Tropical Roof pitch {layout['roof']['pitch_deg']} deg"
    )
    roof_rep = ifcopenshell.api.geometry.add_slab_representation(
        model, context=body, depth=0.20,
        polyline=[
            (-float(layout["roof"]["eave_overhang_m"]), -float(layout["roof"]["eave_overhang_m"])),
            (fw+float(layout["roof"]["eave_overhang_m"]), -float(layout["roof"]["eave_overhang_m"])),
            (fw+float(layout["roof"]["eave_overhang_m"]), fd+float(layout["roof"]["eave_overhang_m"])),
            (-float(layout["roof"]["eave_overhang_m"]), fd+float(layout["roof"]["eave_overhang_m"])),
        ]
    )
    ifcopenshell.api.geometry.assign_representation(model, product=roof, representation=roof_rep)
    ifcopenshell.api.geometry.edit_object_placement(
        model, product=roof,
        matrix=_matrix(np, 0, 0, raised + len(storeys)*storey_h)
    )
    ifcopenshell.api.spatial.assign_container(model, relating_structure=storeys[-1], products=[roof])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(output_path))

    reopened = ifcopenshell.open(str(output_path))
    evidence = {
        "ifc_schema": reopened.schema,
        "ifc_file": str(output_path),
        "bytes": output_path.stat().st_size,
        "IfcProject": len(reopened.by_type("IfcProject")),
        "IfcSite": len(reopened.by_type("IfcSite")),
        "IfcBuilding": len(reopened.by_type("IfcBuilding")),
        "IfcBuildingStorey": len(reopened.by_type("IfcBuildingStorey")),
        "IfcWall": len(reopened.by_type("IfcWall")),
        "IfcSpace": len(reopened.by_type("IfcSpace")),
        "IfcSlab": len(reopened.by_type("IfcSlab")),
        "IfcRoof": len(reopened.by_type("IfcRoof")),
        "IfcOpeningElement": len(reopened.by_type("IfcOpeningElement")),
        "IfcDoor": len(reopened.by_type("IfcDoor")),
        "IfcWindow": len(reopened.by_type("IfcWindow")),
        "release_status": "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION",
    }
    return evidence
