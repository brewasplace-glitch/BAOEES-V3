from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument("--inventory",required=True);p.add_argument("--executable",required=True);p.add_argument("--package-version",required=True);a=p.parse_args()
t=Path(a.inventory).read_text(encoding="utf-8",errors="replace").replace("\\","/").lower()
if not a.package_version.startswith("2.23"): raise RuntimeError("Unexpected package version")
if not Path(a.executable).is_file(): raise RuntimeError("ccx.exe missing")
if "mingw64/bin/ccx.exe" not in t: raise RuntimeError("inventory lacks ccx.exe")
print(json.dumps({"status":"VERIFIED","provider":"MSYS2","package_version":a.package_version,"executable":a.executable},indent=2))
