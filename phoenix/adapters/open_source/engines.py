from __future__ import annotations
from pathlib import Path
from typing import Any
from .base import Detection, EngineAdapter, EngineSpec

class IfcOpenShellAdapter(EngineAdapter):
    def detect_python_module(self):
        import subprocess
        import sys
        probe = subprocess.run(
            [sys.executable, "-c", "import ifcopenshell; print(ifcopenshell.version)"],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if probe.returncode == 0:
            return Detection(
                self.spec.engine_id,
                True,
                sys.executable,
                "python_module",
                (probe.stdout or "").strip(),
                ["IfcOpenShell Python module detected"],
            )
        return None

    spec = EngineSpec(
        "ifcopenshell", "IfcOpenShell / IfcConvert",
        ("IfcConvert.exe","IfcConvert","ifcconvert"),
        ("IFCCONVERT_EXE","IFCOPENSHELL_HOME"),
        (".ifc",".ifczip",".ifcxml"),
        (".glb",".obj",".dae",".svg",".xml",".ifc",".stp",".igs"),
        "https://docs.ifcopenshell.org/"
    )
    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        output = Path(job["output_dir"]) / job.get("output_name", "model.glb")
        cmd = [executable]
        cmd.extend(str(x) for x in job.get("options", []))
        cmd.extend([str(Path(job["input_path"]).resolve()), str(output.resolve())])
        return cmd

class FreeCADAdapter(EngineAdapter):
    spec = EngineSpec(
        "freecad", "FreeCAD command line",
        ("FreeCADCmd.exe","freecadcmd.exe","FreeCADCmd","freecadcmd"),
        ("FREECAD_CMD","FREECAD_HOME"),
        (".py",".fcstd",".step",".stp",".iges",".igs",".ifc"),
        (".fcstd",".step",".stp",".iges",".igs",".dxf",".svg",".obj",".stl"),
        "https://www.freecad.org/"
    )
    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        inp = Path(job["input_path"]).resolve()
        if inp.suffix.lower() == ".py":
            return [executable, str(inp), *[str(x) for x in job.get("arguments", [])]]
        return [executable, str(inp)]

class EnergyPlusAdapter(EngineAdapter):
    spec = EngineSpec(
        "energyplus", "EnergyPlus",
        ("energyplus.exe","energyplus"),
        ("ENERGYPLUS_EXE","ENERGYPLUS_HOME"),
        (".idf",".epjson"),
        (".csv",".eso",".mtr",".sql",".html",".err"),
        "https://energyplus.net/documentation"
    )
    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        cmd=[executable,"-d",str(Path(job["output_dir"]).resolve())]
        weather=job.get("weather_file")
        if weather:
            cmd.extend(["-w",str(Path(weather).resolve())])
        cmd.extend(str(x) for x in job.get("options", []))
        cmd.append(str(Path(job["input_path"]).resolve()))
        return cmd

class OpenSeesAdapter(EngineAdapter):
    spec = EngineSpec(
        "opensees", "OpenSees",
        ("OpenSees.exe","OpenSees"),
        ("OPENSEES_EXE","OPENSEES_HOME"),
        (".tcl",),
        (".out",".csv",".txt",".json"),
        "https://opensees.github.io/OpenSeesDocumentation/"
    )
    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        return [executable,str(Path(job["input_path"]).resolve()),*[str(x) for x in job.get("arguments",[])]]

class CalculiXAdapter(EngineAdapter):
    spec = EngineSpec(
        "calculix", "CalculiX CrunchiX",
        ("ccx.exe","ccx"),
        ("CALCULIX_CCX","CALCULIX_HOME"),
        (".inp",),
        (".frd",".dat",".sta",".cvg"),
        "http://www.dhondt.de/"
    )
    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        inp=Path(job["input_path"]).resolve()
        # ccx expects a job name without .inp; use the absolute stem.
        return [executable,str(inp.with_suffix(""))]

class QGISAdapter(EngineAdapter):
    spec = EngineSpec(
        "qgis", "QGIS Processing Executor",
        ("qgis_process-qgis.exe","qgis_process.exe","qgis_process"),
        ("QGIS_PROCESS_EXE","QGIS_HOME"),
        (".json",".model3",".py",".gpkg",".shp",".geojson",".tif",".tiff"),
        (".gpkg",".shp",".geojson",".tif",".tiff",".csv",".html"),
        "https://docs.qgis.org/"
    )
    def build_command(self, job: dict[str, Any], executable: str) -> list[str]:
        algorithm=job.get("algorithm")
        if not algorithm:
            raise ValueError("QGIS job requires algorithm")
        parameters=job.get("parameters",{})
        cmd=[executable,"run",str(algorithm),"--"]
        for key in sorted(parameters):
            cmd.append(f"{key}={parameters[key]}")
        return cmd

ADAPTERS = {
    "ifcopenshell": IfcOpenShellAdapter,
    "freecad": FreeCADAdapter,
    "energyplus": EnergyPlusAdapter,
    "opensees": OpenSeesAdapter,
    "calculix": CalculiXAdapter,
    "qgis": QGISAdapter,
}

def create_adapter(engine_id: str) -> EngineAdapter:
    try:
        return ADAPTERS[engine_id]()
    except KeyError as exc:
        raise ValueError(f"Unknown engine: {engine_id}") from exc
