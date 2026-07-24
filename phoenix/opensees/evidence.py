"""Structural-analysis evidence persistence."""

from __future__ import annotations

from pathlib import Path

from phoenix.database.persistence import save_json

from .models import AnalysisResult, StructuralModel


def save_analysis_evidence(
    path: str | Path,
    *,
    model: StructuralModel,
    result: AnalysisResult,
) -> str:
    payload = {
        "schema_version": "1.0",
        "model": model.to_dict(),
        "result": result.to_dict(),
    }
    checksum = save_json(Path(path), payload)
    result.checksum_sha256 = checksum
    return checksum
