// PROJECT PHOENIX DE TV VISUAL-ONLY PRESENTATION + JSON SUPPRESSION v1.0
(()=>{"use strict";

const VERSION="1.0.0";
let playlist=[];
let pos=0;
let active=false;
let busy=false;

function router(){
  return window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0 || null;
}
function pid(){
  const r=router();
  return r && typeof r.authoritativeActiveProjectId==="function"
    ? r.authoritativeActiveProjectId()
    : null;
}
function strict(){
  return window.PHOENIX_STRICT_PRESENTATION_V1_0 || null;
}
function technical(path){
  const p=String(path||"").toLowerCase().replace(/\\/g,"/");
  return (
    p.endsWith(".json") ||
    p.endsWith(".txt") ||
    p.endsWith(".log") ||
    p.endsWith(".csv") ||
    p.endsWith(".xml") ||
    /(^|\/)(manifest|evidence|adapter_result|project_state|central_project_digital_twin)[^/]*\./.test(p) ||
    /_(manifest|evidence|adapter_result)\./.test(p)
  );
}
function visual(path){
  const p=String(path||"").toLowerCase().split("?")[0];
  return (
    p.endsWith(".png") ||
    p.endsWith(".jpg") ||
    p.endsWith(".jpeg") ||
    p.endsWith(".svg") ||
    p.endsWith(".html") ||
    p.endsWith(".htm") ||
    p.endsWith(".avi") ||
    p.endsWith(".mp4") ||
    p.endsWith(".webm")
  ) && !technical(p);
}
function blender(pidValue,name){
  return `projects/runtime/${pidValue}/results/generated_visual_media/blender_presentation/${name}`;
}
function pat002Core(pidValue){
  if(pidValue!=="PHOENIX-PAT-002") return [];
  return [
    {id:"design_exterior",label:"Ontwerp · exterieur",path:blender(pidValue,"phoenix_exterior_front.png")},
    {id:"design_rear",label:"Ontwerp · achterzijde",path:blender(pidValue,"phoenix_exterior_rear.png")},
    {id:"design_bird",label:"Ontwerp · vogelvlucht",path:blender(pidValue,"phoenix_bird_view.png")},
    {id:"design_interior",label:"Ontwerp · interieur cutaway",path:blender(pidValue,"phoenix_interior_cutaway.png")}
  ];
}
function requestedVisuals(pidValue){
  const s=strict();
  const out=[];
  if(s && typeof s.checkedOutputs==="function"){
    for(const item of s.checkedOutputs()){
      let path=item.path;
      // For PAT-002 use real IFC->Blender evidence where an equivalent exists.
      if(pidValue==="PHOENIX-PAT-002"){
        if(item.id==="viewer_3d") path=blender(pidValue,"phoenix_exterior_front.png");
        if(item.id==="bird_view") path=blender(pidValue,"phoenix_bird_view.png");
      }
      if(visual(path) && !out.some(x=>x.path===path)){
        out.push({id:item.id,label:item.label,path});
      }
    }
  }
  return out;
}
function buildPlaylist(){
  const p=pid();
  if(!p) return [];
  const requested=requestedVisuals(p);
  const core=pat002Core(p);
  const merged=[...core,...requested];
  const seen=new Set();
  return merged.filter(item=>{
    if(!visual(item.path) || technical(item.path) || seen.has(item.path)) return false;
    seen.add(item.path);
    return true;
  });
}
function stage(){
  return document.getElementById("phoenixTvStage");
}
function meta(){
  return document.getElementById("phoenixTvMeta");
}
function setLoading(item){
  const s=stage();
  if(!s) return;
  s.dataset.phoenixVisualOnlyLoading="1";
  s.style.visibility="hidden";
  const host=s.parentElement;
  if(!host) return;
  let overlay=document.getElementById("phoenixTvVisualOnlyOverlay");
  if(!overlay){
    overlay=document.createElement("div");
    overlay.id="phoenixTvVisualOnlyOverlay";
    overlay.style.cssText="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:#02070d;color:#dff6ff;font:600 14px Segoe UI,Arial;z-index:20;";
    host.style.position="relative";
    host.appendChild(overlay);
  }
  overlay.textContent=`Visuele output laden… ${item?.label||""}`;
  overlay.style.display="flex";
}
function clearLoading(){
  const s=stage();
  if(s){
    s.style.visibility="";
    delete s.dataset.phoenixVisualOnlyLoading;
  }
  const overlay=document.getElementById("phoenixTvVisualOnlyOverlay");
  if(overlay) overlay.style.display="none";
}
function setMeta(item){
  const m=meta();
  if(m && item){
    m.textContent=`${pos+1}/${playlist.length} · ${item.label} · ${item.path}`;
  }
}
async function openAt(index){
  if(busy || !playlist.length) return false;
  const r=router();
  if(!r || typeof r.seekExactArtifact!=="function") return false;
  busy=true;
  pos=(index+playlist.length)%playlist.length;
  const item=playlist[pos];
  setLoading(item);
  try{
    const ok=await r.seekExactArtifact(item.path);
    if(ok){
      setMeta(item);
      return true;
    }
    return false;
  } finally {
    clearLoading();
    busy=false;
  }
}
async function startPresentation(){
  playlist=buildPlaylist();
  pos=0;
  active=playlist.length>0;
  if(!active) return false;
  return openAt(0);
}
function intercept(ev){
  const b=ev.target?.closest?.("button");
  if(!b) return;

  if(b.id==="phoenixTvPresentation"){
    ev.preventDefault();
    ev.stopImmediatePropagation();
    startPresentation();
    return;
  }

  if(!active || !playlist.length) return;

  if(b.id==="phoenixTvNext"){
    ev.preventDefault();
    ev.stopImmediatePropagation();
    openAt(pos+1);
    return;
  }
  if(b.id==="phoenixTvPrev"){
    ev.preventDefault();
    ev.stopImmediatePropagation();
    openAt(pos-1);
    return;
  }
}
function currentPath(){
  const r=router();
  return r && typeof r.currentArtifactPath==="function" ? r.currentArtifactPath() : "";
}
function suppressTechnicalIfVisible(){
  if(!active || busy || !playlist.length) return;
  const p=currentPath();
  if(p && technical(p)){
    openAt(pos);
  }
}
function start(){
  document.addEventListener("click",intercept,true);
  const m=meta();
  if(m){
    new MutationObserver(suppressTechnicalIfVisible).observe(m,{
      childList:true,subtree:true,characterData:true
    });
  }
}
if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",start,{once:true});
}else{
  start();
}

window.PHOENIX_TV_VISUAL_ONLY_PRESENTATION_V1_0={
  VERSION,
  technical,
  visual,
  buildPlaylist,
  startPresentation,
  getPlaylist:()=>playlist.slice()
};
})();