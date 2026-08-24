"""Project Phoenix default document routing via LibreOffice v1.0.

Policy:
- Office-family documents open through the proven LibreOffice adapter.
- PDF and non-Office artifacts continue through the operating-system default viewer.
- Phoenix native DOCX/PDF/XLSX generators remain authoritative and unchanged.
- LibreOffice provides open/convert interoperability, not replacement generation.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from phoenix.engines.adapters.libreoffice_office_adapter_v1_0 import (
    LibreOfficeOfficeAdapter,
)

OFFICE_EXTENSIONS = {
    ".doc", ".docx", ".odt", ".rtf",
    ".xls", ".xlsx", ".ods", ".csv",
    ".ppt", ".pptx", ".odp",
}


def is_office_document(path: str | Path) -> bool:
    return Path(path).suffix.lower() in OFFICE_EXTENSIONS


def open_document_path(path: str | Path) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.exists():
        raise FileNotFoundError(target)

    if is_office_document(target):
        return LibreOfficeOfficeAdapter().open_document(target)

    if os.name == "nt":
        os.startfile(str(target))
        return {
            "status": "STARTED",
            "engine": "SYSTEM_DEFAULT",
            "input": str(target),
        }

    if sys.platform == "darwin":  # pragma: no cover
        subprocess.Popen(["open", str(target)])
    else:  # pragma: no cover
        subprocess.Popen(["xdg-open", str(target)])

    return {
        "status": "STARTED",
        "engine": "SYSTEM_DEFAULT",
        "input": str(target),
    }


def create_pdf_companion(
    input_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    source = Path(input_path).resolve()
    if not is_office_document(source):
        raise ValueError(
            f"PDF companion is only supported for Office-family input: {source}"
        )
    return LibreOfficeOfficeAdapter().convert(
        source,
        "pdf",
        output_dir,
    )
