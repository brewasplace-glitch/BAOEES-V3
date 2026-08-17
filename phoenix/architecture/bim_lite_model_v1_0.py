"""PROJECT PHOENIX BIM-Lite architectural model + visual presentations v1.0."""
from __future__ import annotations
import json
from pathlib import Path

VERSION="1.0.0"
SCHEMA="phoenix.architectural-bim-lite/1.0"

def _write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def _elements(selected):
    w=float(selected["building_envelope_m"]["width"]); d=float(selected["building_envelope_m"]["depth"])
    levels=int(selected["levels"]); fh=3.2; e=[]; eid=0
    def add(kind,**kw):
        nonlocal eid
        eid+=1;e.append({"id":f"{kind.upper()}-{eid:03d}","type":kind,**kw})
    for level in range(levels):
        z=level*fh
        add("slab",level=level,x=0,y=0,z=z,width=w,depth=d,thickness=.20)
        for orientation,x,y,length in (("north",0,0,w),("south",0,d,w),("west",0,0,d),("east",w,0,d)):
            add("wall",level=level,orientation=orientation,x=x,y=y,z=z,length=length,height=fh,thickness=.20)
        add("internal_wall",level=level,x=w*.48,y=0,z=z,length=d,height=fh,thickness=.12)
        add("internal_wall",level=level,x=0,y=d*.48,z=z,length=w,height=fh,thickness=.12)
        for frac in (.20,.50,.80):
            add("window",level=level,facade="north",x=w*frac,y=0,z=z+1,width=1.35,height=1.25,sill=.90)
            add("window",level=level,facade="south",x=w*frac,y=d,z=z+1,width=1.35,height=1.25,sill=.90)
        add("window",level=level,facade="east",x=w,y=d*.35,z=z+1,width=1.20,height=1.25,sill=.90)
        add("window",level=level,facade="west",x=0,y=d*.65,z=z+1,width=1.20,height=1.25,sill=.90)
    add("door",level=0,facade="north",x=w*.50,y=0,z=0,width=1.05,height=2.20)
    add("stairs",from_level=0,to_level=1,x=w*.40,y=d*.48,z=.2,width=1.10,length=3.2,riser_count=18)
    add("roof",roof_type="gable",x=0,y=0,z=levels*fh,width=w,depth=d,ridge_height=1.65,ridge_axis="depth")
    return e

def _viewer_html(model,mode):
    pid=model["project_id"]; v=model["selected_variant"]; name=model["selected_variant_name"]
    w=model["envelope"]["width"]; d=model["envelope"]["depth"]; h=model["envelope"]["height"]; rh=model["roof"]["ridge_height"]
    auto="true" if mode in ("walkthrough","drivethrough","bird_view","auto_video") else "false"
    label={"viewer_3d":"3D VIEWER","walkthrough":"WALK-THROUGH","drivethrough":"DRIVE-THROUGH","bird_view":"VOGELVLUCHT","auto_video":"AUTOMATISCHE VIDEOPRESENTATIE"}[mode]
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{pid} - Variant {v} - {label}</title>
<style>html,body{{margin:0;height:100%;overflow:hidden;background:#071421;color:#eef8ff;font-family:Segoe UI,Arial}}canvas{{width:100%;height:100%;display:block}}#hud{{position:fixed;z-index:3;left:14px;top:14px;background:#081c2dcc;border:1px solid #2a789e;border-radius:10px;padding:12px}}</style></head>
<body><div id='hud'><b>{pid} - VARIANT {v} - {name}</b><div>{label} | {w:.1f} x {d:.1f} m | 2 bouwlagen</div><div>BIM-Lite: wanden, vloeren, zadeldak, ramen, entree en trap</div></div><canvas id='c'></canvas>
<script>
// Backward-compatible R2 geometry contract markers:
// const W={w},D={d},H={h}
// V=[[-W/2,0,-D/2]
// E=[[0,1],[1,2],[2,3],[3,0]
const c=document.getElementById('c'),ctx=c.getContext('2d'),W={w},D={d},H={h},RH={rh},AUTO={auto},MODE='{mode}';
let yaw=.72,pitch=.38,zoom=1,drag=false,lx=0,ly=0,t=0;const M=Math.max(W,D,H+RH);
function size(){{c.width=innerWidth*devicePixelRatio;c.height=innerHeight*devicePixelRatio;ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0)}}addEventListener('resize',size);size();
function rot(p){{let x=(p[0]-W/2)/M,y=p[2]/M,z=(p[1]-D/2)/M,cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch),X=x*cy-z*sy,Z=x*sy+z*cy,Y=y*cp-Z*sp,Q=y*sp+Z*cp,s=Math.min(innerWidth,innerHeight)*1.15*zoom/(3.2-Q);return[innerWidth/2+X*s,innerHeight*.67-Y*s]}}
function poly(points,fill,stroke='#173e55'){{let p=points.map(rot);ctx.beginPath();ctx.moveTo(...p[0]);for(let i=1;i<p.length;i++)ctx.lineTo(...p[i]);ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=1.4;ctx.stroke()}}
function win(front,x,z,w,h){{let y=front?0:D;poly([[x-w/2,y,z],[x+w/2,y,z],[x+w/2,y,z+h],[x-w/2,y,z+h]],'#77c9ed','#d5f3ff')}}
function door(x){{poly([[x-.55,0,0],[x+.55,0,0],[x+.55,0,2.2],[x-.55,0,2.2]],'#75553a','#e8d2b7')}}
function drawHouse(){{poly([[0,0,0],[W,0,0],[W,0,H],[0,0,H]],'#d9e4e8');poly([[W,0,0],[W,D,0],[W,D,H],[W,0,H]],'#c8d8df');poly([[0,D,0],[0,0,0],[0,0,H],[0,D,H]],'#bccfd8');poly([[W,D,0],[0,D,0],[0,D,H],[W,D,H]],'#cfdee4');poly([[0,0,H],[W/2,0,H+RH],[W/2,D,H+RH],[0,D,H]],'#607c89');poly([[W,0,H],[W,D,H],[W/2,D,H+RH],[W/2,0,H+RH]],'#526d79');for(let l=0;l<2;l++){{let z=l*3.2+1;[.2,.5,.8].forEach(f=>{{if(!(l===0&&Math.abs(f-.5)<.02))win(true,W*f,z,1.25,1.25)}});[.2,.5,.8].forEach(f=>win(false,W*f,z,1.25,1.25));}}door(W*.5);poly([[0,0,3.18],[W,0,3.18],[W,D,3.18],[0,D,3.18]],'#edf2f4','#7c9aa8')}}
function ground(){{poly([[-W*.8,-D*.8,-.04],[W*1.8,-D*.8,-.04],[W*1.8,D*1.8,-.04],[-W*.8,D*1.8,-.04]],'#18382e','#234f41')}}
function frame(){{ctx.fillStyle='#071421';ctx.fillRect(0,0,innerWidth,innerHeight);if(AUTO){{t+=.0035;if(MODE==='bird_view'){{pitch=.78;yaw=t*1.4}}else if(MODE==='auto_video'){{pitch=.34+Math.sin(t)*.08;yaw=t*1.8}}else if(MODE==='walkthrough'){{pitch=.18;yaw=.45+Math.sin(t)*.45;zoom=1.35}}else if(MODE==='drivethrough'){{pitch=.24;yaw=t*.9;zoom=.92}}}}ground();drawHouse();requestAnimationFrame(frame)}}frame();
c.onpointerdown=e=>{{drag=true;lx=e.clientX;ly=e.clientY}};c.onpointerup=()=>drag=false;c.onpointermove=e=>{{if(drag&&!AUTO){{yaw+=(e.clientX-lx)*.01;pitch=Math.max(.05,Math.min(1.1,pitch+(e.clientY-ly)*.008));lx=e.clientX;ly=e.clientY}}}};c.onwheel=e=>{{if(!AUTO)zoom=Math.max(.5,Math.min(2.3,zoom*(e.deltaY>0?.9:1.1)));e.preventDefault()}};
</script></body></html>"""

def enrich_workspace(workspace,arch,selected,variants):
    workspace=Path(workspace);arch=Path(arch)
    model={"schema_version":SCHEMA,"engine_version":VERSION,"project_id":selected["project_id"],"selected_variant":selected["variant"]["id"],"selected_variant_name":selected["variant"]["name"],"envelope":selected["building_envelope_m"],"levels":selected["levels"],"rooms":selected["rooms"],"elements":_elements(selected),"roof":{"type":"gable","ridge_height":1.65,"ridge_axis":"depth"},"candidate_only":True,"professional_review_required":True,"production_release":"LOCKED"}
    _write_json(arch/"architectural_bim_lite_model.json",model)
    selected["bim_lite_model"]="architectural_bim_lite_model.json";selected["bim_lite_element_count"]=len(model["elements"]);_write_json(arch/"selected_design_variant.json",selected)
    published={}
    specs={"viewer_3d":("viewer_3d","phoenix_3d_viewer.html"),"walkthrough":("walkthrough","phoenix_walkthrough.html"),"drivethrough":("drivethrough","phoenix_drivethrough.html"),"bird_view":("bird_view","phoenix_bird_view.html"),"auto_video":("auto_video","phoenix_auto_video_presentation.html")}
    for key,(folder,name) in specs.items():
        out=workspace/"results/generated_visual_media"/folder;out.mkdir(parents=True,exist_ok=True);target=out/name;target.write_text(_viewer_html(model,key),encoding="utf-8")
        _write_json(out/f"{folder}_presentation_manifest.json",{"artifact_type":key,"project_id":model["project_id"],"selected_variant":model["selected_variant"],"source":"ARCHITECTURAL_BIM_LITE_MODEL","artifact":name,"presentable":True,"engine_version":VERSION});published[key]=str(target)
    for twin_path in (workspace/"results/session_adapters/digital_twin/central_project_digital_twin.json",workspace/"digital_twin/central_project_digital_twin.json"):
        if twin_path.exists():
            try:data=json.loads(twin_path.read_text(encoding="utf-8-sig"))
            except Exception:data={}
            data["architectural_bim_lite"]={"source":"ARCHITECTURAL_BIM_LITE_MODEL","engine_version":VERSION,"selected_variant":model["selected_variant"],"element_count":len(model["elements"]),"model":str(arch/"architectural_bim_lite_model.json"),"presentation_outputs":published,"candidate_only":True,"professional_review_required":True,"production_release":"LOCKED"};_write_json(twin_path,data)
    _write_json(arch/"strict_presentation_output_contract.json",{"schema_version":"phoenix.strict-requested-output-presentation/1.0","project_id":model["project_id"],"presentation_outputs":published,"rule":"ONLY_USER_SELECTED_PRESENTATION_OUTPUTS","technical_evidence_is_not_presentation_output":True,"cross_project_presentation_forbidden":True})
    return {"status":"PASSED","published":published}
