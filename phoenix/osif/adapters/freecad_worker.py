"""Worker script executed inside FreeCADCmd.

This module intentionally imports FreeCAD only inside ``main`` so normal Phoenix
test and discovery environments do not require FreeCAD to be installed.
"""

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


def _document_summary(document) -> dict:
    objects = []
    for item in document.Objects:
        shape = getattr(item, "Shape", None)
        volume = float(shape.Volume) if shape is not None and hasattr(shape, "Volume") else 0.0
        area = float(shape.Area) if shape is not None and hasattr(shape, "Area") else 0.0
        objects.append(
            {
                "name": str(item.Name),
                "label": str(item.Label),
                "type_id": str(item.TypeId),
                "volume": volume,
                "area": area,
            }
        )
    return {
        "document_name": str(document.Name),
        "object_count": len(objects),
        "objects": objects,
    }


def _create_document(App, Part, job: dict):
    name = str(job.get("document_name") or "PhoenixDocument")
    document = App.newDocument(name)
    primitives = job.get("primitives", [])
    for index, primitive in enumerate(primitives, start=1):
        primitive_type = str(primitive.get("type", "")).lower()
        label = str(primitive.get("label") or f"Object{index}")
        if primitive_type == "box":
            shape = Part.makeBox(
                float(primitive["length"]),
                float(primitive["width"]),
                float(primitive["height"]),
            )
        elif primitive_type == "cylinder":
            shape = Part.makeCylinder(
                float(primitive["radius"]),
                float(primitive["height"]),
            )
        elif primitive_type == "sphere":
            shape = Part.makeSphere(float(primitive["radius"]))
        else:
            raise ValueError(f"Unsupported primitive type: {primitive_type}")
        feature = document.addObject("PartDesign::Feature", f"PhoenixObject{index}")
        feature.Label = label
        feature.Shape = shape
    document.recompute()
    return document


def _open_or_import(App, Import, job: dict):
    source = Path(str(job["source_file"])).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source}")
    suffix = source.suffix.lower()
    if suffix in {".fcstd"}:
        return App.openDocument(str(source))
    document = App.newDocument(str(job.get("document_name") or "PhoenixImported"))
    Import.insert(str(source), document.Name)
    document.recompute()
    return document


def _save_document(document, destination: str) -> str:
    path = Path(destination).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(path))
    return str(path)


def _export_document(Import, document, destination: str) -> str:
    path = Path(destination).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    visible = [item for item in document.Objects if hasattr(item, "Shape")]
    if not visible:
        raise ValueError("Document contains no exportable shape objects.")
    Import.export(visible, str(path))
    return str(path)


def _validate_geometry(document) -> dict:
    invalid = []
    checked = 0
    for item in document.Objects:
        shape = getattr(item, "Shape", None)
        if shape is None or shape.isNull():
            continue
        checked += 1
        if not shape.isValid():
            invalid.append(str(item.Name))
    return {
        "checked_shape_count": checked,
        "invalid_shape_names": invalid,
        "is_valid": not invalid,
    }


def execute_job(job: dict) -> dict:
    import FreeCAD as App
    import Part
    import Import

    operation = str(job["operation"])
    output_files = []
    metadata = {}

    if operation == "document.create":
        document = _create_document(App, Part, job)
    elif operation in {"document.inspect", "geometry.validate", "document.export"}:
        document = _open_or_import(App, Import, job)
    elif operation == "document.import":
        document = _open_or_import(App, Import, job)
        destination = str(job["destination_file"])
        output_files.append(_save_document(document, destination))
    elif operation == "macro.execute":
        macro_file = Path(str(job["macro_file"])).resolve()
        if not macro_file.is_file():
            raise FileNotFoundError(f"Macro file does not exist: {macro_file}")
        namespace = {
            "App": App,
            "Part": Part,
            "Import": Import,
            "__file__": str(macro_file),
            "__name__": "__phoenix_freecad_macro__",
        }
        exec(compile(macro_file.read_text(encoding="utf-8"), str(macro_file), "exec"), namespace)
        document = App.ActiveDocument
        if document is None:
            raise ValueError("Custom macro did not leave an active FreeCAD document.")
    else:
        raise ValueError(f"Unsupported FreeCAD operation: {operation}")

    if operation == "document.create":
        destination = str(job["destination_file"])
        output_files.append(_save_document(document, destination))
    elif operation == "document.export":
        destination = str(job["destination_file"])
        output_files.append(_export_document(Import, document, destination))

    if operation == "geometry.validate":
        metadata["geometry_validation"] = _validate_geometry(document)

    metadata["document"] = _document_summary(document)
    return {
        "status": "completed",
        "output_files": output_files,
        "metadata": metadata,
        "warnings": [],
        "errors": [],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print("Usage: freecad_worker.py JOB_JSON RESULT_JSON", file=sys.stderr)
        return 2

    job_path = Path(arguments[0]).resolve()
    result_path = Path(arguments[1]).resolve()
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        result = execute_job(job)
        _write_json(result_path, result)
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
