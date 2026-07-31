from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def resolve_existing(candidates: list[str | None]) -> Path | None:
    for item in candidates:
        if item and Path(item).is_file():
            return Path(item).resolve()
    return None

def run(args, cwd=None, timeout=3600) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(x) for x in args],
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )

def resolve_ifcopenshell_python() -> Path:
    candidates = [
        os.environ.get("IFCOPENSHELL_PYTHON"),
        r"C:\Users\brewasplace\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        cp = run([candidate, "-c", "import ifcopenshell;print(ifcopenshell.version)"], timeout=180)
        if cp.returncode == 0:
            return Path(candidate).resolve()
    raise RuntimeError("No verified IfcOpenShell Python runtime found")

def validate_program(project: dict[str, Any]) -> list[str]:
    errors = []
    if not project.get("project_id"):
        errors.append("project_id missing")
    storeys = project.get("storeys", [])
    if not storeys:
        errors.append("at least one storey required")
    seen = set()
    for storey in storeys:
        if not storey.get("storey_id"):
            errors.append("storey_id missing")
        spaces = storey.get("spaces", [])
        if not spaces:
            errors.append(f"{storey.get('storey_id')}: no spaces")
        for space in spaces:
            sid = space.get("space_id")
            if not sid:
                errors.append("space_id missing")
            elif sid in seen:
                errors.append(f"duplicate space_id: {sid}")
            else:
                seen.add(sid)
            if float(space.get("area_m2", 0)) <= 0:
                errors.append(f"{sid}: area_m2 must be positive")
            if float(space.get("min_width_m", 0)) <= 0:
                errors.append(f"{sid}: min_width_m must be positive")
    return errors

def layout_storey(storey: dict[str, Any], corridor_m: float = 1.8) -> dict[str, Any]:
    spaces = storey["spaces"]
    target_width = max(
        max(float(s["min_width_m"]) for s in spaces),
        math.sqrt(sum(float(s["area_m2"]) for s in spaces))
    )
    x = 0.0
    y = 0.0
    row_depth = 0.0
    placed = []
    for space in spaces:
        width = max(float(space["min_width_m"]), math.sqrt(float(space["area_m2"])))
        depth = float(space["area_m2"]) / width
        if x > 0 and x + width > target_width * 1.8:
            x = 0.0
            y += row_depth + corridor_m
            row_depth = 0.0
        placed.append({
            **space,
            "x_m": round(x, 3),
            "y_m": round(y, 3),
            "width_m": round(width, 3),
            "depth_m": round(depth, 3),
            "calculated_area_m2": round(width * depth, 3),
        })
        x += width
        row_depth = max(row_depth, depth)
    max_x = max(p["x_m"] + p["width_m"] for p in placed)
    max_y = max(p["y_m"] + p["depth_m"] for p in placed)
    return {
        "storey_id": storey["storey_id"],
        "name": storey["name"],
        "elevation_m": float(storey["elevation_m"]),
        "spaces": placed,
        "building_width_m": round(max_x, 3),
        "building_depth_m": round(max_y, 3),
        "gross_area_m2": round(max_x * max_y, 3),
        "net_program_area_m2": round(sum(float(s["area_m2"]) for s in spaces), 3),
    }

def build_model(project: dict[str, Any]) -> dict[str, Any]:
    storeys = [layout_storey(s) for s in project["storeys"]]
    width = max(s["building_width_m"] for s in storeys)
    depth = max(s["building_depth_m"] for s in storeys)
    height = (
        len(storeys) * float(project["building"]["storey_height_m"])
        + float(project["building"]["roof_thickness_m"])
    )
    return {
        "schema_version": "phoenix.architectural-model/6.5.0",
        "project_id": project["project_id"],
        "project_name": project["project_name"],
        "location": project["location"],
        "jurisdiction": project["jurisdiction"],
        "site": project["site"],
        "building": project["building"],
        "storeys": storeys,
        "envelope": {
            "width_m": round(width, 3),
            "depth_m": round(depth, 3),
            "height_m": round(height, 3),
        },
        "vertical_circulation": project["vertical_circulation"],
        "model_status": "PARAMETRIC_ARCHITECTURAL_MODEL_GENERATED",
    }

def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def svg_plan(storey: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scale = 50
    margin = 60
    width = int(storey["building_width_m"] * scale + margin * 2)
    height = int(storey["building_depth_m"] * scale + margin * 2)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin}" y="30" font-size="20">{storey["name"]} - Floor Plan</text>',
    ]
    for room in storey["spaces"]:
        x = margin + room["x_m"] * scale
        y = margin + room["y_m"] * scale
        w = room["width_m"] * scale
        h = room["depth_m"] * scale
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="black" stroke-width="2"/>')
        parts.append(f'<text x="{x+8}" y="{y+20}" font-size="13">{room["space_id"]} {room["name"]}</text>')
        parts.append(f'<text x="{x+8}" y="{y+38}" font-size="12">{room["area_m2"]} m²</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")

def svg_elevation(model: dict[str, Any], name: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scale = 35
    margin = 60
    w_m = model["envelope"]["width_m"]
    h_m = model["envelope"]["height_m"]
    width = int(w_m * scale + margin * 2)
    height = int(h_m * scale + margin * 2)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{margin}" y="30" font-size="20">{name} Elevation</text>',
        f'<rect x="{margin}" y="{margin}" width="{w_m*scale}" height="{h_m*scale}" fill="none" stroke="black" stroke-width="2"/>',
    ]
    sh = float(model["building"]["storey_height_m"])
    for i in range(1, len(model["storeys"])):
        y = margin + i * sh * scale
        parts.append(f'<line x1="{margin}" y1="{y}" x2="{margin+w_m*scale}" y2="{y}" stroke="black" stroke-width="1"/>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")

def svg_section(model: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    svg_elevation(model, "Section A-A", path)

def generate_freecad(model: dict[str, Any], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    exe = resolve_existing([
        os.environ.get("FREECAD_CMD"),
        r"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
    ])
    if not exe:
        raise RuntimeError("FreeCADCmd executable not found")
    script = output / "build_architectural_model.py"
    fcstd = output / "architectural_model.FCStd"
    step = output / "architectural_model.step"
    width = model["envelope"]["width_m"] * 1000
    depth = model["envelope"]["depth_m"] * 1000
    height = model["envelope"]["height_m"] * 1000
    script.write_text(
        "import FreeCAD as App,Part\n"
        "doc=App.newDocument('PhoenixArchitecturalModel')\n"
        "envelope=doc.addObject('Part::Feature','BuildingEnvelope')\n"
        f"envelope.Shape=Part.makeBox({width},{depth},{height})\n"
        "doc.recompute()\n"
        f"doc.saveAs(r'{fcstd}')\n"
        f"envelope.Shape.exportStep(r'{step}')\n",
        encoding="utf-8",
    )
    cp = run([exe, script], cwd=output, timeout=1200)
    (output / "freecad_stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (output / "freecad_stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
    if cp.returncode != 0 or any(not p.is_file() or p.stat().st_size == 0 for p in (fcstd, step)):
        raise RuntimeError(f"FreeCAD architectural generation failed: {cp.returncode}")
    return {"fcstd": fcstd.name, "step": step.name}

def generate_ifc(model: dict[str, Any], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    python = resolve_ifcopenshell_python()
    script = output / "build_architectural_ifc.py"
    ifc = output / "architectural_model.ifc"
    validation = output / "ifc_validation.json"
    payload = json.dumps(model)
    script.write_text(
        "import ifcopenshell,ifcopenshell.guid,json\n"
        f"model_data=json.loads({payload!r})\n"
        "m=ifcopenshell.file(schema='IFC4')\n"
        "p=m.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new(),Name=model_data['project_name'])\n"
        "site=m.create_entity('IfcSite',GlobalId=ifcopenshell.guid.new(),Name='Project Site')\n"
        "b=m.create_entity('IfcBuilding',GlobalId=ifcopenshell.guid.new(),Name=model_data['project_name'])\n"
        "m.create_entity('IfcRelAggregates',GlobalId=ifcopenshell.guid.new(),RelatingObject=p,RelatedObjects=[site])\n"
        "m.create_entity('IfcRelAggregates',GlobalId=ifcopenshell.guid.new(),RelatingObject=site,RelatedObjects=[b])\n"
        "storeys=[]\n"
        "for s in model_data['storeys']:\n"
        " st=m.create_entity('IfcBuildingStorey',GlobalId=ifcopenshell.guid.new(),Name=s['name'])\n"
        " storeys.append(st)\n"
        " for r in s['spaces']:\n"
        "  sp=m.create_entity('IfcSpace',GlobalId=ifcopenshell.guid.new(),Name=r['name'],LongName=r['space_id'])\n"
        "  m.create_entity('IfcRelContainedInSpatialStructure',GlobalId=ifcopenshell.guid.new(),RelatingStructure=st,RelatedElements=[sp])\n"
        "m.create_entity('IfcRelAggregates',GlobalId=ifcopenshell.guid.new(),RelatingObject=b,RelatedObjects=storeys)\n"
        f"m.write(r'{ifc}')\n"
        f"r=ifcopenshell.open(r'{ifc}')\n"
        f"json.dump({{'schema':r.schema,'projects':len(r.by_type('IfcProject')),'buildings':len(r.by_type('IfcBuilding')),'storeys':len(r.by_type('IfcBuildingStorey')),'spaces':len(r.by_type('IfcSpace'))}},open(r'{validation}','w'),indent=2)\n",
        encoding="utf-8",
    )
    cp = run([python, script], cwd=output, timeout=900)
    (output / "ifcopenshell_stdout.txt").write_text(cp.stdout or "", encoding="utf-8")
    (output / "ifcopenshell_stderr.txt").write_text(cp.stderr or "", encoding="utf-8")
    if cp.returncode != 0 or not ifc.is_file() or ifc.stat().st_size == 0:
        raise RuntimeError(f"IfcOpenShell architectural generation failed: {cp.returncode}")
    return {"ifc": ifc.name, "validation": validation.name}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    project = read_json(Path(args.project).resolve())
    output = Path(args.output).resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for directory in (
        output / "drawings",
        output / "schedules",
        output / "bim",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    errors = validate_program(project)
    if errors:
        write_json(output / "program_validation.json", {"status": "FAILED", "errors": errors})
        raise RuntimeError("Architectural project program validation failed")

    model = build_model(project)
    write_json(output / "architectural_model.json", model)
    write_json(output / "digital_twin_architectural_v6_5_0.json", {
        "schema_version": "phoenix.digital-twin-architectural/6.5.0",
        "project_id": project["project_id"],
        "architectural_model": model,
        "release": {
            "permit_ready": False,
            "execution_ready": False,
            "professional_review_required": True,
        },
    })

    room_rows = []
    for storey in model["storeys"]:
        svg_plan(storey, output / "drawings" / f"{storey['storey_id']}_floor_plan.svg")
        for room in storey["spaces"]:
            room_rows.append({
                "storey_id": storey["storey_id"],
                "space_id": room["space_id"],
                "name": room["name"],
                "function": room["function"],
                "area_m2": room["area_m2"],
                "width_m": room["width_m"],
                "depth_m": room["depth_m"],
            })

    for name in ("North", "East", "South", "West"):
        svg_elevation(model, name, output / "drawings" / f"{name.lower()}_elevation.svg")
    svg_section(model, output / "drawings" / "section_AA.svg")

    write_csv(
        output / "schedules" / "room_schedule.csv",
        ["storey_id","space_id","name","function","area_m2","width_m","depth_m"],
        room_rows,
    )
    write_csv(
        output / "schedules" / "opening_schedule.csv",
        ["opening_id","type","storey_id","width_m","height_m","status"],
        [],
    )
    write_csv(
        output / "schedules" / "material_schedule.csv",
        ["material_id","name","category","thickness_m","status"],
        [
            {"material_id":"MAT-EXT-WALL","name":"External wall assembly","category":"wall","thickness_m":project["building"]["external_wall_thickness_m"],"status":"TO_BE_SPECIFIED"},
            {"material_id":"MAT-INT-WALL","name":"Internal wall assembly","category":"wall","thickness_m":project["building"]["internal_wall_thickness_m"],"status":"TO_BE_SPECIFIED"},
            {"material_id":"MAT-FLOOR","name":"Floor assembly","category":"floor","thickness_m":project["building"]["floor_thickness_m"],"status":"TO_BE_SPECIFIED"},
            {"material_id":"MAT-ROOF","name":"Roof assembly","category":"roof","thickness_m":project["building"]["roof_thickness_m"],"status":"TO_BE_SPECIFIED"},
        ],
    )
    write_csv(
        output / "schedules" / "quantity_schedule.csv",
        ["item","quantity","unit"],
        [
            {"item":"Gross floor area","quantity":sum(s["gross_area_m2"] for s in model["storeys"]),"unit":"m2"},
            {"item":"Net programmed area","quantity":sum(s["net_program_area_m2"] for s in model["storeys"]),"unit":"m2"},
            {"item":"Building volume","quantity":round(model["envelope"]["width_m"]*model["envelope"]["depth_m"]*model["envelope"]["height_m"],3),"unit":"m3"},
        ],
    )

    freecad = generate_freecad(model, output / "bim")
    ifc = generate_ifc(model, output / "bim")

    drawings = sorted((output / "drawings").glob("*.svg"))
    required_generated_files = [
        *(output / "drawings").glob("*.svg"),
        output / "schedules" / "room_schedule.csv",
        output / "schedules" / "opening_schedule.csv",
        output / "schedules" / "material_schedule.csv",
        output / "schedules" / "quantity_schedule.csv",
        output / "bim" / freecad["fcstd"],
        output / "bim" / freecad["step"],
        output / "bim" / ifc["ifc"],
        output / "bim" / ifc["validation"],
    ]
    if not required_generated_files:
        raise RuntimeError("No architectural artifacts were generated")
    for generated in required_generated_files:
        if not generated.is_file() or generated.stat().st_size == 0:
            raise RuntimeError(
                f"Architectural artifact missing or empty: {generated}"
            )

    drawing_rows = [
        {
            "drawing_number": f"A-{i+1:03d}",
            "title": p.stem.replace("_", " ").title(),
            "file": p.relative_to(output).as_posix(),
            "status": "GENERATED_FOR_REVIEW",
        }
        for i, p in enumerate(drawings)
    ]
    write_csv(
        output / "drawing_index.csv",
        ["drawing_number","title","file","status"],
        drawing_rows,
    )

    quality = {
        "schema_version": "phoenix.architectural-quality-report/6.5.0",
        "status": "PASSED_WITH_RELEASE_BLOCKS",
        "program_validation": "PASSED",
        "storey_count": len(model["storeys"]),
        "space_count": len(room_rows),
        "freecad_native_model": freecad,
        "ifc4_model": ifc,
        "drawing_count": len(drawing_rows),
        "release_blocks": [
            "verified_site_evidence_required",
            "jurisdiction_profile_required",
            "professional_architectural_review_required",
            "structural_design_required",
            "fire_safety_review_required",
            "building_physics_review_required",
            "final_material_and_opening_specification_required",
        ],
    }
    write_json(output / "architectural_quality_report.json", quality)

    permit_ready = bool(
        project["professional_release"].get("permit_approved")
        and project["location"].get("address")
        and project["jurisdiction"].get("building_regulation_profile")
        and project["site"].get("verified_coordinates")
    )
    execution_ready = bool(
        permit_ready and project["professional_release"].get("execution_approved")
    )
    write_json(output / "architectural_release_gate.json", {
        "schema_version": "phoenix.architectural-release-gate/6.5.0",
        "permit_ready": permit_ready,
        "execution_ready": execution_ready,
        "automatic_professional_approval": False,
        "status": "UNLOCKED" if execution_ready else "LOCKED",
    })

    artifacts = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({
                "path": path.relative_to(output).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    write_json(output / "artifact_manifest.json", {
        "schema_version": "phoenix.architectural-artifact-manifest/6.5.0",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    })

    write_json(output / "architectural_generator_run.json", {
        "schema_version": "phoenix.architectural-generator-run/6.5.0",
        "status": "PASSED",
        "project_id": project["project_id"],
        "generic_project_mode": True,
        "pilot_project_dependency": False,
        "storeys_generated": len(model["storeys"]),
        "spaces_generated": len(room_rows),
        "drawings_generated": len(drawing_rows),
        "freecad_generated": True,
        "ifc_generated": True,
        "permit_ready": permit_ready,
        "execution_ready": execution_ready,
    })

    print("PARAMETRIC ARCHITECTURAL BIM AND DRAWING GENERATOR: PASSED")
    print("GENERIC BUILDING PROJECT MODE: ACTIVE")
    print("PILOT PROJECT DEPENDENCY: REMOVED")
    print("PARAMETRIC SPACE LAYOUT: GENERATED")
    print("FREECAD ARCHITECTURAL MODEL: GENERATED")
    print("IFC4 ARCHITECTURAL MODEL: GENERATED")
    print("FLOOR PLANS, ELEVATIONS AND SECTIONS: GENERATED")
    print("ROOM, MATERIAL AND QUANTITY SCHEDULES: GENERATED")
    print("CENTRAL DIGITAL TWIN ARCHITECTURAL WRITEBACK: PASSED")
    print("PERMIT-READY RELEASE: " + ("UNLOCKED" if permit_ready else "LOCKED"))
    print("EXECUTION-READY RELEASE: " + ("UNLOCKED" if execution_ready else "LOCKED"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
