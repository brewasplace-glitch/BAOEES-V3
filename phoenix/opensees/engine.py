"""High-level Phoenix OpenSees integration engine."""

from pathlib import Path

from .evidence import save_analysis_evidence
from .models import AnalysisResult, StructuralModel
from .native_solver import solve_with_openseespy
from .offline_solver import solve_linear_2d_truss
from .runtime import OpenSeesRuntimeProbe


class OpenSeesIntegrationEngine:
    def __init__(self) -> None:
        self.runtime = OpenSeesRuntimeProbe()

    def analyze(
        self,
        model: StructuralModel,
        *,
        prefer_native: bool = True,
    ) -> AnalysisResult:
        info = self.runtime.probe()
        if prefer_native and info.openseespy_available:
            return solve_with_openseespy(model)
        return solve_linear_2d_truss(model)

    def analyze_and_save(
        self,
        model: StructuralModel,
        *,
        evidence_path: str | Path,
        prefer_native: bool = True,
    ) -> AnalysisResult:
        result = self.analyze(model, prefer_native=prefer_native)
        save_analysis_evidence(evidence_path, model=model, result=result)
        return result
