from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Iterable
import json

from .r2d_r4_opening_rule_engine import apply_rules


def repair_manifest_file(input_path: Path, output_path: Path, report_path: Path, policy_path: Path | None = None) -> Dict[str, Any]:
    manifest = json.loads(Path(input_path).read_text(encoding='utf-8'))
    policy = json.loads(Path(policy_path).read_text(encoding='utf-8')) if policy_path else {}
    repaired, report = apply_rules(manifest, policy)
    Path(output_path).write_text(json.dumps(repaired, indent=2), encoding='utf-8')
    Path(report_path).write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def exact_opening_id_gate(manifest_variant: Dict[str, Any], freecad_audit: Dict[str, Any], blender_audit: Dict[str, Any]) -> Dict[str, Any]:
    expected = {o['opening_id'] for o in manifest_variant.get('openings', [])}
    freecad = {o['opening_id'] for o in freecad_audit.get('openings', [])}
    blender = {o['opening_id'] for o in blender_audit.get('openings', [])}
    ok = expected == freecad == blender
    return {
        'status': 'PASS' if ok else 'FAIL',
        'expected': sorted(expected),
        'freecad': sorted(freecad),
        'blender': sorted(blender),
        'missing_freecad': sorted(expected-freecad),
        'missing_blender': sorted(expected-blender),
        'extra_freecad': sorted(freecad-expected),
        'extra_blender': sorted(blender-expected),
    }


def geometry_gate(manifest_openings: Iterable[Dict[str, Any]], freecad_openings: Iterable[Dict[str, Any]], blender_openings: Iterable[Dict[str, Any]], xy_tol: float = 0.02, z_tol: float = 0.08) -> Dict[str, Any]:
    mm={o['opening_id']:o for o in manifest_openings}; fm={o['opening_id']:o for o in freecad_openings}; bm={o['opening_id']:o for o in blender_openings}
    failures=[]
    for oid,o in mm.items():
        if oid not in fm or oid not in bm:
            failures.append({'opening_id':oid,'reason':'MISSING_ENGINE_RECORD'}); continue
        f,b=fm[oid],bm[oid]
        if o.get('orientation')!=f.get('orientation') or o.get('orientation')!=b.get('orientation'):
            failures.append({'opening_id':oid,'reason':'ORIENTATION_MISMATCH'}); continue
        if max(abs(float(o['center_xy'][i])-float(f['center_xy'][i])) for i in (0,1))>xy_tol or max(abs(float(o['center_xy'][i])-float(b['center_xy'][i])) for i in (0,1))>xy_tol:
            failures.append({'opening_id':oid,'reason':'XY_MISMATCH'}); continue
        if abs(float(f['actual_z0'])-float(b['actual_z0']))>z_tol or abs(float(f['actual_height_m'])-float(b['actual_height_m']))>z_tol:
            failures.append({'opening_id':oid,'reason':'Z_HEIGHT_MISMATCH'}); continue
    return {'status':'PASS' if not failures else 'FAIL','failures':failures,'xy_tolerance_m':xy_tol,'z_tolerance_m':z_tol}
