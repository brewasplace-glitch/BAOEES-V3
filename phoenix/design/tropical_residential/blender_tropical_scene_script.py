# Executed by Blender's bundled Python runtime.
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def cli_args():
    args = sys.argv
    if "--" not in args:
        raise RuntimeError("Phoenix Blender script requires -- separator")
    args = args[args.index("--") + 1:]
    out = {}
    i = 0
    while i < len(args):
        key = args[i]
        if key == "--quick":
            out["quick"] = True
            i += 1
            continue
        if i + 1 >= len(args):
            raise RuntimeError(f"Missing value for {key}")
        out[key.lstrip("-").replace("-", "_")] = args[i + 1]
        i += 2
    return out


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass


def material(name, base, metallic=0.0, rough=0.55, alpha=1.0, emission=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*base, alpha)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*base, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = rough
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if emission is not None:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 2.0
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = (*emission, 1.0)
    if alpha < 1.0:
        try:
            m.surface_render_method = "DITHERED"
        except Exception:
            try:
                m.blend_method = "BLEND"
            except Exception:
                pass
    return m


def assign(obj, mat):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)


def cube(name, center, dims, mat=None, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(location=center, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        assign(obj, mat)
    return obj


def oriented_box(name, x1, y1, angle, along_start, length, thickness, z0, height, mat):
    if length <= 0.02 or height <= 0.02:
        return None
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    cx = x1 + ux * (along_start + length / 2.0)
    cy = y1 + uy * (along_start + length / 2.0)
    return cube(
        name,
        (cx, cy, z0 + height / 2.0),
        (length, thickness, height),
        mat,
        (0.0, 0.0, a),
    )


def local_opening_distance(wall, opening):
    x1, y1 = float(wall["x1"]), float(wall["y1"])
    x2, y2 = float(wall["x2"]), float(wall["y2"])
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return 0.0
    ux, uy = dx / length, dy / length
    return (float(opening["x"]) - x1) * ux + (float(opening["y"]) - y1) * uy


def build_wall_with_openings(wall, openings, z0, storey_h, wall_mat, frame_mat, glass_mat, door_mat):
    x1, y1, x2, y2 = map(float, (wall["x1"], wall["y1"], wall["x2"], wall["y2"]))
    length = math.hypot(x2-x1, y2-y1)
    angle = math.degrees(math.atan2(y2-y1, x2-x1))
    thickness = float(wall["thickness_m"])
    wall_name = wall["wall_key"].replace(":", "_").replace(",", "_")

    spans = []
    for op in openings:
        start = max(0.0, local_opening_distance(wall, op))
        width = min(float(op["width_m"]), max(0.0, length-start))
        if width > 0.25:
            spans.append((start, min(length, start+width), op))
    spans.sort(key=lambda x: x[0])

    cursor = 0.0
    wall_objs = []
    for idx, (start, end, op) in enumerate(spans):
        if start > cursor + 0.02:
            wall_objs.append(oriented_box(
                f"W_{wall_name}_FULL_{idx}", x1, y1, angle, cursor, start-cursor,
                thickness, z0, storey_h, wall_mat
            ))

        sill = float(op["sill_m"])
        oh = min(float(op["height_m"]), storey_h - sill)
        if sill > 0.02:
            wall_objs.append(oriented_box(
                f"W_{wall_name}_LOW_{idx}", x1, y1, angle, start, end-start,
                thickness, z0, sill, wall_mat
            ))
        top = sill + oh
        if storey_h - top > 0.02:
            wall_objs.append(oriented_box(
                f"W_{wall_name}_UP_{idx}", x1, y1, angle, start, end-start,
                thickness, z0+top, storey_h-top, wall_mat
            ))

        # Visible frame and filling.
        frame_t = 0.065
        frame_d = thickness + 0.045
        # vertical frames
        for edge in (start, end-frame_t):
            oriented_box(
                f"FRAME_{op['opening_id']}_{edge:.2f}", x1, y1, angle,
                edge, frame_t, frame_d, z0+sill, oh, frame_mat
            )
        # top frame
        oriented_box(
            f"FRAME_TOP_{op['opening_id']}", x1, y1, angle,
            start, end-start, frame_d, z0+sill+oh-frame_t, frame_t, frame_mat
        )
        if op["kind"] == "window":
            oriented_box(
                f"FRAME_BOTTOM_{op['opening_id']}", x1, y1, angle,
                start, end-start, frame_d, z0+sill, frame_t, frame_mat
            )
            oriented_box(
                f"GLASS_{op['opening_id']}", x1, y1, angle,
                start+frame_t, max(0.15, end-start-2*frame_t), 0.018,
                z0+sill+frame_t, max(0.15, oh-2*frame_t), glass_mat
            )
        else:
            oriented_box(
                f"DOOR_{op['opening_id']}", x1, y1, angle,
                start+frame_t, max(0.15, end-start-2*frame_t), 0.05,
                z0+sill+frame_t, max(0.15, oh-frame_t), door_mat
            )

        cursor = max(cursor, end)

    if cursor < length - 0.02:
        wall_objs.append(oriented_box(
            f"W_{wall_name}_TAIL", x1, y1, angle, cursor, length-cursor,
            thickness, z0, storey_h, wall_mat
        ))

    if not spans:
        wall_objs.append(oriented_box(
            f"W_{wall_name}", x1, y1, angle, 0.0, length,
            thickness, z0, storey_h, wall_mat
        ))

    for obj in wall_objs:
        if obj:
            obj["PHOENIX_WALL_SOURCE"] = wall.get("source", "")
            obj["PHOENIX_EXTERNAL"] = bool(wall.get("external"))
    return [x for x in wall_objs if x]


def mesh_object(name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign(obj, mat)
    return obj


def gable_roof(fw, fd, z, overhang, pitch_deg, mat):
    x0, x1 = -overhang, fw + overhang
    y0, y1 = -overhang, fd + overhang
    half = (y1-y0)/2.0
    rise = math.tan(math.radians(pitch_deg)) * half
    ym = (y0+y1)/2.0
    verts = [(x0,y0,z),(x1,y0,z),(x1,ym,z+rise),(x0,ym,z+rise),
             (x0,y1,z),(x1,y1,z)]
    faces = [(0,1,2,3),(3,2,5,4),(0,3,4),(1,5,2)]
    return mesh_object("Roof_Gable", verts, faces, mat)


def hip_roof(fw, fd, z, overhang, pitch_deg, mat):
    x0, x1 = -overhang, fw + overhang
    y0, y1 = -overhang, fd + overhang
    span = min(x1-x0, y1-y0)
    rise = math.tan(math.radians(pitch_deg)) * span/2.0
    if (x1-x0) >= (y1-y0):
        inset = (y1-y0)/2.0
        r0, r1 = x0+inset, x1-inset
        ym = (y0+y1)/2.0
        verts=[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z),(r0,ym,z+rise),(r1,ym,z+rise)]
        faces=[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4)]
    else:
        inset = (x1-x0)/2.0
        r0, r1 = y0+inset, y1-inset
        xm = (x0+x1)/2.0
        verts=[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z),(xm,r0,z+rise),(xm,r1,z+rise)]
        faces=[(0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5)]
    return mesh_object("Roof_Hip", verts, faces, mat)


def shed_roof(fw, fd, z, overhang, pitch_deg, mat):
    x0, x1 = -overhang, fw + overhang
    y0, y1 = -overhang, fd + overhang
    rise = math.tan(math.radians(pitch_deg)) * (y1-y0)
    verts=[(x0,y0,z),(x1,y0,z),(x1,y1,z+rise),(x0,y1,z+rise)]
    return mesh_object("Roof_Shed", verts, [(0,1,2,3)], mat)


def point_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, lens=45.0):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    cam = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(cam)
    cam.location = location
    point_at(cam, target)
    return cam


def add_camera_label(cam, text, emission_mat):
    bpy.ops.object.text_add()
    label = bpy.context.object
    label.name = "PHOENIX_VARIANT_LABEL"
    label.data.body = text
    label.data.align_x = "CENTER"
    label.data.align_y = "TOP"
    label.data.size = 0.42
    label.data.extrude = 0.002
    assign(label, emission_mat)
    label.parent = cam
    label.location = (0.0, 2.6, -7.5)
    label.rotation_euler = (0.0, 0.0, 0.0)
    return label


def setup_lighting(fw, fd, total_h):
    world = bpy.context.scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.07, 0.12, 0.18, 1.0)
        bg.inputs["Strength"].default_value = 0.35

    sun_data = bpy.data.lights.new("TropicalSun", "SUN")
    sun_data.energy = 3.0
    sun_data.angle = math.radians(4.0)
    sun = bpy.data.objects.new("TropicalSun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(25))

    area_data = bpy.data.lights.new("FillArea", "AREA")
    area_data.energy = 1400
    area_data.shape = "DISK"
    area_data.size = max(fw, fd) * 0.8
    area = bpy.data.objects.new("FillArea", area_data)
    bpy.context.collection.objects.link(area)
    area.location = (fw*0.2, -fd*0.4, total_h*1.3)
    point_at(area, (fw/2, fd/2, total_h/2))


def strategy_palette(strategy):
    return {
        "PASSIVE_COOLING": ((0.82,0.88,0.82),(0.18,0.34,0.24),(0.58,0.28,0.12)),
        "LOW_COST": ((0.86,0.84,0.78),(0.32,0.31,0.28),(0.50,0.22,0.10)),
        "RESILIENCE": ((0.78,0.82,0.86),(0.18,0.22,0.28),(0.35,0.18,0.10)),
        "INDOOR_OUTDOOR": ((0.90,0.84,0.72),(0.24,0.38,0.26),(0.62,0.30,0.12)),
        "BALANCED": ((0.86,0.88,0.84),(0.22,0.30,0.28),(0.52,0.25,0.11)),
    }.get(strategy, ((0.86,0.86,0.84),(0.25,0.25,0.25),(0.55,0.25,0.10)))


def build_scene(layout):
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    wall_color, roof_color, timber_color = strategy_palette(layout["strategy"])
    wall_mat = material("Wall", wall_color, rough=0.72)
    roof_mat = material("Roof", roof_color, metallic=0.08, rough=0.38)
    timber_mat = material("Timber", timber_color, rough=0.62)
    frame_mat = material("Frames", (0.09,0.10,0.10), metallic=0.35, rough=0.30)
    glass_mat = material("Glass", (0.16,0.42,0.55), rough=0.12, alpha=0.32)
    slab_mat = material("Slab", (0.48,0.49,0.47), rough=0.85)
    ground_mat = material("Ground", (0.18,0.30,0.13), rough=0.95)
    label_mat = material("LabelEmission", (1,1,1), rough=0.2, emission=(1.0,0.92,0.58))

    fw = float(layout["footprint"]["width_m"])
    fd = float(layout["footprint"]["depth_m"])
    raised = float(layout["elevation"]["raised_floor_m"])
    storey_h = float(layout["storey_height_m"])
    nstoreys = int(layout["storeys"])
    total_h = raised + nstoreys*storey_h
    ov = float(layout["roof"]["eave_overhang_m"])
    pitch = float(layout["roof"]["pitch_deg"])

    cube("Ground",(fw/2,fd/2,-0.08),(max(fw*2.6,35),max(fd*2.4,35),0.15),ground_mat)

    for s in range(nstoreys):
        cube(
            f"Slab_S{s+1}",
            (fw/2,fd/2,raised+s*storey_h-0.10),
            (fw,fd,0.20),
            slab_mat,
        )

    wall_objects = []
    for wall in layout["walls"]:
        s = int(wall["storey_index"])
        z0 = raised + s*storey_h
        openings = [o for o in layout["openings"] if o["host_wall_key"] == wall["wall_key"]]
        wall_objects.extend(build_wall_with_openings(
            wall, openings, z0, storey_h,
            wall_mat, frame_mat, glass_mat, timber_mat
        ))

    # Covered tropical veranda.
    v = layout["veranda"]
    vx, vy, vw, vd = map(float, (v["x"],v["y"],v["width"],v["depth"]))
    cube("Veranda_Slab",(vx+vw/2,vy+vd/2,raised-0.04),(vw,vd,0.12),slab_mat)
    for x in (vx+0.18, vx+vw-0.18):
        cube(f"Veranda_Column_{x:.2f}",(x,vy+0.25,raised+storey_h/2),(0.16,0.16,storey_h),timber_mat)
    # Lean-to veranda roof, with a small drainage fall.
    veranda_roof = cube(
        "Veranda_Roof",
        (vx+vw/2,vy+vd/2,raised+storey_h+0.05),
        (vw+0.4,vd+0.4,0.12),
        roof_mat,
        (math.radians(-5.0),0.0,0.0),
    )

    if layout["strategy"] == "RESILIENCE":
        roof = hip_roof(fw,fd,total_h,ov,max(22.0,pitch),roof_mat)
    elif layout["strategy"] == "INDOOR_OUTDOOR":
        roof = shed_roof(fw,fd,total_h,ov,max(12.0,min(pitch,24.0)),roof_mat)
    else:
        roof = gable_roof(fw,fd,total_h,ov,pitch,roof_mat)

    # External shading hoods for tropical solar/rain protection.
    if layout["strategy"] in {"PASSIVE_COOLING","INDOOR_OUTDOOR","BALANCED"}:
        for idx, op in enumerate(layout["openings"]):
            if op["kind"] != "window":
                continue
            host = next((w for w in layout["walls"] if w["wall_key"] == op["host_wall_key"]), None)
            if not host or not host.get("external"):
                continue
            x1,y1,x2,y2 = map(float,(host["x1"],host["y1"],host["x2"],host["y2"]))
            length = math.hypot(x2-x1,y2-y1)
            angle = math.degrees(math.atan2(y2-y1,x2-x1))
            along = local_opening_distance(host,op)
            z = raised + int(op["storey_index"])*storey_h + float(op["sill_m"]) + float(op["height_m"]) + 0.15
            hood = oriented_box(
                f"Shade_{idx}",x1,y1,angle,along-0.10,float(op["width_m"])+0.20,
                0.55,z,0.07,roof_mat
            )

    setup_lighting(fw,fd,total_h)

    distance = max(fw,fd)*1.35 + 8.0
    target = (fw/2,fd/2,raised+storey_h*0.85)
    cameras = {
        "exterior_front": camera("Camera_Front",(fw/2,-distance,raised+storey_h*0.9),target,48),
        "exterior_rear": camera("Camera_Rear",(fw/2,fd+distance,raised+storey_h*0.9),target,48),
        "bird_view": camera("Camera_Bird",(fw*1.35,-fd*1.15,total_h+max(fw,fd)*1.25),(fw/2,fd/2,raised+storey_h*0.7),52),
        "interior_cutaway": camera("Camera_InteriorCutaway",(fw*0.95,-distance*0.52,raised+storey_h*1.05),(fw*0.46,fd*0.42,raised+storey_h*0.55),50),
    }

    label_text = f"VARIANT {layout['variant_id']} — {layout['strategy'].replace('_',' ')}"
    labels = {}
    for name, cam in cameras.items():
        labels[name] = add_camera_label(cam,label_text,label_mat)

    return {
        "cameras": cameras,
        "labels": labels,
        "wall_objects": wall_objects,
        "roof": roof,
        "veranda_roof": veranda_roof,
        "fw": fw,
        "fd": fd,
        "raised": raised,
        "storey_h": storey_h,
        "total_h": total_h,
    }


def configure_render(quick):
    scene = bpy.context.scene

    # Phoenix headless rendering deliberately uses Cycles on CPU.
    # This avoids dependence on OpenGL shader extensions required by EEVEE/
    # Workbench on some Windows GPU/driver combinations. Blender 5.2 supports
    # CPU as an official Cycles render device.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8 if quick else 48
    scene.cycles.use_denoising = False if quick else True

    try:
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.20 if quick else 0.05
    except Exception:
        pass

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100

    if quick:
        scene.render.resolution_x = 400
        scene.render.resolution_y = 267
    else:
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720

    try:
        scene.render.image_settings.color_depth = "8"
        scene.render.image_settings.compression = 20
    except Exception:
        pass

    # Evidence written into the .blend scene for runtime audit.
    scene["PHOENIX_RENDER_ENGINE"] = "CYCLES"
    scene["PHOENIX_RENDER_DEVICE"] = "CPU"
    scene["PHOENIX_RENDER_SAMPLES"] = int(scene.cycles.samples)


def render_view(scene_info, view, out_path):
    scene = bpy.context.scene
    cam = scene_info["cameras"][view]
    scene.camera = cam

    hidden = []
    if view == "interior_cutaway":
        # Cut away two exterior walls and the main roof, exposing real rooms/openings.
        for obj in scene_info["wall_objects"]:
            src = str(obj.get("PHOENIX_WALL_SOURCE",""))
            if src in {"envelope_south","envelope_east"}:
                hidden.append((obj,obj.hide_render))
                obj.hide_render = True
        roof = scene_info["roof"]
        hidden.append((roof,roof.hide_render))
        roof.hide_render = True

    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)

    for obj, old in hidden:
        obj.hide_render = old


def main():
    args = cli_args()
    layout_path = Path(args["layout"])
    output_dir = Path(args["output_dir"])
    quick = bool(args.get("quick"))
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True,exist_ok=True)

    configure_render(quick)
    print("PHOENIX_BLENDER_RENDER_ENGINE", bpy.context.scene.render.engine)
    print("PHOENIX_BLENDER_RENDER_DEVICE", bpy.context.scene.cycles.device)
    print("PHOENIX_BLENDER_RENDER_SAMPLES", bpy.context.scene.cycles.samples)
    info = build_scene(layout)

    files = {}
    for view in ("exterior_front","exterior_rear","bird_view","interior_cutaway"):
        p = output_dir / f"{view}.png"
        render_view(info,view,p)
        if not p.is_file() or p.stat().st_size < 1000:
            raise RuntimeError(f"Blender did not create a valid render: {p}")
        files[view] = str(p)

    blend_path = output_dir / f"variant_{layout['variant_id']}.blend"
    bpy.context.scene["PHOENIX_PROJECT_ID"] = layout["project_id"]
    bpy.context.scene["PHOENIX_VARIANT_ID"] = layout["variant_id"]
    bpy.context.scene["PHOENIX_STRATEGY"] = layout["strategy"]
    bpy.context.scene["PHOENIX_RELEASE_STATUS"] = "CONCEPT_ONLY_NOT_FOR_CONSTRUCTION"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    if not blend_path.is_file() or blend_path.stat().st_size < 1000:
        raise RuntimeError("Blend save failed")

    print("PHOENIX_TROPICAL_3D_RENDER_OK")
    print(json.dumps({
        "variant_id": layout["variant_id"],
        "strategy": layout["strategy"],
        "blend": str(blend_path),
        "renders": files,
        "quick": quick,
    }))


main()
