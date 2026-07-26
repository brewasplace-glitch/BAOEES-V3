from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable
from .base import ExternalApplicationAdapter

class SciaEngineerAdapter(ExternalApplicationAdapter):
    application_name = "SCIA Engineer"
    def candidate_executables(self) -> Iterable[Path]:
        explicit = os.environ.get("PHOENIX_SCIA_EXE")
        if explicit:
            yield Path(explicit)
        patterns = (
            "SCIA/Engineer*/Esa.exe",
            "SCIA/Engineer*/SciaEngineer.exe",
            "SCIA Engineer*/Esa.exe",
            "SCIA Engineer*/SciaEngineer.exe",
        )
        for root in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        ):
            if root.is_dir():
                for pattern in patterns:
                    yield from sorted(root.glob(pattern), reverse=True)
