"""QGIS runtime discovery and capability probing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import os
from pathlib import Path
import shutil
from typing import Optional


@dataclass
class QGISRuntimeInfo:
    pyqgis_available: bool
    qgis_process: Optional[str]
    qgis_prefix_path: Optional[str]
    mode: str

    def to_dict(self) -> dict:
        return asdict(self)


class QGISRuntimeProbe:
    """Detects optional QGIS/PyQGIS runtime without requiring it."""

    def probe(self) -> QGISRuntimeInfo:
        pyqgis_available = importlib.util.find_spec("qgis") is not None
        qgis_process = shutil.which("qgis_process")
        prefix = os.environ.get("QGIS_PREFIX_PATH")

        mode = "native" if pyqgis_available or qgis_process else "offline"
        return QGISRuntimeInfo(
            pyqgis_available=pyqgis_available,
            qgis_process=qgis_process,
            qgis_prefix_path=prefix,
            mode=mode,
        )

    @staticmethod
    def validate_prefix(path: str | None) -> bool:
        if not path:
            return False
        return Path(path).exists()
