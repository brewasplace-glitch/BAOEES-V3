"""OpenSeesPy runtime discovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
from typing import Optional


@dataclass
class OpenSeesRuntimeInfo:
    openseespy_available: bool
    module_name: Optional[str]
    mode: str

    def to_dict(self) -> dict:
        return asdict(self)


class OpenSeesRuntimeProbe:
    def probe(self) -> OpenSeesRuntimeInfo:
        try:
            package_available = importlib.util.find_spec("openseespy") is not None
            available = (
                package_available
                and importlib.util.find_spec("openseespy.opensees") is not None
            )
        except (ImportError, ModuleNotFoundError, AttributeError):
            available = False

        return OpenSeesRuntimeInfo(
            openseespy_available=available,
            module_name="openseespy.opensees" if available else None,
            mode="native" if available else "offline",
        )
