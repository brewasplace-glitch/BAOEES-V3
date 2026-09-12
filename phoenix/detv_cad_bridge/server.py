#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, secrets, shutil, subprocess, sys, tempfile, threading, urllib.parse, uuid, xml.etree.ElementTree as ET
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION="1.0.0"; DEFAULT_PORT=8765; MAX_UPLOAD=100*1024*1024; ALLOWED={".dxf",".dwg"}
SESSIONS={}; LOCK=threading.Lock()

def bootstrap(repo):
    repo=Path(repo)
    if str(repo) not in sys.path: sys.path.insert(0,str(repo))
    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))
    deps=local/"PROJECT-PHOENIX"/"runtime_deps"/"cad_viewer_v1"
    if deps.exists() and str(deps) not in sys.path: sys.path.insert(0,str(deps))

def runtime_config():
    local=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))
    p=local/"PROJECT-PHOENIX"/"cad_viewer"/"cad_viewer_runtime.json"
    if not p.exists(): raise RuntimeError(f"CAD runtime missing: {p}")
    return json.loads(p.read_text(encoding="utf-8-sig"))

def safe_name(n):
    n=Path(n).name; n=re.sub(r"[^A-Za-z0-9._() -]+","_",n).strip(" .")
    return n or "drawing.dxf"

def read_doc(path):
    import ezdxf
    try: return ezdxf.readfile(path),"STRICT",[]
    except Exception as a:
        from ezdxf import recover
        try:
            doc,aud=recover.readfile(path)
            return doc,"RECOVER",[str(x) for x in getattr(aud,"errors",[])[:50]]
        except Exception as b:
            raise RuntimeError(f"DXF_PARSE_FAILED_STRICT_AND_RECOVER: strict={a}; recover={b}") from b

def render_svg(path,layers=None):
    from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout
    from ezdxf.addons.drawing.config import Configuration,BackgroundPolicy
    doc,mode,errs=read_doc(path); msp=doc.modelspace()
    names=[str(x.dxf.name) for x in doc.layers]; selected=set(layers or [])
    filt=None
    if selected:
        def filt(e):
            try: return str(e.dxf.layer) in selected
            except Exception: return True
    ctx=RenderContext(doc); page=layout.Page(1400,900,units=layout.Units.px)
    backend=svg.SVGRenderBackend(page,layout.Settings(fit_page=True,output_layers=False))
    Frontend(ctx,backend,config=Configuration(background_policy=BackgroundPolicy.WHITE)).draw_layout(msp,filter_func=filt)
    return {"svg":ET.tostring(backend.get_xml_root_element(),encoding="unicode"),"layers":names,"read_mode":mode,"recovery_errors":errs,"dxfversion":str(doc.dxfversion)}

def convert_dwg(src,dst,rt):
    exe=Path(rt["libredwg_dwg2dxf_exe"]); p=subprocess.run([str(exe),"-y","-o",str(dst),str(src)],capture_output=True,text=True)
    if p.returncode!=0 or not dst.exists(): raise RuntimeError("LibreDWG conversion failed: "+(p.stderr or p.stdout or str(p.returncode)))
    return dst

def open_librecad(src,rt):
    exe=Path(rt["librecad_exe"])
    if not exe.exists(): raise RuntimeError("LibreCAD executable missing")
    subprocess.Popen([str(exe),str(src)],close_fds=True)

def process_source(src,session,rt):
    ext=src.suffix.lower()
    if ext not in ALLOWED: raise RuntimeError("Only DXF/DWG supported")
    render=src; conversion="NOT_REQUIRED"
    if ext==".dwg":
        render=session/f"{src.stem}_libredwg.dxf"; convert_dwg(src,render,rt); conversion="PASS"
    try:
        r=render_svg(render); embedded="PASS"; err=None
    except Exception as e:
        r={"svg":"","layers":[],"read_mode":"FAILED","recovery_errors":[],"dxfversion":""}
        embedded="DEGRADED_DWG_CONVERSION_OUTPUT_UNPARSABLE" if ext==".dwg" else "FAILED_DXF_RENDER"; err=str(e)
    return {"source":src,"render_source":render,"source_format":ext[1:].upper(),"conversion_status":conversion,"embedded_status":embedded,"error":err,**r}

def project_context(repo,hint=""):
    if hint.strip(): return {"status":"HINT_FROM_DE_TV","tokens":[hint.strip()],"sources":["DE_TV_RUNTIME_HINT"]}
    candidates=[repo/"outputs/runtime/active_project_context.json",repo/"outputs/runtime/active_project.json",repo/"runtime/active_project_context.json",repo/"runtime/active_project.json",repo/"configs/phoenix/active_project_context.json",repo/"configs/phoenix/active_project.json"]
    vals=[]; sources=[]
    keys={"project_id","projectid","project_name","projectname","project_slug","slug","active_project","current_project"}
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if str(k).lower() in keys and isinstance(v,(str,int)) and 2<=len(str(v).strip())<=160: vals.append(str(v).strip())
                walk(v)
        elif isinstance(x,list):
            for v in x[:100]: walk(v)
    for p in candidates:
        if p.exists():
            try:
                walk(json.loads(p.read_text(encoding="utf-8-sig"))); sources.append(str(p.relative_to(repo)))
            except Exception: pass
    dedup=[]
    for v in vals:
        if v not in dedup: dedup.append(v)
    return {"status":"AUTHORITATIVE_CONTEXT_FOUND" if dedup else "NO_AUTHORITATIVE_ACTIVE_PROJECT_CONTEXT","tokens":dedup,"sources":sources}

def scan_project(repo,hint=""):
    ctx=project_context(repo,hint); toks=[x.lower() for x in ctx["tokens"]]; matches=[]; fallback=[]
    for base in [repo/"outputs",repo/"projects",repo/"configs/projects",repo/"apps"]:
        if not base.exists(): continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in ALLOWED: continue
            rel=p.relative_to(repo).as_posix(); item={"path":rel,"name":p.name,"mtime":p.stat().st_mtime,"size":p.stat().st_size}; fallback.append(item)
            if toks and any(t in rel.lower() for t in toks): matches.append(item)
    k=lambda x:(-x["mtime"],x["path"]); matches.sort(key=k); fallback.sort(key=k)
    files=matches[:100] if toks else fallback[:30]
    return {"context":ctx,"routing":"PROJECT_SCOPED_MATCHES" if toks else "UNSCOPED_RECENT_CANDIDATES_REQUIRES_USER_SELECTION","files":files,"quality_gate":"PASS_PROJECT_SCOPED" if toks and files else "HOLD_NO_CONFIRMED_PROJECT_MATCH"}

def viewer_page(repo,token,mode,hint):
    p=repo/"phoenix/detv_cad_bridge/assets/viewer.html"
    t=p.read_text(encoding="utf-8")
    return t.replace("__TOKEN_JSON__",json.dumps(token)).replace("__MODE_JSON__",json.dumps(mode)).replace("__HINT_JSON__",json.dumps(hint))

class H(BaseHTTPRequestHandler):
    server_version="PHOENIX-DETV-CAD/1.0"
    def log_message(self,fmt,*args): pass
    @property
    def app(self): return self.server.app
    def js(self,o,status=200):
        b=json.dumps(o,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
    def ht(self,t):
        b=t.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.send_header("Cache-Control","no-store"); self.send_header("Content-Security-Policy","frame-ancestors *"); self.end_headers(); self.wfile.write(b)
    def token(self): return secrets.compare_digest(self.headers.get("X-Phoenix-Token",""),self.app["token"])
    def need(self):
        if self.token(): return True
        self.js({"error":"Invalid PHOENIX CAD session token"},403); return False
    def body_json(self):
        n=int(self.headers.get("Content-Length","0") or 0)
        if n<=0 or n>2_000_000: raise ValueError("Invalid JSON payload")
        return json.loads(self.rfile.read(n).decode())
    def do_GET(self):
        u=urllib.parse.urlparse(self.path)
        if u.path=="/health": self.js({"status":"PASS","service":"PHOENIX_DETV_CAD_SIDECAR","version":VERSION,"pid":os.getpid()}); return
        if u.path=="/viewer":
            q=urllib.parse.parse_qs(u.query); self.ht(viewer_page(self.app["repo"],self.app["token"],q.get("mode",["file"])[0],q.get("project_hint",[""])[0])); return
        if u.path=="/api/project-files":
            if not self.need(): return
            q=urllib.parse.parse_qs(u.query); self.js(scan_project(self.app["repo"],q.get("project_hint",[""])[0])); return
        self.js({"error":"Not found"},404)
    def do_POST(self):
        if not self.need(): return
        try:
            p=urllib.parse.urlparse(self.path).path
            if p=="/api/upload": self.upload()
            elif p=="/api/open-project": self.open_project()
            elif p=="/api/rerender": self.rerender()
            elif p=="/api/open-librecad": self.open_lc()
            else: self.js({"error":"Not found"},404)
        except Exception as e: self.js({"error":str(e)},500)
    def upload(self):
        n=int(self.headers.get("Content-Length","0") or 0); ct=self.headers.get("Content-Type","")
        if n<=0 or n>MAX_UPLOAD: raise ValueError("CAD upload empty or exceeds 100 MB")
        if "multipart/form-data" not in ct: raise ValueError("multipart/form-data required")
        body=self.rfile.read(n); msg=BytesParser(policy=policy.default).parsebytes((f"Content-Type: {ct}\r\nMIME-Version: 1.0\r\n\r\n").encode()+body)
        name=None; data=None
        for part in msg.iter_parts():
            if part.get_param("name",header="content-disposition")=="file": name=part.get_filename(); data=part.get_payload(decode=True); break
        if not name or data is None: raise ValueError("No CAD file received")
        name=safe_name(name)
        if Path(name).suffix.lower() not in ALLOWED: raise ValueError("Only DXF/DWG allowed")
        sid=uuid.uuid4().hex; d=self.app["sessions"]/sid; d.mkdir(parents=True); src=d/name; src.write_bytes(data)
        r=process_source(src,d,self.app["runtime"]);
        with LOCK: SESSIONS[sid]={"source":str(src),"render_source":str(r["render_source"]),"name":name}
        out={k:v for k,v in r.items() if k not in {"source","render_source"}}; out.update({"session_id":sid,"name":name}); self.js(out)
    def open_project(self):
        rel=str(self.body_json().get("path","")).replace("\\","/"); target=(self.app["repo"]/rel).resolve(); repo=self.app["repo"].resolve()
        if repo not in target.parents or not target.exists() or target.suffix.lower() not in ALLOWED: raise ValueError("Invalid project CAD path")
        sid=uuid.uuid4().hex; d=self.app["sessions"]/sid; d.mkdir(parents=True); src=d/safe_name(target.name); shutil.copy2(target,src); r=process_source(src,d,self.app["runtime"])
        with LOCK: SESSIONS[sid]={"source":str(src),"render_source":str(r["render_source"]),"name":target.name,"repo_source":str(target)}
        out={k:v for k,v in r.items() if k not in {"source","render_source"}}; out.update({"session_id":sid,"name":target.name}); self.js(out)
    def rerender(self):
        x=self.body_json(); sid=str(x.get("session_id",""))
        with LOCK: rec=SESSIONS.get(sid)
        if not rec: raise ValueError("Unknown CAD session")
        r=render_svg(Path(rec["render_source"]),x.get("layers",[])); self.js({"session_id":sid,"svg":r["svg"],"layers":r["layers"],"read_mode":r["read_mode"]})
    def open_lc(self):
        sid=str(self.body_json().get("session_id",""))
        with LOCK: rec=SESSIONS.get(sid)
        if not rec: raise ValueError("Unknown CAD session")
        open_librecad(Path(rec.get("repo_source") or rec["source"]),self.app["runtime"]); self.js({"status":"PASS","action":"LIBRECAD_LAUNCHED"})

def self_test(repo):
    bootstrap(repo); import ezdxf
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.dxf"; doc=ezdxf.new("R2010"); doc.layers.add("PHX_WALLS"); doc.modelspace().add_line((0,0),(10,10),dxfattribs={"layer":"PHX_WALLS"}); doc.saveas(p)
        r=render_svg(p); assert "<svg" in r["svg"] and "PHX_WALLS" in r["layers"]
        h=viewer_page(Path(repo),"tok","file",""); assert "Open bestand" in h and "Open in LibreCAD" in h
    print("PHOENIX_4_41_DETV_CAD_SIDECAR_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",type=Path,default=Path(r"C:\PROJECT-PHOENIX")); ap.add_argument("--port",type=int,default=DEFAULT_PORT); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    repo=a.repo_root.resolve(); bootstrap(repo)
    if a.self_test: self_test(repo); return 0
    rt=runtime_config(); local=Path(os.environ.get("LOCALAPPDATA",str(Path.home()))); sessions=local/"PROJECT-PHOENIX"/"cad_viewer"/"detv_sessions"; sessions.mkdir(parents=True,exist_ok=True)
    s=ThreadingHTTPServer(("127.0.0.1",a.port),H); s.app={"repo":repo,"runtime":rt,"sessions":sessions,"token":secrets.token_urlsafe(32)}
    print(f"PHOENIX_DETV_CAD_SIDECAR=LISTENING http://127.0.0.1:{a.port}")
    try: s.serve_forever(poll_interval=.25)
    finally: s.server_close()
    return 0
if __name__=="__main__": raise SystemExit(main())
