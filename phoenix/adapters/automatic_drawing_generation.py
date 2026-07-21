from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from html import escape
import json, math, tempfile
from pathlib import Path
from phoenix.orchestration.runtime import AdapterResult

class AutomaticDrawingGenerationError(ValueError):
    pass

@dataclass(frozen=True)
class AutomaticDrawingGenerationConfig:
    project_id: str
    bim_synchronization_artifact: str | Path
    output_directory: str | Path
    drawing_prefix: str = "PHX"
    revision: str = "P01"
    title: str = "Phoenix Structural Drawing Set"
    author: str = "Project Phoenix"
    sheet_width_mm: float = 841.0
    sheet_height_mm: float = 594.0
    margin_mm: float = 20.0

    def validate(self):
        if not self.project_id.strip():
            raise AutomaticDrawingGenerationError("project_id is required.")
        if not Path(self.bim_synchronization_artifact).is_file():
            raise AutomaticDrawingGenerationError("BIM artifact does not exist.")
        if not self.drawing_prefix.strip() or not self.revision.strip():
            raise AutomaticDrawingGenerationError("Prefix and revision are required.")
        if min(self.sheet_width_mm, self.sheet_height_mm, self.margin_mm) <= 0:
            raise AutomaticDrawingGenerationError("Sheet values must be positive.")
        if self.margin_mm * 2 >= min(self.sheet_width_mm, self.sheet_height_mm):
            raise AutomaticDrawingGenerationError("Margins leave no drawable area.")

def _canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def _verified(path, project_id):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutomaticDrawingGenerationError("Unable to read BIM artifact.") from exc
    if data.get("schema") != "phoenix-bim-ifc-synchronization-v1.0":
        raise AutomaticDrawingGenerationError("Wave 13 BIM artifact required.")
    if data.get("project_id") != project_id:
        raise AutomaticDrawingGenerationError("project_id mismatch.")
    unsigned = dict(data)
    expected = unsigned.pop("artifact_sha256", None)
    if expected != sha256(_canonical(unsigned).encode("utf-8")).hexdigest():
        raise AutomaticDrawingGenerationError("BIM artifact integrity failed.")
    status = (data.get("synchronization_summary") or {}).get("synchronization_status")
    if status != "ready_for_ifc_serialization":
        raise AutomaticDrawingGenerationError("BIM artifact is not ready.")
    return data

def _model(bim):
    nodes = {}
    for item in bim.get("nodes") or []:
        coords = item.get("coordinates_m")
        if not item.get("phoenix_id") or not isinstance(coords, list) or len(coords) != 3:
            raise AutomaticDrawingGenerationError("Invalid BIM node.")
        point = tuple(float(v) for v in coords)
        if not all(math.isfinite(v) for v in point):
            raise AutomaticDrawingGenerationError("Non-finite BIM coordinate.")
        nodes[item["phoenix_id"]] = point
    segments = []
    for item in bim.get("elements") or []:
        ids = item.get("node_ids") or []
        if len(ids) != 2:
            raise AutomaticDrawingGenerationError("Only two-node line elements are supported.")
        if ids[0] not in nodes or ids[1] not in nodes:
            raise AutomaticDrawingGenerationError("Unknown node reference.")
        segments.append((item["phoenix_id"], nodes[ids[0]], nodes[ids[1]]))
    if not nodes or not segments:
        raise AutomaticDrawingGenerationError("Nodes and elements are required.")
    return sorted(segments)

def _atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                     dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp = Path(handle.name)
    temp.replace(path)

def _svg(segments, projection, cfg, sheet, title):
    def project(p):
        return (p[0], p[1]) if projection == "plan" else (p[0], p[2])
    points = [project(p) for _, a, b in segments for p in (a, b)]
    minx, maxx = min(p[0] for p in points), max(p[0] for p in points)
    miny, maxy = min(p[1] for p in points), max(p[1] for p in points)
    if math.isclose(minx, maxx): maxx += 1.0
    if math.isclose(miny, maxy): maxy += 1.0
    draw_w = cfg.sheet_width_mm - 2 * cfg.margin_mm
    draw_h = cfg.sheet_height_mm - 2 * cfg.margin_mm - 45.0
    scale = min(draw_w / (maxx-minx), draw_h / (maxy-miny)) * 0.82
    def tr(p):
        x, y = project(p)
        return cfg.margin_mm + (x-minx)*scale, cfg.margin_mm + draw_h - (y-miny)*scale
    geometry = []
    for eid, a, b in segments:
        x1, y1 = tr(a); x2, y2 = tr(b)
        geometry.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" class="s"/>'
        )
        geometry.append(
            f'<text x="{(x1+x2)/2:.3f}" y="{(y1+y2)/2-2:.3f}" class="t">{escape(eid)}</text>'
        )
    ty = cfg.sheet_height_mm - cfg.margin_mm - 45.0
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.sheet_width_mm}mm" height="{cfg.sheet_height_mm}mm" viewBox="0 0 {cfg.sheet_width_mm} {cfg.sheet_height_mm}">',
        '<style>.b{fill:none;stroke:#000;stroke-width:.35}.s{stroke:#000;stroke-width:.7}.t{font:3px sans-serif;text-anchor:middle}.x{font:3.2px sans-serif}.h{font:bold 6px sans-serif}</style>',
        f'<rect x="{cfg.margin_mm}" y="{cfg.margin_mm}" width="{cfg.sheet_width_mm-2*cfg.margin_mm}" height="{cfg.sheet_height_mm-2*cfg.margin_mm}" class="b"/>',
        f'<text x="{cfg.margin_mm}" y="{cfg.margin_mm-4}" class="h">{escape(title)}</text>',
        *geometry,
        f'<text x="{cfg.margin_mm}" y="{ty-6}" class="x">OVERALL {(maxx-minx):.3f} m x {(maxy-miny):.3f} m</text>',
        f'<rect x="{cfg.margin_mm}" y="{ty}" width="{cfg.sheet_width_mm-2*cfg.margin_mm}" height="45" class="b"/>',
        f'<text x="{cfg.margin_mm+4}" y="{ty+10}" class="h">{escape(cfg.title)}</text>',
        f'<text x="{cfg.margin_mm+4}" y="{ty+20}" class="x">PROJECT: {escape(cfg.project_id)}</text>',
        f'<text x="{cfg.margin_mm+4}" y="{ty+29}" class="x">AUTHOR: {escape(cfg.author)}</text>',
        f'<text x="{cfg.sheet_width_mm-200}" y="{ty+10}" class="x">SHEET: {escape(sheet)}</text>',
        f'<text x="{cfg.sheet_width_mm-200}" y="{ty+20}" class="x">REVISION: {escape(cfg.revision)}</text>',
        f'<text x="{cfg.sheet_width_mm-200}" y="{ty+29}" class="x">SCALE: AUTO-FIT</text>',
        '</svg>',
    ]
    return "\n".join(parts) + "\n"

def _dxf(segments):
    def pair(code, value):
        return f"{code}\n{value}\n"
    out = pair(0,"SECTION")+pair(2,"HEADER")+pair(9,"$ACADVER")+pair(1,"AC1009")+pair(0,"ENDSEC")
    out += pair(0,"SECTION")+pair(2,"ENTITIES")
    for eid, a, b in segments:
        out += pair(0,"LINE")+pair(8,"PHX_STRUCTURE")
        out += pair(10,f"{a[0]:.9f}")+pair(20,f"{a[1]:.9f}")+pair(30,f"{a[2]:.9f}")
        out += pair(11,f"{b[0]:.9f}")+pair(21,f"{b[1]:.9f}")+pair(31,f"{b[2]:.9f}")
        out += pair(0,"TEXT")+pair(8,"PHX_ID")
        out += pair(10,f"{(a[0]+b[0])/2:.9f}")+pair(20,f"{(a[1]+b[1])/2:.9f}")+pair(30,f"{(a[2]+b[2])/2:.9f}")
        out += pair(40,"0.20")+pair(1,eid)
    return out + pair(0,"ENDSEC") + pair(0,"EOF")

def create_automatic_drawing_generation_adapter(config):
    config.validate()
    def adapter(*, project_id, engine_id, plan_fingerprint):
        if engine_id != "automatic_drawing_generation":
            raise AutomaticDrawingGenerationError("Unsupported engine_id.")
        if project_id != config.project_id or not plan_fingerprint.strip():
            raise AutomaticDrawingGenerationError("Invalid runtime identity.")
        source = Path(config.bim_synchronization_artifact)
        bim = _verified(source, project_id)
        segments = _model(bim)
        out = Path(config.output_directory)
        drawing_dir = out / "drawings"
        files = [
            (drawing_dir/f"{config.drawing_prefix}-S-101_{config.revision}.svg",
             _svg(segments,"plan",config,f"{config.drawing_prefix}-S-101","STRUCTURAL PLAN"),
             "structural_plan"),
            (drawing_dir/f"{config.drawing_prefix}-S-201_{config.revision}.svg",
             _svg(segments,"elevation",config,f"{config.drawing_prefix}-S-201","STRUCTURAL ELEVATION X-Z"),
             "structural_elevation"),
            (drawing_dir/f"{config.drawing_prefix}-S-MODEL_{config.revision}.dxf",
             _dxf(segments),"structural_model_linework"),
        ]
        records = []
        for path, content, kind in files:
            _atomic(path, content)
            records.append({
                "drawing_id": path.stem, "drawing_type": kind,
                "format": path.suffix[1:].lower(), "path": path.as_posix(),
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "revision": config.revision, "status": "generated_for_review",
            })
        register = {
            "schema":"phoenix-drawing-register-v1.0",
            "project_id":project_id,
            "source_bim_artifact":source.as_posix(),
            "source_bim_artifact_sha256":bim["artifact_sha256"],
            "drawings":records,
            "summary":{"drawing_count":3,"svg_count":2,"dxf_count":1,
                       "element_count":len(segments),"status":"generated_for_review"},
            "claims_policy":{"permit_ready_not_claimed":True,
                             "construction_ready_not_claimed":True,
                             "dwg_not_generated":True,"pdf_not_generated":True,
                             "reinforcement_detailing_not_generated":True,
                             "competent_engineer_review_required":True},
        }
        register["artifact_sha256"] = sha256(_canonical(register).encode("utf-8")).hexdigest()
        register_path = out/"drawing_register_v1_0.json"
        _atomic(register_path, json.dumps(register, indent=2)+"\n")
        manifest = {
            "schema":"phoenix-drawing-package-manifest-v1.0",
            "project_id":project_id,
            "drawing_register":register_path.as_posix(),
            "drawing_register_sha256":sha256(register_path.read_bytes()).hexdigest(),
            "files":[{"path":r["path"],"sha256":r["sha256"]} for r in records],
        }
        manifest["artifact_sha256"] = sha256(_canonical(manifest).encode("utf-8")).hexdigest()
        manifest_path = out/"drawing_package_manifest_v1_0.json"
        _atomic(manifest_path, json.dumps(manifest, indent=2)+"\n")
        return AdapterResult(
            outputs=tuple([r["path"] for r in records]+[register_path.as_posix(),manifest_path.as_posix()]),
            evidence=(f'drawing-package-manifest:{manifest["artifact_sha256"]}',
                      f'drawings-generated:{len(records)}'),
            metadata={"adapter":"phoenix_automatic_drawing_generation_v1_0",
                      "drawing_count":3,"status":"generated_for_review",
                      "dwg_generated":False,"pdf_generated":False},
        )
    return adapter
