// PROJECT PHOENIX DE TV AUTHORITATIVE VISUAL MEDIA ROUTER v1.0
(()=>{"use strict";

const VERSION="1.0.0";
const STATE={catalog:[],index:0,active:false,busy:false,timer:null};

function routing(){
  return window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0 || null;
}
function activeProjectId(){
  const r=routing();
  return r && typeof r.authoritativeActiveProjectId==="function"
    ? r.authoritativeActiveProjectId()
    : null;
}
function norm(s){
  return String(s||"").trim().toLowerCase().replace(/\s+/g," ");
}
function technical(path){
  const p=norm(path).replace(/\\/g,"/");
  return (
    /\.(json|txt|log|csv|xml)$/i.test(p) ||
    /(^|\/)[^/]*(manifest|evidence|adapter_result|project_state|digital_twin)[^/]*$/i.test(p)
  );
}
function visual(path){
  const p=String(path||"").toLowerCase().split("?")[0];
  return /\.(png|jpg|jpeg|svg|webp|mp4|webm|avi|html|htm)$/i.test(p) && !technical(p);
}
function blenderPath(pid,name){
  return `projects/runtime/${pid}/results/generated_visual_media/blender_presentation/${name}`;
}
function pat002Catalog(pid){
  return [
    {id:"design",label:"Ontwerp · exterieur voorzijde",path:blenderPath(pid,"phoenix_exterior_front.png")},
    {id:"rear",label:"Ontwerp · achterzijde",path:blenderPath(pid,"phoenix_exterior_rear.png")},
    {id:"bird",label:"Ontwerp · vogelvlucht",path:blenderPath(pid,"phoenix_bird_view.png")},
    {id:"interior",label:"Ontwerp · interieur cutaway",path:blenderPath(pid,"phoenix_interior_cutaway.png")}
  ];
}
function buildCatalog(){
  const pid=activeProjectId();
  if(!pid) return [];
  if(pid==="PHOENIX-PAT-002") return pat002Catalog(pid).filter(x=>visual(x.path));
  return [];
}
function commandMap(pid){
  if(pid!=="PHOENIX-PAT-002") return new Map();
  const c=pat002Catalog(pid);
  const by=id=>c.find(x=>x.id===id);
  return new Map([
    ["toon ontwerp",by("design")],
    ["ontwerp",by("design")],
    ["toon exterieur",by("design")],
    ["exterieur",by("design")],
    ["toon variant b",by("design")],
    ["variant b",by("design")],
    ["toon 3d",by("design")],
    ["3d",by("design")],
    ["toon interieur",by("interior")],
    ["interieur",by("interior")],
    ["toon vogelvlucht",by("bird")],
    ["vogelvlucht",by("bird")],
    ["toon bird view",by("bird")],
    ["bird view",by("bird")],
    ["toon achterzijde",by("rear")],
    ["achterzijde",by("rear")],
    ["toon achtergevel",by("rear")],
    ["achtergevel",by("rear")]
  ]);
}
function resolveCommand(raw){
  const pid=activeProjectId();
  if(!pid) return null;
  const cmd=norm(raw);
  const mapped=commandMap(pid).get(cmd);
  if(mapped) return mapped;

  let path=String(raw||"").trim().replace(/^toon\s+/i,"").replace(/\\/g,"/");
  const cat=buildCatalog();
  const exact=cat.find(x=>norm(x.path)===norm(path));
  if(exact) return exact;

  const leaf=path.split("/").pop();
  return cat.find(x=>x.path.endsWith("/"+leaf)) || null;
}
function stage(){
  return document.getElementById("phoenixTvStage");
}
function statusNode(){
  return document.getElementById("phoenixTvStatus");
}
function metaNode(){
  return document.getElementById("phoenixTvMeta");
}
function ensureOverlay(){
  const s=stage();
  if(!s || !s.parentElement) return null;
  const host=s.parentElement;
  if(getComputedStyle(host).position==="static") host.style.position="relative";
  let o=document.getElementById("phoenixTvAuthoritativeOverlay");
  if(!o){
    o=document.createElement("div");
    o.id="phoenixTvAuthoritativeOverlay";
    o.style.cssText=[
      "position:absolute","inset:0","z-index:9999","display:none",
      "align-items:center","justify-content:center","background:#02070d",
      "color:#dff6ff","font:600 14px Segoe UI,Arial"
    ].join(";");
    host.appendChild(o);
  }
  return o;
}
function mask(item){
  const s=stage();
  if(s) s.style.visibility="hidden";
  const o=ensureOverlay();
  if(o){
    o.textContent=`Visuele output laden… ${item?.label||""}`;
    o.style.display="flex";
  }
}
function unmask(){
  const s=stage();
  if(s) s.style.visibility="";
  const o=document.getElementById("phoenixTvAuthoritativeOverlay");
  if(o) o.style.display="none";
}
function updateUi(item){
  const m=metaNode();
  if(m && item){
    m.textContent=`${STATE.index+1}/${STATE.catalog.length} · ${item.label} · ${item.path}`;
  }
  const st=statusNode();
  if(st) st.textContent="VISUEEL";
}
async function openItem(item){
  if(!item || STATE.busy) return false;
  const r=routing();
  if(!r || typeof r.seekExactArtifact!=="function") return false;
  if(!visual(item.path) || technical(item.path)) return false;

  STATE.busy=true;
  mask(item);
  try{
    const ok=await r.seekExactArtifact(item.path);
    if(ok){
      updateUi(item);
      return true;
    }
    return false;
  }finally{
    unmask();
    STATE.busy=false;
  }
}
async function openIndex(i){
  if(!STATE.catalog.length) STATE.catalog=buildCatalog();
  if(!STATE.catalog.length) return false;
  STATE.index=(i+STATE.catalog.length)%STATE.catalog.length;
  return openItem(STATE.catalog[STATE.index]);
}
function stopTimer(){
  if(STATE.timer){clearInterval(STATE.timer);STATE.timer=null;}
}
async function startPresentation(){
  stopTimer();
  STATE.catalog=buildCatalog();
  STATE.index=0;
  STATE.active=STATE.catalog.length>0;
  if(!STATE.active) return false;
  const ok=await openIndex(0);
  if(ok){
    STATE.timer=setInterval(()=>{ if(!STATE.busy) openIndex(STATE.index+1); },7000);
  }
  return ok;
}
async function handleCommand(raw){
  stopTimer();
  STATE.catalog=buildCatalog();
  const item=resolveCommand(raw);
  if(!item) return false;
  STATE.active=true;
  const idx=STATE.catalog.findIndex(x=>x.path===item.path);
  if(idx>=0) STATE.index=idx;
  return openItem(item);
}
function isButton(el,id,text){
  if(!el) return false;
  if(el.id===id) return true;
  return norm(el.textContent)===norm(text);
}
function captureClick(ev){
  const b=ev.target?.closest?.("button");
  if(!b) return;

  if(isButton(b,"phoenixTvPresentation","PRESENTATIE")){
    ev.preventDefault(); ev.stopImmediatePropagation();
    startPresentation();
    return;
  }
  if(isButton(b,"phoenixTvNext","VOLGENDE") || /volgende/.test(norm(b.textContent))){
    if(!STATE.active) STATE.catalog=buildCatalog();
    if(STATE.catalog.length){
      ev.preventDefault(); ev.stopImmediatePropagation(); stopTimer(); STATE.active=true;
      openIndex(STATE.index+1);
    }
    return;
  }
  if(isButton(b,"phoenixTvPrev","VORIGE") || /vorige/.test(norm(b.textContent))){
    if(!STATE.active) STATE.catalog=buildCatalog();
    if(STATE.catalog.length){
      ev.preventDefault(); ev.stopImmediatePropagation(); stopTimer(); STATE.active=true;
      openIndex(STATE.index-1);
    }
    return;
  }
  if(isButton(b,"phoenixTvCommandGo","TOON")){
    const input=document.getElementById("phoenixTvCommand");
    if(input && resolveCommand(input.value)){
      ev.preventDefault(); ev.stopImmediatePropagation();
      handleCommand(input.value);
    }
  }
}
function captureKey(ev){
  if(ev.key!=="Enter" || ev.target?.id!=="phoenixTvCommand") return;
  if(resolveCommand(ev.target.value)){
    ev.preventDefault(); ev.stopImmediatePropagation();
    handleCommand(ev.target.value);
  }
}
function install(){
  window.addEventListener("click",captureClick,true);
  window.addEventListener("keydown",captureKey,true);
  STATE.catalog=buildCatalog();
}
if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",install,{once:true});
}else{
  install();
}

window.PHOENIX_TV_AUTHORITATIVE_VISUAL_MEDIA_ROUTER_V1_0={
  VERSION,
  activeProjectId,
  technical,
  visual,
  buildCatalog,
  resolveCommand,
  openItem,
  openIndex,
  startPresentation,
  handleCommand,
  state:STATE
};
})();