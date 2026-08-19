from __future__ import annotations
import importlib.util
import shutil
from typing import Dict

def detect_open_source_stack() -> Dict[str, dict]:
    def py(name):
        return importlib.util.find_spec(name) is not None

    return {
        "ifcopenshell": {"available": py("ifcopenshell"), "role": "primary_authoritative_ifc_adapter", "license_family": "LGPL-3.0-or-later"},
        "shapely": {"available": py("shapely"), "role": "2D geometry / footprint operations", "license_family": "BSD-3-Clause"},
        "networkx": {"available": py("networkx"), "role": "space adjacency graph", "license_family": "BSD-3-Clause"},
        "pymoo": {"available": py("pymoo"), "role": "multi-objective optimisation", "license_family": "Apache-2.0"},
        "freecad": {"available": shutil.which("FreeCADCmd") is not None or shutil.which("freecadcmd") is not None, "role": "parametric_bim_cad_fallback", "license_family": "LGPL-2.0-or-later"},
        "energyplus": {"available": shutil.which("energyplus") is not None, "role": "thermal/energy simulation", "license_family": "BSD-like"},
        "blender": {"available": shutil.which("blender") is not None, "role": "3D/final rendering", "license_family": "GPL"}
    }
