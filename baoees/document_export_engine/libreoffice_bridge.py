"""LibreOffice bridge for the existing BAOEES/Phoenix DocumentExportEngine.

This file keeps the existing document engine intact and exposes a thin reusable
bridge to the central Phoenix LibreOffice adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from phoenix.engines.adapters.libreoffice_office_adapter_v1_0 import (
    LibreOfficeOfficeAdapter,
)


class DocumentExportLibreOfficeBridge:
    def __init__(self) -> None:
        self._libreoffice = LibreOfficeOfficeAdapter()

    def libreoffice_capability(self) -> dict[str, Any]:
        return self._libreoffice.capability()

    def convert_office_document(
        self,
        input_path: str | Path,
        target_format: str,
        output_dir: str | Path,
    ) -> dict[str, Any]:
        return self._libreoffice.convert(
            input_path,
            target_format,
            output_dir,
        )

    def open_office_document(self, input_path: str | Path) -> dict[str, Any]:
        return self._libreoffice.open_document(input_path)
