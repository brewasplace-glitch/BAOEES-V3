#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path

BEGIN="<!-- PHOENIX_DETV_CAD_BRIDGE_BEGIN -->"
END="<!-- PHOENIX_DETV_CAD_BRIDGE_END -->"
SCRIPT_NAME="phoenix_detv_cad_bridge.js"

def git_ls_files(repo: Path):
    p=subprocess.run(["git","-C",str(repo),"ls-files"],capture_output=True,text=True)
    if p.returncode!=0:
        raise RuntimeError(p.stderr or "git ls-files failed")
    return [x.strip().replace("\\","/") for x in p.stdout.splitlines() if x.strip()]

def score_candidate(path: str, text: str) -> int:
    p=path.lower(); t=text.lower(); s=0
    if "de tv" in t: s+=45
    if "de-tv" in t or "de_tv" in t: s+=35
    if "open-source player" in t or "open source player" in t: s+=22
    if "phoenix_3d_viewer" in t: s+=18
    if "media player" in t: s+=15
    if "start project" in t or "startscherm" in t or "start screen" in t: s+=12
    if "project phoenix" in t: s+=8
    if "tv" in p: s+=18
    if "dashboard" in p: s+=12
    if "start" in p or "index" in p: s+=8
    if "viewer" in p: s+=5
    if "3d_viewer" in p or "3d-viewer" in p: s-=30
    if p.startswith("outputs/"): s-=25
    if p.startswith("tests/") or "/test" in p: s-=40
    return s

def detect_host(repo: Path):
    c=[]
    for rel in git_ls_files(repo):
        low=rel.lower()
        if not low.endswith((".html",".htm")): continue
        if any(x in low for x in ("node_modules/",".venv/","venv/")): continue
        path=repo/rel
        try:
            if path.stat().st_size>5_000_000: continue
            text=path.read_text(encoding="utf-8-sig",errors="replace")
        except Exception:
            continue
        score=score_candidate(rel,text)
        if score>0: c.append((score,rel))
    c.sort(key=lambda x:(-x[0],len(x[1]),x[1]))
    if not c:
        raise RuntimeError("No tracked HTML candidate for PHOENIX DE TV/start screen found")
    score,rel=c[0]
    if score<25:
        raise RuntimeError(f"DE TV host confidence too low: {rel} score={score}")
    if len(c)>1 and c[1][0]==score:
        tied=[p for s,p in c if s==score]
        preferred=[p for p in tied if "tv" in p.lower() or "dashboard" in p.lower()]
        if len(preferred)==1: rel=preferred[0]
        else: raise RuntimeError("Ambiguous DE TV hosts: "+", ".join(tied[:8]))
    return {"host_rel":rel,"score":score,"top_candidates":[{"score":s,"path":p} for s,p in c[:10]]}

def inject_host_text(text: str) -> str:
    block=f'{BEGIN}\n<script src="./{SCRIPT_NAME}"></script>\n{END}'
    if BEGIN in text and END in text:
        a=text.index(BEGIN); b=text.index(END,a)+len(END)
        return text[:a]+block+text[b:]
    i=text.lower().rfind("</body>")
    if i>=0: return text[:i]+block+"\n"+text[i:]
    return text.rstrip()+"\n"+block+"\n"

def apply(repo: Path, bridge_source: Path, result: Path):
    d=detect_host(repo)
    host_rel=d["host_rel"]; host=repo/host_rel
    host.write_text(inject_host_text(host.read_text(encoding="utf-8-sig")),encoding="utf-8",newline="\n")
    bridge_rel=(Path(host_rel).parent/SCRIPT_NAME).as_posix()
    bridge=repo/bridge_rel
    bridge.write_bytes(bridge_source.read_bytes())
    d.update({"bridge_rel":bridge_rel,"status":"PASS"})
    result.write_text(json.dumps(d,indent=2),encoding="utf-8")
    return d

def verify(repo: Path, result: Path):
    d=json.loads(result.read_text(encoding="utf-8"))
    h=(repo/d["host_rel"]).read_text(encoding="utf-8-sig",errors="replace")
    if BEGIN not in h or END not in h or SCRIPT_NAME not in h:
        raise RuntimeError("DE TV host marker/script missing")
    if not (repo/d["bridge_rel"]).exists():
        raise RuntimeError("DE TV bridge JS missing")
    return d

def self_test():
    h="<html><body><h1>PROJECT PHOENIX DE TV</h1></body></html>"
    assert score_candidate("apps/dashboard/index.html",h)>=25
    p=inject_host_text(h); p2=inject_host_text(p)
    assert p2.count(BEGIN)==1 and SCRIPT_NAME in p2
    print("PHOENIX_4_41_DETV_CAD_PATCHER_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path)
    ap.add_argument("--bridge-source",type=Path)
    ap.add_argument("--result",type=Path)
    ap.add_argument("--detect",action="store_true")
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--verify",action="store_true")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.repo_root: ap.error("--repo-root required")
    repo=a.repo_root.resolve()
    if a.detect:
        print(json.dumps(detect_host(repo),indent=2)); return 0
    if a.apply:
        if not a.bridge_source or not a.result: ap.error("--bridge-source/--result required")
        print(json.dumps(apply(repo,a.bridge_source,a.result),indent=2))
        print("DETV_CAD_HOST_PATCH=PASS"); return 0
    if a.verify:
        if not a.result: ap.error("--result required")
        print(json.dumps(verify(repo,a.result),indent=2))
        print("DETV_CAD_HOST_VERIFY=PASS"); return 0
    ap.error("choose operation")

if __name__=="__main__":
    raise SystemExit(main())
