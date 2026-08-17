"""PROJECT PHOENIX IFC Authoritative Model Adapter v1.0."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np

VERSION="1.0.0"
SCHEMA="phoenix.ifc-authoritative-model/1.0"

def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def _write(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _matrix(x=0.0,y=0.0,z=0.0,angle=0.0):
    c,s=math.cos(angle),math.sin(angle)
    return np.array([[c,-s,0,x],[s,c,0,y],[0,0,1,z],[0,0,0,1]],dtype=float)

def _box_rep(model,body,w,d,h):
    import ifcopenshell.api.geometry
    vertices=[(0,0,0),(w,0,0),(w,d,0),(0,d,0),(0,0,h),(w,0,h),(w,d,h),(0,d,h)]
    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return ifcopenshell.api.geometry.add_mesh_representation(model,context=body,vertices=[vertices],faces=[faces])

def _assign_rep(model,product,rep,matrix,container=None):
    import ifcopenshell.api.geometry, ifcopenshell.api.spatial
    ifcopenshell.api.geometry.assign_representation(model,product=product,representation=rep)
    ifcopenshell.api.geometry.edit_object_placement(model,product=product,matrix=matrix,is_si=True)
    if container is not None:
        ifcopenshell.api.spatial.assign_container(model,relating_structure=container,products=[product])

def generate_authoritative_ifc(workspace:Path,arch:Path,selected:dict,variants:list):
    import ifcopenshell
    import ifcopenshell.api.project, ifcopenshell.api.root, ifcopenshell.api.unit
    import ifcopenshell.api.context, ifcopenshell.api.aggregate, ifcopenshell.api.geometry
    import ifcopenshell.api.spatial

    workspace=Path(workspace);arch=Path(arch)
    pid=selected["project_id"]; env=selected["building_envelope_m"]
    w=float(env["width"]);d=float(env["depth"]);levels=int(selected.get("levels",2));fh=3.2;wall_t=.20

    model=ifcopenshell.api.project.create_file(version="IFC4")
    project=ifcopenshell.api.root.create_entity(model,ifc_class="IfcProject",name=pid)
    ifcopenshell.api.unit.assign_unit(model)
    context=ifcopenshell.api.context.add_context(model,context_type="Model")
    body=ifcopenshell.api.context.add_context(model,context_type="Model",context_identifier="Body",target_view="MODEL_VIEW",parent=context)

    site=ifcopenshell.api.root.create_entity(model,ifc_class="IfcSite",name=f"{pid} Site")
    building=ifcopenshell.api.root.create_entity(model,ifc_class="IfcBuilding",name=f"{pid} Building")
    ifcopenshell.api.aggregate.assign_object(model,relating_object=project,products=[site])
    ifcopenshell.api.aggregate.assign_object(model,relating_object=site,products=[building])

    storeys=[]
    for level in range(levels):
        storey=ifcopenshell.api.root.create_entity(model,ifc_class="IfcBuildingStorey",name="Ground Floor" if level==0 else f"Level {level:02d}")
        ifcopenshell.api.aggregate.assign_object(model,relating_object=building,products=[storey])
        ifcopenshell.api.geometry.edit_object_placement(model,product=storey,matrix=_matrix(z=level*fh),is_si=True)
        storeys.append(storey)

    wall_count=0;slab_count=0;space_count=0;door_count=0;window_count=0
    for level,storey in enumerate(storeys):
        z=level*fh
        wall_specs=[
          ("North",w,0,0,0),
          ("South",w,0,d-wall_t,0),
          ("West",d,wall_t,0,math.pi/2),
          ("East",d,w,0,math.pi/2),
          ("Internal-X",d,wall_t,w*.48,math.pi/2),
          ("Internal-Y",w,0,d*.48,0),
        ]
        for name,length,x,y,ang in wall_specs:
            wall=ifcopenshell.api.root.create_entity(model,ifc_class="IfcWall",name=f"L{level} {name} Wall")
            rep=ifcopenshell.api.geometry.add_wall_representation(model,context=body,length=length,height=fh,thickness=wall_t)
            _assign_rep(model,wall,rep,_matrix(x,y,z,ang),storey);wall_count+=1

        slab=ifcopenshell.api.root.create_entity(model,ifc_class="IfcSlab",name=f"L{level} Floor Slab")
        rep=_box_rep(model,body,w,d,.20);_assign_rep(model,slab,rep,_matrix(0,0,z),storey);slab_count+=1

        rooms=selected.get("rooms",{}).get("ground" if level==0 else "upper",[])
        for room in rooms:
            space=ifcopenshell.api.root.create_entity(model,ifc_class="IfcSpace",name=str(room.get("name","Space")))
            ifcopenshell.api.aggregate.assign_object(model,relating_object=storey,products=[space])
            ifcopenshell.api.geometry.edit_object_placement(model,product=space,matrix=_matrix(float(room.get("x",0)),float(room.get("y",0)),z),is_si=True)
            space_count+=1

        # Semantic windows, represented as thin glazing boxes. Openings are deferred to detailed IFC phase.
        for frac in (.2,.5,.8):
            win=ifcopenshell.api.root.create_entity(model,ifc_class="IfcWindow",name=f"L{level} North Window {frac}")
            rep=_box_rep(model,body,1.25,.06,1.25)
            _assign_rep(model,win,rep,_matrix(w*frac-.625,-.03,z+1.0),storey);window_count+=1

    door=ifcopenshell.api.root.create_entity(model,ifc_class="IfcDoor",name="Main Entrance Door")
    rep=_box_rep(model,body,1.05,.06,2.20)
    _assign_rep(model,door,rep,_matrix(w*.5-.525,-.03,0),storeys[0]);door_count+=1

    roof=ifcopenshell.api.root.create_entity(model,ifc_class="IfcRoof",name="Main Roof")
    # Foundation phase: authoritative semantic roof with simple envelope representation.
    rep=_box_rep(model,body,w,d,.25)
    _assign_rep(model,roof,rep,_matrix(0,0,levels*fh),storeys[-1])

    out=arch/"ifc";out.mkdir(parents=True,exist_ok=True)
    ifc_path=out/f"{pid}_architectural_authoritative.ifc"
    model.write(str(ifc_path))

    # Reopen immediately to prove the artifact is parseable and semantically populated.
    check=ifcopenshell.open(str(ifc_path))
    counts={k:len(check.by_type(k)) for k in ("IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey","IfcWall","IfcSlab","IfcSpace","IfcDoor","IfcWindow","IfcRoof")}
    if counts["IfcProject"]!=1 or counts["IfcBuilding"]!=1 or counts["IfcWall"]<levels*6:
        raise RuntimeError(f"IFC semantic validation failed: {counts}")

    evidence={
      "schema_version":SCHEMA,"adapter_version":VERSION,"project_id":pid,
      "authoritative_geometry_format":"IFC","ifc_schema":check.schema,
      "ifc_file":str(ifc_path),"selected_variant":selected["variant"]["id"],
      "selected_variant_name":selected["variant"]["name"],"entity_counts":counts,
      "ifcopenshell_version":str(getattr(ifcopenshell,"version",getattr(ifcopenshell,"__version__","unknown"))),
      "bim_lite_role":"PRESENTATION_FALLBACK_ONLY",
      "professional_review_required":True,"production_release":"LOCKED"
    }
    _write(out/"ifc_authoritative_model_evidence.json",evidence)

    model_path=arch/"architectural_model.json"
    if model_path.exists():
        data=_read(model_path)
        # Preserve the design generator provenance for backward compatibility.
        # IFC is expressed separately as the authoritative geometry source.
        data["architectural_model_source"]="REAL_MULTI_VARIANT_PARAMETRIC_DESIGN"
        data["authoritative_geometry_source"]="IFC_AUTHORITATIVE"
        data["authoritative_geometry_format"]="IFC"
        data["authoritative_ifc"]=str(ifc_path)
        data["ifc_adapter_version"]=VERSION
        data["bim_lite_role"]="PRESENTATION_FALLBACK_ONLY"
        _write(model_path,data)

    for twin_path in (workspace/"results/session_adapters/digital_twin/central_project_digital_twin.json",workspace/"digital_twin/central_project_digital_twin.json"):
        if twin_path.exists():
            data=_read(twin_path)
            data["authoritative_architectural_geometry"]={
              "format":"IFC","source":"IFC_AUTHORITATIVE","ifc_file":str(ifc_path),
              "selected_variant":selected["variant"]["id"],"entity_counts":counts,
              "adapter_version":VERSION,"bim_lite_role":"PRESENTATION_FALLBACK_ONLY",
              "professional_review_required":True,"production_release":"LOCKED"}
            _write(twin_path,data)

    return evidence
