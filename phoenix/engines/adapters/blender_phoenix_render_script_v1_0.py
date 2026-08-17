import bpy,sys,math
from pathlib import Path
args=sys.argv[sys.argv.index("--")+1:]
obj=Path(args[0]);out=Path(args[1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=str(obj))
for o in bpy.context.scene.objects:
    if getattr(o,"type",None)=="MESH":
        mat=bpy.data.materials.new(name="PhoenixMaterial");mat.diffuse_color=(0.72,0.78,0.82,1.0);o.data.materials.append(mat)
bpy.ops.mesh.primitive_plane_add(size=50,location=(0,0,-0.05))
plane=bpy.context.object
mat=bpy.data.materials.new(name="Ground");mat.diffuse_color=(0.15,0.26,0.16,1.0);plane.data.materials.append(mat)
bpy.ops.object.light_add(type='SUN',location=(5,-5,12));bpy.context.object.rotation_euler=(math.radians(30),0,math.radians(25))
bpy.ops.object.light_add(type='AREA',location=(4,-6,8));bpy.context.object.data.energy=1200;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=6
bpy.ops.object.camera_add(location=(14,-16,10));cam=bpy.context.object;bpy.context.scene.camera=cam
def look_at(obj,pt=(0,0,3)):
    import mathutils
    direction=mathutils.Vector(pt)-obj.location
    obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
look_at(cam)
scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.filepath=str(out)
scene.render.image_settings.file_format='PNG'
scene.world.color=(0.06,0.09,0.13)
bpy.ops.render.render(write_still=True)
