"""IFC -> OBJ mesh derivation for Phoenix visual stack v1.0."""
from __future__ import annotations
from pathlib import Path
import json

VERSION="1.0.0"

def ifc_to_obj(ifc_path:Path,obj_path:Path)->dict:
    import ifcopenshell
    import ifcopenshell.geom

    ifc_path=Path(ifc_path).resolve();obj_path=Path(obj_path).resolve()
    if not ifc_path.exists():raise FileNotFoundError(ifc_path)
    model=ifcopenshell.open(str(ifc_path))
    settings=ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS,True)

    products=[]
    for cls in ("IfcWall","IfcSlab","IfcRoof","IfcDoor","IfcWindow"):
        products.extend(model.by_type(cls))

    obj_path.parent.mkdir(parents=True,exist_ok=True)
    lines=["# PROJECT PHOENIX IFC-derived OBJ","o PhoenixBuilding"]
    vertex_offset=1;mesh_count=0;triangle_count=0
    for product in products:
        try:
            shape=ifcopenshell.geom.create_shape(settings,product)
            verts=list(shape.geometry.verts)
            faces=list(shape.geometry.faces)
            if not verts or not faces:continue
            lines.append(f"g {product.is_a()}_{product.id()}")
            for i in range(0,len(verts),3):
                lines.append(f"v {verts[i]:.9f} {verts[i+1]:.9f} {verts[i+2]:.9f}")
            for i in range(0,len(faces),3):
                a=faces[i]+vertex_offset;b=faces[i+1]+vertex_offset;c=faces[i+2]+vertex_offset
                lines.append(f"f {a} {b} {c}")
                triangle_count+=1
            vertex_offset += len(verts)//3
            mesh_count+=1
        except Exception:
            continue

    if mesh_count==0 or triangle_count==0:
        raise RuntimeError("IFC_VISUAL_MESH_EMPTY")
    obj_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    evidence={
      "adapter_version":VERSION,"source_ifc":str(ifc_path),"obj":str(obj_path),
      "mesh_objects":mesh_count,"triangles":triangle_count,
      "authoritative_geometry":"IFC","derived_artifact":"OBJ","production_release":"LOCKED"
    }
    obj_path.with_suffix(".evidence.json").write_text(json.dumps(evidence,indent=2)+"\n",encoding="utf-8")
    return evidence
