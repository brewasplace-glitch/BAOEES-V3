#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HOST_DIR_REL="phoenix/local_app/static/official_start_v3_0"
HOST_REL=HOST_DIR_REL+"/index.html"
TEXT_EXTS={".html",".htm",".js",".json",".css"}

def start_files(repo: Path):
    base=repo/HOST_DIR_REL
    if not base.exists():
        raise RuntimeError(f"missing startscreen directory: {HOST_DIR_REL}")
    return sorted(
        p for p in base.rglob("*")
        if p.is_file() and p.suffix.lower() in TEXT_EXTS
    )

def patch_text(text: str):
    out=text
    count=0

    for old,new in (
        ("START v3.0.2","START v4.41"),
        ("START v3.0","START v4.41"),
    ):
        n=out.count(old)
        if n:
            out=out.replace(old,new)
            count+=n

    key_colon=re.compile(
        r'(?P<prefix>["\'](?:start_version|startVersion|official_start_version|officialStartVersion)["\']\s*:\s*["\'])'
        r'v?3\.0\.2'
        r'(?P<suffix>["\'])'
    )
    out,n=key_colon.subn(lambda m:m.group("prefix")+"v4.41"+m.group("suffix"),out)
    count+=n

    key_assign=re.compile(
        r'(?P<prefix>\b(?:start_version|startVersion|official_start_version|officialStartVersion)\s*=\s*["\'])'
        r'v?3\.0\.2'
        r'(?P<suffix>["\'])'
    )
    out,n=key_assign.subn(lambda m:m.group("prefix")+"v4.41"+m.group("suffix"),out)
    count+=n

    return out,count

def synchronize(repo: Path, report: Path):
    changed=[]
    entries=[]
    total=0

    for p in start_files(repo):
        rel=p.relative_to(repo).as_posix()
        original=p.read_text(encoding="utf-8-sig")
        patched,n=patch_text(original)
        if n:
            p.write_text(patched,encoding="utf-8",newline="\n")
            changed.append(rel)
            total+=n
        entries.append({"path":rel,"replacements":n})

    host=repo/HOST_REL
    html=host.read_text(encoding="utf-8")
    html,n=re.subn(
        r'(phoenix_detv_cad_bridge\.js)(?:\?[^"\']*)?',
        r'\1?v=4.41-runtime-cors-v1',
        html,
        count=1,
        flags=re.I,
    )
    if n!=1:
        raise RuntimeError("expected exactly one CAD bridge script reference")
    host.write_text(html,encoding="utf-8",newline="\n")
    if HOST_REL not in changed:
        changed.append(HOST_REL)

    result={
        "status":"PASS",
        "replacement_count":total,
        "changed_files":sorted(set(changed)),
        "files":entries,
    }
    report.write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

def verify(repo: Path, bridge: Path, report: Path):
    stale=[]
    for p in start_files(repo):
        if "START v3.0.2" in p.read_text(encoding="utf-8-sig"):
            stale.append(p.relative_to(repo).as_posix())

    host=(repo/HOST_REL).read_text(encoding="utf-8")
    if "phoenix_detv_cad_bridge.js?v=4.41-runtime-cors-v1" not in host:
        raise RuntimeError("new CAD bridge cache key missing")

    js=bridge.read_text(encoding="utf-8")
    required=[
        "syncRuntimeVersionText",
        "START v4.41",
        'mode:"cors"',
        "CAD sidecar browser health failed",
    ]
    missing=[x for x in required if x not in js]
    if stale or missing:
        raise RuntimeError(f"runtime sync verify failed: stale={stale}; missing={missing}")

    data=json.loads(report.read_text(encoding="utf-8"))
    return {
        "status":"PASS",
        "replacement_count":data["replacement_count"],
        "stale_exact_literals":stale,
    }

def self_test():
    out,n=patch_text("v1.8.7 · START v3.0.2")
    assert n==1
    assert out=="v1.8.7 · START v4.41"

    out,n=patch_text('{"startVersion":"v3.0.2"}')
    assert n==1
    assert out=='{"startVersion":"v4.41"}'

    out,n=patch_text("RUNTIME v1.8.7")
    assert n==0
    assert out=="RUNTIME v1.8.7"

    print("PHOENIX_4_41_START_RUNTIME_SYNC_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path)
    ap.add_argument("--bridge",type=Path)
    ap.add_argument("--report",type=Path)
    ap.add_argument("--sync",action="store_true")
    ap.add_argument("--verify",action="store_true")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()

    if a.self_test:
        self_test()
        return 0

    if not a.repo_root:
        ap.error("--repo-root required")
    repo=a.repo_root.resolve()

    if a.sync:
        if not a.report: ap.error("--report required")
        print(json.dumps(synchronize(repo,a.report),indent=2))
        print("START_RUNTIME_VERSION_SYNC=PASS")
        return 0

    if a.verify:
        if not a.report or not a.bridge: ap.error("--report and --bridge required")
        print(json.dumps(verify(repo,a.bridge,a.report),indent=2))
        print("START_RUNTIME_VERSION_VERIFY=PASS")
        return 0

    ap.error("choose --sync, --verify or --self-test")

if __name__=="__main__":
    raise SystemExit(main())
