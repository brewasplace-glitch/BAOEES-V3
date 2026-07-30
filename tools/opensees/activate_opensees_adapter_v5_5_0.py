from pathlib import Path
import re, sys

def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: activate_opensees_adapter_v5_5_0.py <engines.py>")
    path=Path(sys.argv[1]);text=path.read_text(encoding="utf-8-sig")
    base="from .base import Detection, EngineAdapter, EngineSpec"
    imp="from .opensees_adapter_v5_5_0 import OpenSeesPyAdapter"
    if imp not in text:
        text=text.replace(base,base+"\n"+imp) if base in text else imp+"\n"+text
    for pat,repl in (
        (r'("opensees"\s*:\s*)OpenSeesAdapter\s*\(\s*\)',r'\1OpenSeesPyAdapter'),
        (r'("opensees"\s*:\s*)OpenSeesAdapter\b',r'\1OpenSeesPyAdapter'),
        (r'("opensees"\s*:\s*)OpenSeesPyAdapter\s*\(\s*\)',r'\1OpenSeesPyAdapter'),
    ):
        text=re.sub(pat,repl,text)
    if not re.search(r'"opensees"\s*:\s*OpenSeesPyAdapter(?!\s*\()',text):
        raise RuntimeError("OpenSees registry class reference not found")
    if "OpenSeesPyAdapter()" in text:
        raise RuntimeError("OpenSees registry contains an adapter instance")
    path.write_text(text,encoding="utf-8",newline="\n")
    print("OPENSEES REGISTRY CLASS REFERENCE: VERIFIED")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
