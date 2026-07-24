from __future__ import annotations
from math import dist
from pathlib import Path
import json, hashlib, subprocess
from .models import FEAnalysisResult, FEModel
from .runtime import CalculiXRuntimeProbe

def render_inp(model: FEModel) -> str:
    model.validate()
    nt = {n.node_id: i for i, n in enumerate(model.nodes, 1)}
    mt = {m.material_id: i for i, m in enumerate(model.materials, 1)}
    lines = ["*HEADING", f"PHOENIX BB14: {model.name}", "*NODE"]
    for n in model.nodes:
        lines.append(f"{nt[n.node_id]}, {n.x:.12g}, {n.y:.12g}, {n.z:.12g}")
    if model.beam_elements:
        lines.append("*ELEMENT, TYPE=B31, ELSET=EALL")
        for i, e in enumerate(model.beam_elements, 1):
            lines.append(f"{i}, {nt[e.start_node_id]}, {nt[e.end_node_id]}")
    for m in model.materials:
        lines += [f"*MATERIAL, NAME=MAT_{mt[m.material_id]}", "*ELASTIC",
                  f"{m.elastic_modulus:.12g}, {m.poisson_ratio:.12g}"]
        if m.density > 0: lines += ["*DENSITY", f"{m.density:.12g}"]
    for i, e in enumerate(model.beam_elements, 1):
        lines += [f"*ELSET, ELSET=E_{i}", str(i),
                  f"*BEAM SECTION, ELSET=E_{i}, MATERIAL=MAT_{mt[e.material_id]}, SECTION=GENERAL",
                  f"{e.area:.12g}, {e.second_moment_y:.12g}, {e.second_moment_z:.12g}, {e.torsional_constant:.12g}",
                  "0., 0., 1."]
    if model.boundary_conditions:
        lines.append("*BOUNDARY")
        for b in model.boundary_conditions:
            lines.append(f"{nt[b.node_id]}, {b.dof_start}, {b.dof_end}, {b.value:.12g}")
    lines += ["*STEP", "*STATIC"]
    if model.concentrated_loads:
        lines.append("*CLOAD")
        for load in model.concentrated_loads:
            lines.append(f"{nt[load.node_id]}, {load.dof}, {load.magnitude:.12g}")
    lines += ["*NODE FILE", "U, RF", "*EL FILE", "S, E", "*END STEP", ""]
    return "\n".join(lines)

def solve_offline(model: FEModel) -> FEAnalysisResult:
    model.validate()
    if len(model.nodes) != 2 or len(model.beam_elements) != 1:
        raise ValueError("offline solver supports one cantilever beam")
    e = model.beam_elements[0]
    start = next(n for n in model.nodes if n.node_id == e.start_node_id)
    end = next(n for n in model.nodes if n.node_id == e.end_node_id)
    mat = next(m for m in model.materials if m.material_id == e.material_id)
    fixed = any(b.node_id == start.node_id and b.dof_start == 1 and b.dof_end == 6 for b in model.boundary_conditions)
    loads = [l for l in model.concentrated_loads if l.node_id == end.node_id and l.dof in (2, 3)]
    if not fixed or len(loads) != 1: raise ValueError("offline cantilever setup invalid")
    load = loads[0]
    length = dist((start.x,start.y,start.z),(end.x,end.y,end.z))
    inertia = e.second_moment_z if load.dof == 2 else e.second_moment_y
    delta = load.magnitude * length**3 / (3 * mat.elastic_modulus * inertia)
    theta = load.magnitude * length**2 / (2 * mat.elastic_modulus * inertia)
    rotation_dof = 6 if load.dof == 2 else 5
    d0, d1, r0 = [0.0]*6, [0.0]*6, [0.0]*6
    d1[load.dof-1] = delta
    d1[rotation_dof-1] = theta
    r0[load.dof-1] = -load.magnitude
    r0[rotation_dof-1] = -load.magnitude * length
    return FEAnalysisResult(
        model.model_id, "linear_static_single_cantilever", True, "offline",
        {start.node_id:d0, end.node_id:d1},
        {start.node_id:r0, end.node_id:[0.0]*6},
        {e.element_id:{"length":length,"tip_deflection":delta,"tip_rotation":theta}},
        {"scope":"single_cantilever_verification"}
    )

class CalculiXIntegrationEngine:
    def __init__(self): self.runtime = CalculiXRuntimeProbe()
    def analyze_and_save(self, model, working_directory, evidence_path, prefer_native=True):
        work = Path(working_directory); work.mkdir(parents=True, exist_ok=True)
        inp = work / f"{model.model_id}.inp"
        inp.write_text(render_inp(model), encoding="utf-8", newline="\n")
        runtime = self.runtime.probe()
        if prefer_native and runtime.available:
            completed = subprocess.run([runtime.executable, inp.stem], cwd=work, capture_output=True, text=True)
            if completed.returncode != 0: raise RuntimeError(completed.stderr)
            result = FEAnalysisResult(model.model_id, "calculix_native_static", True, "native",
                                      diagnostics={"stdout":completed.stdout})
        else:
            result = solve_offline(model)
        payload = {"schema_version":"1.0","model":model.to_dict(),"result":result.to_dict(),"input_deck":str(inp)}
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        path = Path(evidence_path); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        result.checksum_sha256 = hashlib.sha256(data).hexdigest()
        return result
