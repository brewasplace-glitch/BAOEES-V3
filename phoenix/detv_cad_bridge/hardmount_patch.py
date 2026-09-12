#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path

HOST_REL="phoenix/local_app/static/official_start_v3_0/index.html"
BRIDGE_REL="phoenix/local_app/static/official_start_v3_0/phoenix_detv_cad_bridge.js"
VIEWER_REL="phoenix/detv_cad_bridge/assets/viewer.html"
CACHE_KEY="v4.41-detv-hardmount-v1"

def patch_host(repo:Path,report:Path):
    host=repo/HOST_REL
    text=host.read_text(encoding="utf-8-sig")
    out,n=re.subn(
        r'(phoenix_detv_cad_bridge\.js)(?:\?[^"\']*)?',
        rf'\1?{CACHE_KEY}',text,count=1,flags=re.I
    )
    if n!=1:
        raise RuntimeError("expected exactly one DE TV CAD bridge script reference")
    host.write_text(out,encoding="utf-8",newline="\n")
    data={"status":"PASS","host_rel":HOST_REL,"cache_key":CACHE_KEY,"changed_files":[HOST_REL]}
    report.write_text(json.dumps(data,indent=2),encoding="utf-8")
    return data

def verify(repo:Path,report:Path):
    host=(repo/HOST_REL).read_text(encoding="utf-8")
    bridge=(repo/BRIDGE_REL).read_text(encoding="utf-8")
    viewer=(repo/VIEWER_REL).read_text(encoding="utf-8")
    errors=[]
    if f"phoenix_detv_cad_bridge.js?{CACHE_KEY}" not in host:
        errors.append("cache key missing")
    for x in (
        "__PHOENIX_DETV_CAD_HARD_MOUNT_V1__","findDeTvViewport",
        "phoenix-cad-detv-mount","phoenix-cad-viewer-ready",
        "DETV_HARD_MOUNT_CAD_VIEWER_PROTOCOL=v1"
    ):
        if x not in bridge: errors.append("bridge marker missing: "+x)
    if "phoenix-cad-modal" in bridge: errors.append("old modal remains")
    for x in (
        "phoenix-cad-viewer-ready","phoenix-cad-file-loaded",
        "ALLOWED_PARENT_ORIGINS",'e.data.protocol==="v1"',
        'document.documentElement.classList.add("compact")'
    ):
        if x not in viewer: errors.append("viewer marker missing: "+x)
    if errors:
        raise RuntimeError("; ".join(errors))
    data=json.loads(report.read_text(encoding="utf-8"))
    return {"status":"PASS","host_rel":HOST_REL,"cache_key":data["cache_key"]}

def self_test():
    s='<script src="./phoenix_detv_cad_bridge.js?v=old"></script>'
    out,n=re.subn(
        r'(phoenix_detv_cad_bridge\.js)(?:\?[^"\']*)?',
        rf'\1?{CACHE_KEY}',s,count=1,flags=re.I
    )
    assert n==1 and CACHE_KEY in out
    print("PHOENIX_4_41_DETV_HARDMOUNT_PATCH_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path)
    ap.add_argument("--report",type=Path)
    ap.add_argument("--patch",action="store_true")
    ap.add_argument("--verify",action="store_true")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test();return 0
    if not a.repo_root: ap.error("--repo-root required")
    repo=a.repo_root.resolve()
    if a.patch:
        if not a.report: ap.error("--report required")
        print(json.dumps(patch_host(repo,a.report),indent=2))
        print("DETV_HARDMOUNT_HOST_PATCH=PASS");return 0
    if a.verify:
        if not a.report: ap.error("--report required")
        print(json.dumps(verify(repo,a.report),indent=2))
        print("DETV_HARDMOUNT_SOURCE_VERIFY=PASS");return 0
    ap.error("choose --patch, --verify or --self-test")
if __name__=="__main__":
    raise SystemExit(main())
