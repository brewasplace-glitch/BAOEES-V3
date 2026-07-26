"""Default dependency catalog for PROJECT-PHOENIX."""

from __future__ import annotations

from .models import DependencyKind, DependencySpec


def default_dependency_catalog() -> tuple[DependencySpec, ...]:
    return (
        DependencySpec(
            id="PTDM-PYTHON",
            name="Python",
            kind=DependencyKind.EXECUTABLE,
            required=True,
            capability="phoenix_runtime",
            executable_names=("python.exe", "python3.exe", "py.exe"),
            environment_variables=("PHOENIX_PYTHON_EXE",),
        ),
        DependencySpec(
            id="PTDM-GIT",
            name="Git",
            kind=DependencyKind.EXECUTABLE,
            required=True,
            capability="version_control",
            executable_names=("git.exe",),
            environment_variables=("PHOENIX_GIT_EXE",),
            windows_candidates=(
                r"%ProgramFiles%\Git\cmd\git.exe",
                r"%ProgramFiles%\Git\bin\git.exe",
            ),
        ),
        DependencySpec(
            id="PTDM-IFCOPENSHELL",
            name="IfcOpenShell",
            kind=DependencyKind.PYTHON_PACKAGE,
            required=True,
            capability="ifc_processing",
            python_import_name="ifcopenshell",
            python_distribution_name="ifcopenshell",
        ),
        DependencySpec(
            id="PTDM-OPENSEESPY",
            name="OpenSeesPy",
            kind=DependencyKind.PYTHON_PACKAGE,
            required=False,
            capability="structural_analysis",
            python_import_name="openseespy",
            python_distribution_name="openseespy",
        ),
        DependencySpec(
            id="PTDM-FREECAD",
            name="FreeCAD",
            kind=DependencyKind.EXECUTABLE,
            required=False,
            capability="parametric_bim",
            executable_names=("FreeCAD.exe", "FreeCADCmd.exe"),
            environment_variables=("PHOENIX_FREECAD_EXE",),
            windows_candidates=(
                r"%ProgramFiles%\FreeCAD*\bin\FreeCAD.exe",
                r"%ProgramFiles%\FreeCAD*\bin\FreeCADCmd.exe",
            ),
        ),
        DependencySpec(
            id="PTDM-BLENDER",
            name="Blender",
            kind=DependencyKind.EXECUTABLE,
            required=False,
            capability="visualization",
            executable_names=("blender.exe",),
            environment_variables=("PHOENIX_BLENDER_EXE",),
            windows_candidates=(
                r"%ProgramFiles%\Blender Foundation\Blender*\blender.exe",
            ),
        ),
        DependencySpec(
            id="PTDM-CALCULIX",
            name="CalculiX",
            kind=DependencyKind.EXECUTABLE,
            required=False,
            capability="finite_element_analysis",
            executable_names=("ccx.exe",),
            environment_variables=("PHOENIX_CALCULIX_EXE",),
        ),
        DependencySpec(
            id="PTDM-SKETCHUP",
            name="SketchUp",
            kind=DependencyKind.EXECUTABLE,
            required=False,
            capability="concept_modeling",
            executable_names=("SketchUp.exe",),
            environment_variables=("PHOENIX_SKETCHUP_EXE",),
            windows_candidates=(
                r"%ProgramFiles%\SketchUp\SketchUp *\SketchUp.exe",
                r"%ProgramFiles(x86)%\SketchUp\SketchUp *\SketchUp.exe",
            ),
        ),
        DependencySpec(
            id="PTDM-SCIA",
            name="SCIA Engineer",
            kind=DependencyKind.EXECUTABLE,
            required=False,
            capability="structural_validation",
            executable_names=("Esa.exe", "SciaEngineer.exe"),
            environment_variables=("PHOENIX_SCIA_EXE",),
            windows_candidates=(
                r"%ProgramFiles%\SCIA\Engineer*\Esa.exe",
                r"%ProgramFiles(x86)%\SCIA\Engineer*\Esa.exe",
                r"%ProgramFiles%\SCIA Engineer*\Esa.exe",
                r"%ProgramFiles(x86)%\SCIA Engineer*\Esa.exe",
            ),
        ),
    )
