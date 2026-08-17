// PROJECT PHOENIX DE TV DIRECT AUTHORITATIVE PNG RENDER BRIDGE + RESPONSIVE CONTROL BAR REPAIR v1.0
(()=>{"use strict";

const PAT002="PHOENIX-PAT-002";
const BASE=`projects/runtime/${PAT002}/results/generated_visual_media/blender_presentation/`;
const ITEMS=[
  {file:"phoenix_exterior_front.png",label:"Ontwerp · exterieur voorzijde"},
  {file:"phoenix_exterior_rear.png",label:"Ontwerp · achterzijde"},
  {file:"phoenix_bird_view.png",label:"Ontwerp · vogelvlucht"},
  {file:"phoenix_interior_cutaway.png",label:"Ontwerp · interieur cutaway"}
];
const STATE={index:0,timer:null};

function activeProject(){
  const r=window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0;
  if(r && typeof r.authoritativeActiveProjectId==="function"){
    try{return r.authoritativeActiveProjectId();}catch(_){}
  }
  return PAT002;
}
function stage(){
  return document.getElementById("phoenixTvStage") ||
         document.getElementById("phoenixTvOutput") ||
         document.querySelector("[data-phoenix-tv-stage]") ||
         document.querySelector(".phoenix-tv-stage") ||
         document.querySelector(".tv-stage");
}
function statusNode(){return document.getElementById("phoenixTvStatus");}
function metaNode(){return document.getElementById("phoenixTvMeta");}
function commandInput(){return document.getElementById("phoenixTvCommand");}
function directUrl(path){
  const p=String(path||"").replace(/^\/+/,"");
  return `/artifact?path=${encodeURIComponent(p)}`;
}
function candidates(path){
  const p=String(path||"").replace(/^\/+/,"");
  return [
    `/artifact?path=${encodeURIComponent(p)}`,
    `/api/artifact?path=${encodeURIComponent(p)}`,
    `/api/file?path=${encodeURIComponent(p)}`,
    `/files/${p}`,
    `/${p}`
  ];
}
function releaseMask(){
  const s=stage();
  if(s){
    s.style.visibility="";
    s.style.opacity="";
    s.removeAttribute("aria-busy");
  }
  document.querySelectorAll("[data-phoenix-tv-loading-mask],.phoenix-tv-loading-mask").forEach(n=>n.remove());
}
function fit(){
  const s=stage();
  if(!s)return;
  const top=s.getBoundingClientRect().top;
  const reserve=178;
  const h=Math.max(300,Math.min(720,window.innerHeight-top-reserve));
  s.style.height=`${h}px`;
  s.style.minHeight="300px";
  s.style.maxHeight=`${h}px`;
  s.style.overflow="hidden";
}
function ensureControlsVisible(){
  const input=commandInput();
  if(!input)return;
  const host=input.closest("section,div");
  if(host) host.style.position="relative";
}
async function probe(url){
  try{
    const r=await fetch(url,{method:"HEAD",cache:"no-store"});
    return r.ok;
  }catch(_){return false;}
}
async function resolveUrl(path){
  for(const u of candidates(path)){
    if(await probe(u))return u;
  }
  return directUrl(path);
}
async function renderIndex(i){
  if(activeProject()!==PAT002)return false;
  STATE.index=(i+ITEMS.length)%ITEMS.length;
  const item=ITEMS[STATE.index], path=BASE+item.file, s=stage();
  if(!s)return false;

  if(statusNode())statusNode().textContent="LADEN";
  if(metaNode())metaNode().textContent=item.label+" · "+PAT002+" · IFC → Blender";

  s.style.visibility="";
  s.style.opacity="";
  s.setAttribute("aria-busy","true");
  s.innerHTML="";
  const wrap=document.createElement("div");
  wrap.setAttribute("data-phoenix-tv-direct-png","1");
  wrap.style.cssText="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#02070c;";
  const img=document.createElement("img");
  img.alt=item.label;
  img.style.cssText="display:block;max-width:100%;max-height:100%;width:auto;height:auto;object-fit:contain;";
  wrap.appendChild(img);
  s.appendChild(wrap);
  fit();

  const url=await resolveUrl(path);
  return await new Promise(resolve=>{
    let done=false;
    const finish=(ok)=>{
      if(done)return; done=true;
      releaseMask();
      if(statusNode())statusNode().textContent=ok?"GEREED":"VISUAL NIET GEVONDEN";
      resolve(ok);
    };
    img.onload=()=>finish(true);
    img.onerror=async()=>{
      // Last-resort compatibility bridge: ask the existing exact-artifact router,
      // but keep technical intermediate content hidden.
      try{
        const r=window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0;
        if(r && typeof r.seekExactArtifact==="function"){
          const ok=await r.seekExactArtifact(path);
          if(ok){releaseMask(); if(statusNode())statusNode().textContent="GEREED"; resolve(true); return;}
        }
      }catch(_){}
      finish(false);
    };
    img.src=url;
    setTimeout(()=>finish(img.complete && img.naturalWidth>0),12000);
  });
}
function normalize(v){return String(v||"").trim().toLowerCase().replace(/\s+/g," ");}
function commandIndex(v){
  const c=normalize(v);
  if(/^(toon )?(ontwerp|exterieur|variant b|3d)$/.test(c))return 0;
  if(/^(toon )?(achterzijde|achtergevel|rear)$/.test(c))return 1;
  if(/^(toon )?(vogelvlucht|bird view)$/.test(c))return 2;
  if(/^(toon )?(interieur|interior)$/.test(c))return 3;
  const leaf=c.replace(/^toon\s+/,"").split(/[\\/]/).pop();
  const n=ITEMS.findIndex(x=>x.file.toLowerCase()===leaf);
  return n;
}
function stopPresentation(){
  if(STATE.timer){clearInterval(STATE.timer);STATE.timer=null;}
}
async function startPresentation(){
  stopPresentation();
  await renderIndex(0);
  STATE.timer=setInterval(()=>renderIndex(STATE.index+1),7000);
}
function buttonKind(b){
  if(!b)return "";
  const id=(b.id||"").toLowerCase();
  const txt=normalize(b.textContent);
  if(id==="phoenixtvcommandgo" || txt==="toon")return "show";
  if(txt.includes("presentatie"))return "presentation";
  if(txt.includes("volgende"))return "next";
  if(txt.includes("vorige"))return "prev";
  if(txt.includes("vol scherm") || txt.includes("fullscreen"))return "fullscreen";
  return "";
}
function own(ev){
  const b=ev.target&&ev.target.closest?ev.target.closest("button"):null;
  const kind=buttonKind(b);
  if(!kind)return;
  if(activeProject()!==PAT002)return;
  if(!["show","presentation","next","prev"].includes(kind))return;
  ev.preventDefault(); ev.stopImmediatePropagation();
  if(kind==="presentation")startPresentation();
  else if(kind==="next"){stopPresentation();renderIndex(STATE.index+1);}
  else if(kind==="prev"){stopPresentation();renderIndex(STATE.index-1);}
  else{
    stopPresentation();
    const input=commandInput(), idx=commandIndex(input?input.value:"");
    if(idx>=0)renderIndex(idx);
    else if(statusNode())statusNode().textContent="COMMANDO ONBEKEND";
  }
}
function key(ev){
  if(ev.key!=="Enter" || !ev.target || ev.target.id!=="phoenixTvCommand")return;
  if(activeProject()!==PAT002)return;
  const idx=commandIndex(ev.target.value);
  if(idx<0)return;
  ev.preventDefault();ev.stopImmediatePropagation();
  stopPresentation();renderIndex(idx);
}
window.addEventListener("click",own,true);
window.addEventListener("keydown",key,true);
window.addEventListener("resize",fit,{passive:true});
document.addEventListener("fullscreenchange",()=>setTimeout(fit,50));
setTimeout(()=>{fit();ensureControlsVisible();releaseMask();},0);
setTimeout(fit,500);

window.PHOENIX_DE_TV_DIRECT_AUTHORITATIVE_PNG_RENDER_BRIDGE_V1_0={
  renderIndex,startPresentation,stopPresentation,commandIndex,fit,releaseMask
};
})();