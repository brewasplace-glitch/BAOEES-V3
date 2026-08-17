"""Phoenix CalculiX adapter foundation v1.0."""
from __future__ import annotations
import subprocess
from pathlib import Path
from phoenix.engines.engine_discovery_v1_0 import discover_engine

VERSION="1.0.0"

def capability_state(repository:Path)->dict:
    d=discover_engine("calculix",repository)
    return {
      **d,
      "adapter_version":VERSION,
      "capabilities":["STRUCTURAL_FEM","STATIC","NONLINEAR","THERMAL"],
      "execution_supported":bool(d["available"])
    }

def execute_deck(repository:Path,deck:Path,cwd:Path|None=None,timeout:int=300)->dict:
    state=capability_state(repository)
    if not state["available"]:
        raise RuntimeError("CALCULIX_ENGINE_NOT_AVAILABLE")
    deck=Path(deck).resolve()
    if not deck.exists() or deck.suffix.lower()!=".inp":
        raise ValueError("CalculiX deck must be an existing .inp file")
    work=Path(cwd).resolve() if cwd else deck.parent
    job=deck.stem
    proc=subprocess.run([state["executable"],"-i",job],cwd=str(work),capture_output=True,text=True,timeout=timeout)
    return {
      "engine":"calculix","adapter_version":VERSION,"executable":state["executable"],
      "returncode":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr,
      "job":job,"cwd":str(work),"passed":proc.returncode==0
    }
