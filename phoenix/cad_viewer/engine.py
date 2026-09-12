#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

ENGINE_VERSION = "1.0.0"
SUPPORTED = {".dxf", ".dwg"}


def load_runtime_config(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for key in ("librecad_exe", "libredwg_dwg2dxf_exe"):
        if key not in data or not data[key]:
            raise RuntimeError(f"runtime config missing {key}")
    return data


def inspect_dxf(path: Path) -> Dict[str, Any]:
    import ezdxf

    read_mode = "STRICT"
    recovery_errors = []
    try:
        doc = ezdxf.readfile(path)
    except Exception as strict_exc:
        try:
            from ezdxf import recover
            doc, auditor = recover.readfile(path)
            read_mode = "RECOVER"
            recovery_errors = [str(x) for x in getattr(auditor, "errors", [])[:50]]
        except Exception as recover_exc:
            raise RuntimeError(
                "DXF_PARSE_FAILED_STRICT_AND_RECOVER: "
                f"strict={strict_exc}; recover={recover_exc}"
            ) from recover_exc

    msp = doc.modelspace()

    counts = collections.Counter()
    text_samples = []
    for entity in msp:
        et = entity.dxftype()
        counts[et] += 1
        if et in ("TEXT", "MTEXT") and len(text_samples) < 50:
            try:
                value = entity.dxf.text if et == "TEXT" else entity.text
                if value:
                    text_samples.append(str(value))
            except Exception:
                pass

    layers = []
    for layer in doc.layers:
        try:
            layers.append({
                "name": layer.dxf.name,
                "color": int(layer.dxf.color),
                "linetype": str(layer.dxf.linetype),
            })
        except Exception:
            layers.append({"name": str(layer.dxf.name)})

    result = {
        "format": "DXF",
        "path": str(path),
        "dxfversion": str(doc.dxfversion),
        "read_mode": read_mode,
        "recovery_errors": recovery_errors,
        "modelspace_entity_count": sum(counts.values()),
        "entity_counts": dict(sorted(counts.items())),
        "layer_count": len(layers),
        "layers": layers,
        "text_samples": text_samples,
    }
    return result


def convert_dwg_to_dxf(dwg: Path, dwg2dxf_exe: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    cmd = [
        str(dwg2dxf_exe),
        "-y",
        "-o",
        str(output),
        str(dwg),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "LibreDWG dwg2dxf failed: "
            + (proc.stderr or proc.stdout or f"exit {proc.returncode}")
        )
    if not output.exists() or output.stat().st_size <= 0:
        raise RuntimeError("LibreDWG reported success but DXF output is missing")
    return output


def inspect_file(path: Path, runtime: Dict[str, Any], workdir: Path) -> Dict[str, Any]:
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise RuntimeError(f"unsupported CAD format: {ext}")

    if ext == ".dxf":
        result = inspect_dxf(path)
        result["source_format"] = "DXF"
        result["conversion"] = "NOT_REQUIRED"
        return result

    converted = workdir / f"{path.stem}_libredwg.dxf"
    convert_dwg_to_dxf(
        path,
        Path(runtime["libredwg_dwg2dxf_exe"]),
        converted,
    )
    try:
        result = inspect_dxf(converted)
        result["machine_inspection_status"] = "PASS"
    except Exception as exc:
        # LibreDWG 0.14 can emit DXF with duplicate/invalid handles for some DWG
        # files. Interactive LibreCAD viewing remains available independently.
        result = {
            "format": "DWG",
            "source_format": "DWG",
            "source_path": str(path),
            "converted_dxf": str(converted),
            "conversion": "LibreDWG_0.14_DWG_TO_DXF",
            "conversion_status": "PASS",
            "machine_inspection_status": "DEGRADED_LIBREDWG_DXF_PARSE",
            "machine_inspection_error": str(exc),
            "interactive_viewer": "LibreCAD",
            "interactive_viewer_status": "AVAILABLE",
        }
        return result

    result["source_format"] = "DWG"
    result["conversion"] = "LibreDWG_0.14_DWG_TO_DXF"
    result["conversion_status"] = "PASS"
    result["source_path"] = str(path)
    result["converted_dxf"] = str(converted)
    result["interactive_viewer"] = "LibreCAD"
    result["interactive_viewer_status"] = "AVAILABLE"
    return result


def open_file(path: Path, runtime: Dict[str, Any]) -> None:
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise RuntimeError(f"unsupported CAD format: {ext}")

    viewer = Path(runtime["librecad_exe"])
    if not viewer.exists():
        raise RuntimeError(f"LibreCAD executable not found: {viewer}")

    # LibreCAD can read DXF and DWG directly. Phoenix keeps LibreDWG as
    # an independent machine-readable DWG fallback/conversion backend.
    subprocess.Popen([str(viewer), str(path)], close_fds=True)


def make_test_dxf(path: Path) -> None:
    import ezdxf

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    doc.layers.add("PHOENIX_TEST")
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "PHOENIX_TEST"})
    msp.add_line((1000, 0), (1000, 500), dxfattribs={"layer": "PHOENIX_TEST"})
    msp.add_text("PHOENIX CAD VIEWER TEST", dxfattribs={"height": 50, "layer": "PHOENIX_TEST"})
    doc.saveas(path)


def verify_runtime(runtime: Dict[str, Any]) -> Dict[str, Any]:
    viewer = Path(runtime["librecad_exe"])
    converter = Path(runtime["libredwg_dwg2dxf_exe"])
    if not viewer.exists():
        raise RuntimeError(f"LibreCAD missing: {viewer}")
    if not converter.exists():
        raise RuntimeError(f"LibreDWG dwg2dxf missing: {converter}")

    proc = subprocess.run([str(converter), "--version"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("LibreDWG --version failed")

    return {
        "librecad_exe": str(viewer),
        "libredwg_dwg2dxf_exe": str(converter),
        "libredwg_version_output": (proc.stdout or proc.stderr).strip(),
        "status": "PASS",
    }


def self_test() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.dxf"
        make_test_dxf(p)
        result = inspect_dxf(p)
        assert result["format"] == "DXF"
        assert result["modelspace_entity_count"] == 3
        assert "PHOENIX_TEST" in [x["name"] for x in result["layers"]]
        assert "LINE" in result["entity_counts"]
        print("PHOENIX_4_41_CAD_VIEWER_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-config", type=Path)
    ap.add_argument("--inspect", type=Path)
    ap.add_argument("--open", dest="open_file_path", type=Path)
    ap.add_argument("--convert-dwg", type=Path)
    ap.add_argument("--output-dxf", type=Path)
    ap.add_argument("--output-json", type=Path)
    ap.add_argument("--make-test-dxf", type=Path)
    ap.add_argument("--verify-runtime", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    if args.make_test_dxf:
        make_test_dxf(args.make_test_dxf)
        print(f"TEST_DXF={args.make_test_dxf}")
        print("TEST_DXF_CREATE=PASS")
        return 0

    if not args.runtime_config:
        ap.error("--runtime-config required")
    runtime = load_runtime_config(args.runtime_config)

    if args.verify_runtime:
        result = verify_runtime(runtime)
        print(json.dumps(result, indent=2))
        print("CAD_VIEWER_RUNTIME_VERIFY=PASS")
        return 0

    if args.open_file_path:
        p = args.open_file_path.resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        open_file(p, runtime)
        print(f"CAD_OPEN_LAUNCHED={p}")
        print("CAD_OPEN=PASS")
        return 0

    if args.convert_dwg:
        p = args.convert_dwg.resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        if p.suffix.lower() != ".dwg":
            raise RuntimeError("--convert-dwg requires a .dwg file")
        out = args.output_dxf or p.with_suffix(".phoenix.dxf")
        convert_dwg_to_dxf(p, Path(runtime["libredwg_dwg2dxf_exe"]), out)
        print(f"DWG_SOURCE={p}")
        print(f"DXF_OUTPUT={out}")
        print("DWG_TO_DXF=PASS")
        return 0

    if args.inspect:
        p = args.inspect.resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        with tempfile.TemporaryDirectory(prefix="phoenix_cad_inspect_") as td:
            result = inspect_file(p, runtime, Path(td))
            payload = json.dumps(result, indent=2, ensure_ascii=False)
            if args.output_json:
                args.output_json.parent.mkdir(parents=True, exist_ok=True)
                args.output_json.write_text(payload, encoding="utf-8")
            print(payload)
            print("CAD_INSPECT=PASS")
        return 0

    ap.error("one operation is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
