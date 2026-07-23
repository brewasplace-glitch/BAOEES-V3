"""Worker executed inside Blender's Python runtime."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _clean_scene(bpy) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _import_scene(bpy, source: Path) -> None:
    suffix = source.suffix.lower()
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source))
    elif suffix == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(source))
        else:
            bpy.ops.import_scene.obj(filepath=str(source))
    elif suffix in {".gltf", ".glb"}:
        bpy.ops.import_scene.gltf(filepath=str(source))
    elif suffix == ".stl":
        if hasattr(bpy.ops.wm, "stl_import"):
            bpy.ops.wm.stl_import(filepath=str(source))
        else:
            bpy.ops.import_mesh.stl(filepath=str(source))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source))
    else:
        raise ValueError(f"Unsupported Blender source format: {suffix}")


def _apply_materials(bpy, materials: list[dict]) -> None:
    for item in materials:
        object_name = str(item.get("object_name", ""))
        target = bpy.data.objects.get(object_name)
        if target is None:
            continue
        material = bpy.data.materials.new(
            name=str(item.get("name") or f"PhoenixMaterial_{object_name}")
        )
        material.use_nodes = True
        color = item.get("base_color", [0.8, 0.8, 0.8, 1.0])
        material.diffuse_color = tuple(float(value) for value in color)
        if target.data and hasattr(target.data, "materials"):
            target.data.materials.clear()
            target.data.materials.append(material)


def _configure_camera(bpy, config: dict) -> None:
    camera_data = bpy.data.cameras.new("PhoenixCamera")
    camera = bpy.data.objects.new("PhoenixCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = tuple(config.get("location", [10.0, -10.0, 8.0]))
    camera.rotation_euler = tuple(config.get("rotation_euler", [1.1, 0.0, 0.8]))
    camera_data.lens = float(config.get("lens_mm", 50.0))
    bpy.context.scene.camera = camera


def _configure_lights(bpy, lights: list[dict]) -> None:
    for index, item in enumerate(lights, start=1):
        light_data = bpy.data.lights.new(
            name=str(item.get("name") or f"PhoenixLight{index}"),
            type=str(item.get("type", "AREA")).upper(),
        )
        light_data.energy = float(item.get("energy", 1000.0))
        light = bpy.data.objects.new(light_data.name, light_data)
        light.location = tuple(item.get("location", [4.0, -4.0, 8.0]))
        light.rotation_euler = tuple(item.get("rotation_euler", [0.0, 0.0, 0.0]))
        bpy.context.scene.collection.objects.link(light)


def _scene_summary(bpy) -> dict:
    return {
        "object_count": len(bpy.data.objects),
        "mesh_count": len(bpy.data.meshes),
        "material_count": len(bpy.data.materials),
        "camera_count": len(bpy.data.cameras),
        "light_count": len(bpy.data.lights),
        "objects": [
            {
                "name": item.name,
                "type": item.type,
                "location": list(item.location),
            }
            for item in bpy.data.objects
        ],
    }


def _render_still(bpy, destination: Path, settings: dict) -> None:
    scene = bpy.context.scene
    scene.render.filepath = str(destination)
    scene.render.resolution_x = int(settings.get("width", 1920))
    scene.render.resolution_y = int(settings.get("height", 1080))
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = str(
        settings.get("format", "PNG")
    ).upper()
    scene.render.engine = str(settings.get("engine", "BLENDER_EEVEE_NEXT"))
    bpy.ops.render.render(write_still=True)


def _render_animation(bpy, destination: Path, settings: dict) -> None:
    scene = bpy.context.scene
    scene.render.filepath = str(destination)
    scene.render.resolution_x = int(settings.get("width", 1920))
    scene.render.resolution_y = int(settings.get("height", 1080))
    scene.frame_start = int(settings.get("frame_start", 1))
    scene.frame_end = int(settings.get("frame_end", 120))
    scene.render.fps = int(settings.get("fps", 30))
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = str(settings.get("container", "MPEG4"))
    scene.render.engine = str(settings.get("engine", "BLENDER_EEVEE_NEXT"))
    bpy.ops.render.render(animation=True)


def execute_job(job: dict) -> dict:
    import bpy

    operation = str(job["operation"])
    source = Path(str(job.get("source_file", ""))).resolve()
    destination = Path(str(job.get("destination_file", ""))).resolve()
    output_files = []

    _clean_scene(bpy)
    if source:
        _import_scene(bpy, source)

    _apply_materials(bpy, list(job.get("materials", [])))
    _configure_camera(bpy, dict(job.get("camera", {})))
    _configure_lights(
        bpy,
        list(
            job.get(
                "lights",
                [
                    {
                        "type": "AREA",
                        "energy": 1200,
                        "location": [4, -4, 8],
                    }
                ],
            )
        ),
    )

    if operation == "scene.inspect":
        pass
    elif operation == "scene.save":
        destination.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(destination))
        output_files.append(str(destination))
    elif operation == "render.still":
        destination.parent.mkdir(parents=True, exist_ok=True)
        _render_still(bpy, destination, dict(job.get("render", {})))
        output_files.append(str(destination))
    elif operation == "render.animation":
        destination.parent.mkdir(parents=True, exist_ok=True)
        _render_animation(bpy, destination, dict(job.get("render", {})))
        output_files.append(str(destination))
    elif operation == "scene.export":
        destination.parent.mkdir(parents=True, exist_ok=True)
        suffix = destination.suffix.lower()
        if suffix in {".gltf", ".glb"}:
            bpy.ops.export_scene.gltf(filepath=str(destination))
        elif suffix == ".obj":
            if hasattr(bpy.ops.wm, "obj_export"):
                bpy.ops.wm.obj_export(filepath=str(destination))
            else:
                bpy.ops.export_scene.obj(filepath=str(destination))
        elif suffix == ".stl":
            if hasattr(bpy.ops.wm, "stl_export"):
                bpy.ops.wm.stl_export(filepath=str(destination))
            else:
                bpy.ops.export_mesh.stl(filepath=str(destination))
        else:
            raise ValueError(f"Unsupported export format: {suffix}")
        output_files.append(str(destination))
    else:
        raise ValueError(f"Unsupported Blender operation: {operation}")

    return {
        "status": "completed",
        "output_files": output_files,
        "metadata": {"scene": _scene_summary(bpy)},
        "warnings": [],
        "errors": [],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--" in arguments:
        arguments = arguments[arguments.index("--") + 1:]
    if len(arguments) != 2:
        print("Usage: blender_worker.py JOB_JSON RESULT_JSON", file=sys.stderr)
        return 2

    job_path = Path(arguments[0]).resolve()
    result_path = Path(arguments[1]).resolve()
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        _write_json(result_path, execute_job(job))
        return 0
    except Exception as exc:
        _write_json(
            result_path,
            {
                "status": "failed",
                "output_files": [],
                "metadata": {},
                "warnings": [],
                "errors": [f"{type(exc).__name__}: {exc}"],
                "traceback": traceback.format_exc(),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
