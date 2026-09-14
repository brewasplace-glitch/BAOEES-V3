from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class GateResult:
    passed: bool
    checks: dict[str,bool]
    missing: tuple[str,...]

class EvidenceGate:
    REQUIRED=("baseline","risk","plan","tests","diff_check","scope","evidence")

    def evaluate(self, checks: dict[str,bool])->GateResult:
        normalized={name:bool(checks.get(name,False)) for name in self.REQUIRED}
        missing=tuple(name for name,value in normalized.items() if not value)
        return GateResult(not missing,normalized,missing)
