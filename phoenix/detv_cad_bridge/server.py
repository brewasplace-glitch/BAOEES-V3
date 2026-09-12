#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, re, secrets, shutil, subprocess, sys, tempfile, threading, traceback, urllib.parse, uuid, xml.etree.ElementTree as ET
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION="1.2.0"; DEFAULT_PORT=8765; MAX_UPLOAD=100*1024*1024; ALLOWED={".dxf",".dwg"}
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
    try:
        return ezdxf.readfile(path),"STRICT",[]
    except Exception as strict_error:
        from ezdxf import recover
        try:
            doc,aud=recover.readfile(path)
            return doc,"RECOVER",[str(x) for x in getattr(aud,"errors",[])[:50]]
        except Exception as recover_error:
            raise RuntimeError(
                f"DXF_PARSE_FAILED_STRICT_AND_RECOVER: strict={strict_error}; recover={recover_error}"
            ) from recover_error

def entity_inventory(doc):
    counts={}
    for entity in doc.modelspace():
        t=entity.dxftype()
        counts[t]=counts.get(t,0)+1
    return dict(sorted(counts.items()))

def _layer_names(doc):
    return [str(x.dxf.name) for x in doc.layers]

def _selected_filter(selected):
    selected=set(selected or [])
    if not selected:
        return None
    def filt(entity):
        try:
            return str(entity.dxf.layer) in selected
        except Exception:
            return True
    return filt

def _safe_frontend_draw(frontend,ctx,msp,filter_func=None):
    skipped=[]
    ctx.set_current_layout(msp)
    frontend.set_background(ctx.current_layout_properties.background_color)
    frontend.parent_stack=[]
    for entity in msp:
        if filter_func is not None:
            try:
                if not filter_func(entity):
                    continue
            except Exception:
                pass
        try:
            frontend.draw_entities([entity])
        except Exception as exc:
            skipped.append({
                "type":entity.dxftype(),
                "handle":str(getattr(entity.dxf,"handle","") or ""),
                "layer":str(getattr(entity.dxf,"layer","") or ""),
                "error":f"{type(exc).__name__}: {exc}",
            })
    frontend.pipeline.finalize()
    return skipped

def render_svg_resilient(path,layers=None):
    from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout
    from ezdxf.addons.drawing.config import Configuration,BackgroundPolicy
    doc,mode,errs=read_doc(path)
    msp=doc.modelspace()
    names=_layer_names(doc)
    filt=_selected_filter(layers)
    attempts=[]

    # Attempt A: official SVGBackend API from ezdxf documentation.
    try:
        ctx=RenderContext(doc)
        backend=svg.SVGBackend()
        frontend=Frontend(
            ctx,
            backend,
            config=Configuration(background_policy=BackgroundPolicy.WHITE),
        )
        skipped=_safe_frontend_draw(frontend,ctx,msp,filt)
        page=layout.Page(1400,900,units=layout.Units.px)
        svg_text=backend.get_string(
            page,
            settings=layout.Settings(fit_page=True,output_layers=False),
        )
        if "<svg" not in svg_text:
            raise RuntimeError("SVGBackend produced no SVG root")
        return {
            "svg":svg_text,
            "layers":names,
            "read_mode":mode,
            "recovery_errors":errs,
            "dxfversion":str(doc.dxfversion),
            "renderer":"EZDXF_SVGBACKEND_SAFE",
            "skipped_entities":skipped,
            "primary_attempts":attempts,
            "inventory":entity_inventory(doc),
        }
    except Exception as exc:
        attempts.append({
            "renderer":"EZDXF_SVGBACKEND_SAFE",
            "error":f"{type(exc).__name__}: {exc}",
            "traceback":traceback.format_exc(limit=20),
        })

    # Attempt B: legacy SVGRenderBackend used by Phoenix before this repair.
    try:
        ctx=RenderContext(doc)
        page=layout.Page(1400,900,units=layout.Units.px)
        backend=svg.SVGRenderBackend(
            page,
            layout.Settings(fit_page=True,output_layers=False),
        )
        frontend=Frontend(
            ctx,
            backend,
            config=Configuration(background_policy=BackgroundPolicy.WHITE),
        )
        skipped=_safe_frontend_draw(frontend,ctx,msp,filt)
        svg_text=ET.tostring(
            backend.get_xml_root_element(),
            encoding="unicode",
        )
        if "<svg" not in svg_text:
            raise RuntimeError("SVGRenderBackend produced no SVG root")
        return {
            "svg":svg_text,
            "layers":names,
            "read_mode":mode,
            "recovery_errors":errs,
            "dxfversion":str(doc.dxfversion),
            "renderer":"EZDXF_SVGRENDERBACKEND_SAFE",
            "skipped_entities":skipped,
            "primary_attempts":attempts,
            "inventory":entity_inventory(doc),
        }
    except Exception as exc:
        attempts.append({
            "renderer":"EZDXF_SVGRENDERBACKEND_SAFE",
            "error":f"{type(exc).__name__}: {exc}",
            "traceback":traceback.format_exc(limit=20),
        })

    raise RuntimeError(json.dumps({
        "status":"FAILED_EZDXF_SVG_RENDER",
        "attempts":attempts,
        "inventory":entity_inventory(doc),
        "read_mode":mode,
        "recovery_errors":errs,
        "dxfversion":str(doc.dxfversion),
    },ensure_ascii=False))

def _aci_color(index):
    palette={
        1:"#ff3b30",2:"#ffd60a",3:"#32d74b",4:"#64d2ff",
        5:"#0a84ff",6:"#bf5af2",7:"#f5f5f5",8:"#9d9d9d",9:"#d1d1d6"
    }
    try:
        i=abs(int(index))
    except Exception:
        i=7
    return palette.get(i,"#e7eef7")

def _entity_color(entity):
    try:
        rgb=entity.rgb
        if rgb:
            return "#{:02x}{:02x}{:02x}".format(*rgb)
    except Exception:
        pass
    try:
        return _aci_color(entity.dxf.color)
    except Exception:
        return "#e7eef7"

def _layer_of(entity):
    try:
        return str(entity.dxf.layer)
    except Exception:
        return "0"

def _point(v):
    return [float(v[0]),float(v[1])]

def _add_bounds(bounds,x,y):
    if math.isfinite(x) and math.isfinite(y):
        bounds[0]=min(bounds[0],x);bounds[1]=min(bounds[1],y)
        bounds[2]=max(bounds[2],x);bounds[3]=max(bounds[3],y)

def _append_line(out,bounds,a,b,entity):
    a=_point(a);b=_point(b)
    _add_bounds(bounds,*a);_add_bounds(bounds,*b)
    out.append({"type":"line","a":a,"b":b,"layer":_layer_of(entity),"color":_entity_color(entity)})

def _primitive_entity(entity,out,bounds,skipped,depth=0):
    if depth>4:
        skipped.append({"type":entity.dxftype(),"reason":"max virtual entity depth"})
        return
    t=entity.dxftype()
    layer=_layer_of(entity); color=_entity_color(entity)
    try:
        if t=="LINE":
            _append_line(out,bounds,entity.dxf.start,entity.dxf.end,entity);return
        if t=="CIRCLE":
            c=_point(entity.dxf.center);r=float(entity.dxf.radius)
            _add_bounds(bounds,c[0]-r,c[1]-r);_add_bounds(bounds,c[0]+r,c[1]+r)
            out.append({"type":"circle","c":c,"r":r,"layer":layer,"color":color});return
        if t=="ARC":
            c=_point(entity.dxf.center);r=float(entity.dxf.radius)
            _add_bounds(bounds,c[0]-r,c[1]-r);_add_bounds(bounds,c[0]+r,c[1]+r)
            out.append({
                "type":"arc","c":c,"r":r,
                "start":float(entity.dxf.start_angle),
                "end":float(entity.dxf.end_angle),
                "layer":layer,"color":color,
            });return
        if t=="LWPOLYLINE":
            pts=[[float(x),float(y)] for x,y,*_ in entity.get_points("xy")]
            for x,y in pts:_add_bounds(bounds,x,y)
            if len(pts)>=2:
                out.append({"type":"polyline","pts":pts,"closed":bool(entity.closed),"layer":layer,"color":color})
            return
        if t=="POLYLINE":
            pts=[_point(v.dxf.location) for v in entity.vertices]
            for x,y in pts:_add_bounds(bounds,x,y)
            if len(pts)>=2:
                out.append({"type":"polyline","pts":pts,"closed":bool(entity.is_closed),"layer":layer,"color":color})
            return
        if t=="POINT":
            p=_point(entity.dxf.location);_add_bounds(bounds,*p)
            out.append({"type":"point","p":p,"layer":layer,"color":color});return
        if t=="TEXT":
            p=_point(entity.dxf.insert);_add_bounds(bounds,*p)
            out.append({
                "type":"text","p":p,"text":str(entity.dxf.text),
                "height":float(getattr(entity.dxf,"height",1.0) or 1.0),
                "rotation":float(getattr(entity.dxf,"rotation",0.0) or 0.0),
                "layer":layer,"color":color,
            });return
        if t=="MTEXT":
            p=_point(entity.dxf.insert);_add_bounds(bounds,*p)
            try:text=entity.plain_text()
            except Exception:text=str(getattr(entity,"text",""))
            out.append({
                "type":"text","p":p,"text":text,
                "height":float(getattr(entity.dxf,"char_height",1.0) or 1.0),
                "rotation":float(getattr(entity.dxf,"rotation",0.0) or 0.0),
                "layer":layer,"color":color,
            });return
        if t in {"SOLID","TRACE","3DFACE"}:
            pts=[]
            for attr in ("vtx0","vtx1","vtx2","vtx3"):
                if hasattr(entity.dxf,attr):
                    pts.append(_point(getattr(entity.dxf,attr)))
            for x,y in pts:_add_bounds(bounds,x,y)
            if len(pts)>=3:
                out.append({"type":"polygon","pts":pts,"layer":layer,"color":color})
            return
        if t in {"INSERT","DIMENSION","LEADER","MLEADER","MULTILEADER"}:
            try:
                children=list(entity.virtual_entities())
            except Exception as exc:
                skipped.append({"type":t,"layer":layer,"reason":f"virtual_entities: {type(exc).__name__}: {exc}"})
                return
            for child in children:
                _primitive_entity(child,out,bounds,skipped,depth+1)
            return
        if t in {"ELLIPSE","SPLINE"}:
            try:
                from ezdxf.path import make_path
                pts=[_point(p) for p in make_path(entity).flattening(0.25)]
                for x,y in pts:_add_bounds(bounds,x,y)
                if len(pts)>=2:
                    out.append({"type":"polyline","pts":pts,"closed":False,"layer":layer,"color":color})
                return
            except Exception as exc:
                skipped.append({"type":t,"layer":layer,"reason":f"path flatten: {type(exc).__name__}: {exc}"})
                return
        skipped.append({"type":t,"layer":layer,"reason":"unsupported primitive fallback entity"})
    except Exception as exc:
        skipped.append({"type":t,"layer":layer,"reason":f"{type(exc).__name__}: {exc}"})

def extract_browser_primitives(path,layers=None):
    doc,mode,errs=read_doc(path)
    selected=set(layers or [])
    out=[]; skipped=[]; bounds=[math.inf,math.inf,-math.inf,-math.inf]
    for entity in doc.modelspace():
        if selected:
            try:
                if str(entity.dxf.layer) not in selected:
                    continue
            except Exception:
                pass
        _primitive_entity(entity,out,bounds,skipped)
    valid=all(math.isfinite(x) for x in bounds) and bounds[2]>=bounds[0] and bounds[3]>=bounds[1]
    if not valid:
        bounds=[0.0,0.0,1.0,1.0]
    return {
        "browser_primitives":out,
        "primitive_bounds":bounds,
        "primitive_skipped":skipped,
        "layers":_layer_names(doc),
        "read_mode":mode,
        "recovery_errors":errs,
        "dxfversion":str(doc.dxfversion),
        "inventory":entity_inventory(doc),
        "renderer":"PHOENIX_BROWSER_PRIMITIVE_CANVAS",
    }

def write_render_diagnostics(session,src,payload):
    data={
        "schema":"PHOENIX_CAD_RENDER_DIAGNOSTICS_1.0",
        "source":str(src),
        "result":payload,
    }
    p=session/"render_diagnostics.json"
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    return p

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
    if ext not in ALLOWED:
        raise RuntimeError("Only DXF/DWG supported")

    render=src
    conversion="NOT_REQUIRED"
    if ext==".dwg":
        render=session/f"{src.stem}_libredwg.dxf"
        convert_dwg(src,render,rt)
        conversion="PASS"

    primary_error=None
    primary_detail=None
    try:
        r=render_svg_resilient(render)
        payload={
            "source":src,
            "render_source":render,
            "source_format":ext[1:].upper(),
            "conversion_status":conversion,
            "embedded_status":"PASS",
            "error":None,
            "primary_error":None,
            "fallback_used":False,
            **r,
        }
        diag=write_render_diagnostics(session,src,{
            "embedded_status":"PASS",
            "renderer":r.get("renderer"),
            "inventory":r.get("inventory"),
            "skipped_entities":r.get("skipped_entities"),
            "primary_attempts":r.get("primary_attempts"),
        })
        payload["diagnostics_file"]=str(diag)
        return payload
    except Exception as exc:
        primary_error=f"{type(exc).__name__}: {exc}"
        try:
            primary_detail=json.loads(str(exc))
        except Exception:
            primary_detail={"error":str(exc)}

    try:
        fallback=extract_browser_primitives(render)
        if not fallback["browser_primitives"]:
            raise RuntimeError("primitive fallback produced zero drawable primitives")
        status="PASS_BROWSER_PRIMITIVE_FALLBACK"
        payload={
            "source":src,
            "render_source":render,
            "source_format":ext[1:].upper(),
            "conversion_status":conversion,
            "embedded_status":status,
            "error":None,
            "primary_error":primary_error,
            "primary_detail":primary_detail,
            "fallback_used":True,
            "svg":"",
            **fallback,
        }
        diag=write_render_diagnostics(session,src,{
            "embedded_status":status,
            "primary_error":primary_error,
            "primary_detail":primary_detail,
            "primitive_count":len(fallback["browser_primitives"]),
            "primitive_skipped":fallback["primitive_skipped"],
            "inventory":fallback["inventory"],
        })
        payload["diagnostics_file"]=str(diag)
        return payload
    except Exception as fallback_exc:
        failed_status="DEGRADED_DWG_CONVERSION_OUTPUT_UNPARSABLE" if ext==".dwg" else "FAILED_DXF_RENDER"
        payload={
            "source":src,
            "render_source":render,
            "source_format":ext[1:].upper(),
            "conversion_status":conversion,
            "embedded_status":failed_status,
            "error":f"{type(fallback_exc).__name__}: {fallback_exc}",
            "primary_error":primary_error,
            "primary_detail":primary_detail,
            "fallback_used":True,
            "svg":"",
            "browser_primitives":[],
            "primitive_bounds":[0,0,1,1],
            "primitive_skipped":[],
            "layers":[],
            "read_mode":"FAILED",
            "recovery_errors":[],
            "dxfversion":"",
            "renderer":"FAILED",
        }
        diag=write_render_diagnostics(session,src,payload)
        payload["diagnostics_file"]=str(diag)
        return payload

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
    server_version="PHOENIX-DETV-CAD/1.2"
    CORS_ALLOWED_ORIGINS={
        "http://127.0.0.1:8766",
        "http://localhost:8766",
    }
    def log_message(self,fmt,*args): pass
    @property
    def app(self): return self.server.app
    def cors_headers(self):
        origin=self.headers.get("Origin","")
        if origin in self.CORS_ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin",origin)
            self.send_header("Vary","Origin")
            self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers","Content-Type, X-Phoenix-Token")
            self.send_header("Access-Control-Max-Age","600")
    def js(self,o,status=200):
        b=json.dumps(o,ensure_ascii=False).encode()
        self.send_response(status)
        self.cors_headers()
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(b)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(b)
    def ht(self,t):
        b=t.encode()
        self.send_response(200)
        self.cors_headers()
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(b)))
        self.send_header("Cache-Control","no-store")
        self.send_header("Content-Security-Policy","frame-ancestors *")
        self.end_headers()
        self.wfile.write(b)
    def do_OPTIONS(self):
        origin=self.headers.get("Origin","")
        if origin not in self.CORS_ALLOWED_ORIGINS:
            self.send_response(403)
            self.send_header("Content-Length","0")
            self.end_headers()
            return
        self.send_response(204)
        self.cors_headers()
        self.send_header("Content-Length","0")
        self.end_headers()
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
        path=Path(rec["render_source"])
        layers=x.get("layers",[])
        try:
            r=render_svg_resilient(path,layers)
            self.js({
                "session_id":sid,
                "embedded_status":"PASS",
                "renderer":r["renderer"],
                "svg":r["svg"],
                "browser_primitives":[],
                "primitive_bounds":[0,0,1,1],
                "layers":r["layers"],
                "read_mode":r["read_mode"],
            })
        except Exception as primary:
            f=extract_browser_primitives(path,layers)
            self.js({
                "session_id":sid,
                "embedded_status":"PASS_BROWSER_PRIMITIVE_FALLBACK",
                "renderer":f["renderer"],
                "svg":"",
                "browser_primitives":f["browser_primitives"],
                "primitive_bounds":f["primitive_bounds"],
                "layers":f["layers"],
                "read_mode":f["read_mode"],
                "primary_error":str(primary),
            })
    def open_lc(self):
        sid=str(self.body_json().get("session_id",""))
        with LOCK: rec=SESSIONS.get(sid)
        if not rec: raise ValueError("Unknown CAD session")
        open_librecad(Path(rec.get("repo_source") or rec["source"]),self.app["runtime"]); self.js({"status":"PASS","action":"LIBRECAD_LAUNCHED"})

def self_test(repo):
    bootstrap(repo); import ezdxf
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.dxf"
        doc=ezdxf.new("R2010")
        doc.layers.add("PHX_WALLS")
        msp=doc.modelspace()
        msp.add_line((0,0),(10,10),dxfattribs={"layer":"PHX_WALLS"})
        msp.add_circle((5,5),2,dxfattribs={"layer":"PHX_WALLS"})
        msp.add_text("PHOENIX",dxfattribs={"height":1.0,"layer":"PHX_WALLS"}).set_placement((1,8))
        doc.saveas(p)

        r=render_svg_resilient(p)
        assert "<svg" in r["svg"] and "PHX_WALLS" in r["layers"]

        f=extract_browser_primitives(p)
        assert len(f["browser_primitives"])>=3
        assert f["renderer"]=="PHOENIX_BROWSER_PRIMITIVE_CANVAS"

        h=viewer_page(Path(repo),"tok","file","")
        assert "Open bestand" in h and "Open in LibreCAD" in h
        assert "renderPrimitiveCanvas" in h
    print("PHOENIX_4_41_DETV_CAD_RENDER_COMPAT_SELF_TEST=PASS")

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
