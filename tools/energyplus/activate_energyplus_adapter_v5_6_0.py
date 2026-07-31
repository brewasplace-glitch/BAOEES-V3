from pathlib import Path
import re,sys
p=Path(sys.argv[1]);t=p.read_text(encoding="utf-8-sig");base="from .base import Detection, EngineAdapter, EngineSpec";imp="from .energyplus_adapter_v5_6_0 import EnergyPlusWindowsAdapter"
if imp not in t:t=t.replace(base,base+"\n"+imp) if base in t else imp+"\n"+t
t=re.sub(r'("energyplus"\s*:\s*)EnergyPlusAdapter(?:\s*\(\s*\))?',r'\1EnergyPlusWindowsAdapter',t)
t=re.sub(r'("energyplus"\s*:\s*)EnergyPlusWindowsAdapter\s*\(\s*\)',r'\1EnergyPlusWindowsAdapter',t)
if not re.search(r'"energyplus"\s*:\s*EnergyPlusWindowsAdapter(?!\s*\()',t):raise RuntimeError("EnergyPlus class reference missing")
p.write_text(t,encoding="utf-8",newline="\n");print("ENERGYPLUS REGISTRY CLASS REFERENCE: VERIFIED")
