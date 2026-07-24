from dataclasses import asdict, dataclass
from pathlib import Path
import os, shutil

@dataclass
class CalculiXRuntimeInfo:
    executable: str | None
    available: bool
    mode: str
    def to_dict(self): return asdict(self)

class CalculiXRuntimeProbe:
    def probe(self):
        configured = os.environ.get("CALCULIX_CCX")
        if configured and Path(configured).exists():
            return CalculiXRuntimeInfo(configured, True, "native")
        for candidate in ("ccx", "ccx.exe", "calculix", "calculix.exe"):
            found = shutil.which(candidate)
            if found: return CalculiXRuntimeInfo(found, True, "native")
        return CalculiXRuntimeInfo(None, False, "offline")
