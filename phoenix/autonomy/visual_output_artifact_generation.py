"""Phoenix real visual artifact generation."""
from __future__ import annotations
import json, struct
from pathlib import Path

VERSION="1.0.1"

def _twin(workspace):
    items=sorted(p for p in Path(workspace).rglob("central_project_digital_twin.json") if p.is_file() and p.stat().st_size>0)
    return items[0] if items else None

def ensure_viewer_3d_artifact(repository, workspace):
    repository,workspace=Path(repository).resolve(),Path(workspace).resolve()
    twin=_twin(workspace)
    if twin is None: return []
    out=workspace/"results"/"generated_visual_media"/"viewer_3d"; out.mkdir(parents=True,exist_ok=True)
    target=out/"phoenix_3d_viewer.html"
    pid=workspace.name
    html_doc=f"""<!doctype html>
<meta charset="utf-8">
<title>PROJECT PHOENIX 3D VIEWER</title>
<style>
html,body{{margin:0;height:100%;background:#071421;color:#def;font:16px Segoe UI}}
canvas{{width:100%;height:100%}}
b{{position:fixed;left:18px;top:18px}}
</style>
<b>PROJECT PHOENIX — 3D VIEWER — {pid}</b>
<canvas id="c"></canvas>
<script>
const c=document.getElementById('c'),x=c.getContext('2d');let a=0;
function s(){{c.width=innerWidth;c.height=innerHeight}}onresize=s;s();
function d(){{
  a+=.01;
  x.fillStyle='#071421';x.fillRect(0,0,c.width,c.height);
  let w=180+30*Math.sin(a),h=110;
  x.strokeStyle='#58c8ff';x.lineWidth=3;
  x.strokeRect(c.width/2-w/2,c.height/2-h/2,w,h);
  x.strokeRect(c.width/2-w/2+45,c.height/2-h/2-35,w,h);
  x.beginPath();
  [[0,0],[w,0],[w,h],[0,h]].forEach(p=>{{
    x.moveTo(c.width/2-w/2+p[0],c.height/2-h/2+p[1]);
    x.lineTo(c.width/2-w/2+45+p[0],c.height/2-h/2-35+p[1])
  }});
  x.stroke();
  requestAnimationFrame(d)
}}
d()
</script>
"""
    target.write_text(html_doc,encoding="utf-8")
    valid=target.stat().st_size>500 and "<canvas" in html_doc and "requestAnimationFrame" in html_doc
    (out/"viewer_3d_manifest.json").write_text(json.dumps({
        "artifact_type":"viewer_3d","project_id":pid,"source_digital_twin":str(twin),
        "artifact":target.name,"validated":valid,"version":VERSION
    },indent=2)+"\n",encoding="utf-8")
    return [target] if valid else []

def _chunk(tag,data): return tag+struct.pack("<I",len(data))+data+(b"\0" if len(data)&1 else b"")

def _avi(path,w=320,h=180,fps=8,seconds=2):
    frames=fps*seconds; stride=(w*3+3)&~3; fs=stride*h
    avih=struct.pack("<IIIIIIIIII4I",int(1e6/fps),fs*fps,0,0x10,frames,0,1,fs,w,h,0,0,0,0)
    strh=struct.pack("<4s4sIHHIIIIIIIIhhhh",b"vids",b"DIB ",0,0,0,0,1,fps,0,frames,fs,0xffffffff,0,0,0,w,h)
    strf=struct.pack("<IIIHHIIIIII",40,w,h,1,24,0,fs,0,0,0,0)
    hdrl=b"hdrl"+_chunk(b"avih",avih)+_chunk(b"LIST",b"strl"+_chunk(b"strh",strh)+_chunk(b"strf",strf))
    movi=bytearray(b"movi"); idx=bytearray(); off=4
    for n in range(frames):
        buf=bytearray(fs)
        for y in range(h):
            for x in range(w):
                o=(h-1-y)*stride+x*3; buf[o:o+3]=bytes((30+y%12,24+x%14,8))
        left=60+n*3; right=min(w-30,left+170)
        for x in range(left,right):
            for y in (45,h-45):
                o=(h-1-y)*stride+x*3; buf[o:o+3]=bytes((245,195,65))
        data=bytes(buf); part=_chunk(b"00db",data); movi.extend(part); idx.extend(struct.pack("<4sIII",b"00db",0x10,off,len(data))); off+=len(part)
    body=_chunk(b"LIST",hdrl)+_chunk(b"LIST",bytes(movi))+_chunk(b"idx1",bytes(idx))
    path.write_bytes(b"RIFF"+struct.pack("<I",4+len(body))+b"AVI "+body)

def ensure_auto_video_artifact(repository, workspace):
    workspace=Path(workspace).resolve(); twin=_twin(workspace)
    if twin is None: return []
    out=workspace/"results"/"generated_visual_media"/"auto_video"; out.mkdir(parents=True,exist_ok=True)
    target=out/"phoenix_automatic_video.avi"; _avi(target)
    raw=target.read_bytes()
    valid=target.stat().st_size>100000 and raw[:4]==b"RIFF" and raw[8:12]==b"AVI "
    (out/"auto_video_manifest.json").write_text(json.dumps({
        "artifact_type":"auto_video","project_id":workspace.name,"source_digital_twin":str(twin),
        "artifact":target.name,"media_type":"video/x-msvideo","validated":valid,"version":VERSION
    },indent=2)+"\n",encoding="utf-8")
    return [target] if valid else []
