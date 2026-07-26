from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable
from .base import ExternalApplicationAdapter

class SketchUpAdapter(ExternalApplicationAdapter):
    application_name = "SketchUp"
    def candidate_executables(self) -> Iterable[Path]:
        explicit = os.environ.get("PHOENIX_SKETCHUP_EXE")
        if explicit:
            yield Path(explicit)
        for root in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "SketchUp",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "SketchUp",
        ):
            if root.is_dir():
                yield from sorted(root.glob("SketchUp */SketchUp.exe"), reverse=True)
                yield from sorted(root.glob("*/SketchUp.exe"), reverse=True)
