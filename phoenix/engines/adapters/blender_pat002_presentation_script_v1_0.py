import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
obj_path = Path(args[0]).resolve()
out_dir = Path(args[1]).resolve()
project_id = args[2]
variant_id = args[3]
variant_name = args[4]

# The Blender process is already started with --factory-startup and -E CYCLES.
# Do NOT reset factory settings here: that would erase the CLI-selected CYCLES engine.
if bpy.context.scene.render.engine != "CYCLES":
    raise RuntimeError(
        "PHOENIX_CYCLES_LOST_BEFORE_OBJ_IMPORT: "
        + str(bpy.context.scene.render.engine)
    )

bpy.ops.wm.obj_import(filepath=str(obj_path))

mesh_objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("NO_MESH_OBJECTS_IMPORTED")

# Materials.
def material(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name=name)
    m.diffuse_color = rgba
    return m

mat_wall = material("Phoenix Wall", (0.78, 0.82, 0.84, 1.0))
mat_glass = material("Phoenix Glass", (0.22, 0.55, 0.76, 0.35))
mat_door = material("Phoenix Door", (0.40, 0.22, 0.10, 1.0))
mat_roof = material("Phoenix Roof", (0.23, 0.28, 0.31, 1.0))
mat_slab = material("Phoenix Slab", (0.60, 0.62, 0.63, 1.0))
for obj in mesh_objects:
    n = obj.name.lower()
    if "window" in n:
        mat = mat_glass
    elif "door" in n:
        mat = mat_door
    elif "roof" in n:
        mat = mat_roof
    elif "slab" in n:
        mat = mat_slab
    else:
        mat = mat_wall
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

# Bounds.
def world_bounds(objects):
    pts = []
    for obj in objects:
        for corner in obj.bound_box:
            pts.append(obj.matrix_world @ Vector(corner))
    if not pts:
        return Vector((-5,-5,0)), Vector((5,5,6))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

lo, hi = world_bounds(mesh_objects)
center = (lo + hi) * 0.5
size = hi - lo
span = max(size.x, size.y, 8.0)

# Ground plane.
bpy.ops.mesh.primitive_plane_add(size=max(40.0, span * 4.0), location=(center.x, center.y, lo.z - 0.03))
ground = bpy.context.object
ground.name = "Phoenix Ground"
ground.data.materials.append(material("Phoenix Ground Mat", (0.12, 0.24, 0.14, 1.0)))

# Lighting.
bpy.ops.object.light_add(type="SUN", location=(center.x + span, center.y - span, hi.z + span))
sun = bpy.context.object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(28), math.radians(-12), math.radians(32))

bpy.ops.object.light_add(type="AREA", location=(center.x - span*.3, center.y - span*.8, hi.z + span*.5))
area = bpy.context.object
area.data.energy = 1800
area.data.shape = "DISK"
area.data.size = max(5.0, span * .7)

# World/render.
scene = bpy.context.scene

# Phoenix autonomous/headless renderer:
# CYCLES was selected by the command line and verified before OBJ import.
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8
scene.cycles.use_denoising = False
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.2

scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
if scene.world is None:
    scene.world = bpy.data.worlds.new("Phoenix World")
scene.world.color = (0.035, 0.055, 0.085)

# Camera helpers.
def look_at(obj, point):
    direction = Vector(point) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def create_camera(name, location, target):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.name = name
    cam.data.lens = 48
    look_at(cam, target)
    return cam

front = create_camera(
    "Phoenix Exterior Front",
    (center.x, lo.y - span*1.55, center.z + span*.35),
    (center.x, center.y, center.z)
)
rear = create_camera(
    "Phoenix Exterior Rear",
    (center.x, hi.y + span*1.55, center.z + span*.28),
    (center.x, center.y, center.z)
)
bird = create_camera(
    "Phoenix Bird View",
    (hi.x + span*.85, lo.y - span*.85, hi.z + span*1.45),
    (center.x, center.y, center.z*.75)
)
interior = create_camera(
    "Phoenix Interior Cutaway",
    (center.x, lo.y - span*.72, max(lo.z + 2.1, center.z*.55)),
    (center.x, center.y + size.y*.08, max(lo.z + 1.6, center.z*.45))
)

def render(cam, filename):
    scene.camera = cam
    scene.render.filepath = str(out_dir / filename)
    bpy.ops.render.render(write_still=True)

# Normal exterior views.
render(front, "phoenix_exterior_front.png")
render(rear, "phoenix_exterior_rear.png")
render(bird, "phoenix_bird_view.png")

# Interior cutaway: hide roof and the front-most wall(s).
roof_objects = [o for o in mesh_objects if "roof" in o.name.lower()]
wall_objects = [o for o in mesh_objects if "wall" in o.name.lower()]
for o in roof_objects:
    o.hide_render = True

if wall_objects:
    wall_centers = []
    for o in wall_objects:
        c = o.matrix_world.translation
        wall_centers.append((c.y, o))
    min_y = min(y for y, _ in wall_centers)
    threshold = max(0.25, size.y * 0.03)
    for y, o in wall_centers:
        if abs(y - min_y) <= threshold:
            o.hide_render = True

render(interior, "phoenix_interior_cutaway.png")

# Marker proving this is a real Blender scene generated from IFC-derived geometry.
(out_dir / "phoenix_blender_scene_evidence.txt").write_text(
    f"{project_id}|variant={variant_id}|name={variant_name}|meshes={len(mesh_objects)}",
    encoding="utf-8"
)
