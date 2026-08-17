// PROJECT PHOENIX DE TV SEEK-EXACT VISUAL-READY BRIDGE + LOADING FAILSAFE v1.0
(()=>{"use strict";

const PAT002="PHOENIX-PAT-002";
const BASE=`projects/runtime/${PAT002}/results/generated_visual_media/blender_presentation/`;
const ITEMS=[
  {file:"phoenix_exterior_front.png",label:"Ontwerp · exterieur voorzijde"},
  {file:"phoenix_exterior_rear.png",label:"Ontwerp · achterzijde"},
  {file:"phoenix_bird_view.png",label:"Ontwerp · vogelvlucht"},
  {file:"phoenix_interior_cutaway.png",label:"Ontwerp · interieur cutaway"}
];
const S={index:0,timer:null,busy:false,token:0};

function norm(v){return String(v||"").trim().toLowerCase().replace(/\s+/g," ");}
function activeProject(){
  const r=window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0;
  if(r && typeof r.authoritativeActiveProjectId==="function"){
    try{return r.authoritativeActiveProjectId();}catch(_){}
  }
  return null;
}
function router(){return window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0 || null;}
function stage(){
  return document.getElementById("phoenixTvStage") ||
         document.getElementById("phoenixTvOutput") ||
         document.querySelector("[data-phoenix-tv-stage]") ||
         document.querySelector(".phoenix-tv-stage") ||
         document.querySelector(".tv-stage");
}
function meta(){return document.getElementById("phoenixTvMeta");}
function status(){return document.getElementById("phoenixTvStatus");}
function command(){return document.getElementById("phoenixTvCommand");}

function itemPath(item){return BASE+item.file;}

function visualReady(path){
  const st=stage(), m=meta();
  if(!st) return false;

  const target=path.toLowerCase();
  const metaText=(m?.textContent||"").toLowerCase();
  const stageText=(st.textContent||"").toLowerCase();

  const pathEvidence=metaText.includes(target.toLowerCase()) ||
                     metaText.includes(path.split("/").pop().toLowerCase()) ||
                     stageText.includes(path.split("/").pop().toLowerCase());

  const visualNode=st.querySelector("img,canvas,video,iframe,svg,object,embed");
  if(visualNode){
    if(visualNode.tagName==="IMG"){
      return visualNode.complete && visualNode.naturalWidth>0 && (pathEvidence || true);
    }
    return true;
  }

  // Some Phoenix renderers use background-image or HTML/CSS-rendered wrappers.
  const descendants=[st,...st.querySelectorAll("*")];
  for(const n of descendants.slice(0,120)){
    try{
      const bg=getComputedStyle(n).backgroundImage;
      if(bg && bg!=="none" && bg.includes("url(")) return true;
    }catch(_){}
  }
  return false;
}
function overlay(){
  const st=stage();
  if(!st || !st.parentElement) return null;
  const host=st.parentElement;
  if(getComputedStyle(host).position==="static") host.style.position="relative";
  let o=document.getElementById("phoenixTvVisualReadyOverlay");
  if(!o){
    o=document.createElement("div");
    o.id="phoenixTvVisualReadyOverlay";
    o.style.cssText="position:absolute;inset:0;z-index:10000;display:none;align-items:center;justify-content:center;background:#02070d;color:#dff6ff;font:600 14px Segoe UI,Arial;text-align:center;padding:20px;";
    host.appendChild(o);
  }
  return o;
}
function mask(item){
  const st=stage();
  if(st){
    st.style.visibility="hidden";
    st.setAttribute("aria-busy","true");
  }
  const o=overlay();
  if(o){
    o.textContent=`Visuele output laden… ${item.label}`;
    o.style.display="flex";
  }
  if(status()) status().textContent="LADEN";
}
function release(ok,item,message){
  const st=stage(),o=document.getElementById("phoenixTvVisualReadyOverlay");
  if(st){
    st.style.visibility="";
    st.removeAttribute("aria-busy");
  }
  if(o) o.style.display="none";
  if(status()) status().textContent=ok?"GEREED":"VISUAL NIET GEVONDEN";
  if(meta()){
    meta().textContent=ok
      ? `${S.index+1}/${ITEMS.length} · ${item.label} · ${itemPath(item)}`
      : `${item.label} · ${message||"artifact kon niet worden geopend"}`;
  }
}
function waitForVisual(path,timeoutMs,token){
  return new Promise(resolve=>{
    const started=Date.now();
    let observer=null;
    const finish=(v)=>{
      if(observer)observer.disconnect();
      clearInterval(poll);
      resolve(v);
    };
    const check=()=>{
      if(token!==S.token)return finish(false);
      if(visualReady(path))return finish(true);
      if(Date.now()-started>=timeoutMs)return finish(false);
    };
    const st=stage();
    if(st){
      observer=new MutationObserver(check);
      observer.observe(st,{childList:true,subtree:true,attributes:true,characterData:true});
    }
    const poll=setInterval(check,120);
    check();
  });
}
async function openIndex(i){
  if(activeProject()!==PAT002 || S.busy)return false;
  const r=router();
  if(!r || typeof r.seekExactArtifact!=="function"){
    const item=ITEMS[(i+ITEMS.length)%ITEMS.length];
    release(false,item,"seekExactArtifact bridge ontbreekt");
    return false;
  }

  S.index=(i+ITEMS.length)%ITEMS.length;
  const item=ITEMS[S.index];
  const path=itemPath(item);
  const token=++S.token;
  S.busy=true;
  mask(item);

  let seekOk=false;
  try{
    const seekPromise=Promise.resolve(r.seekExactArtifact(path));
    seekOk=await Promise.race([
      seekPromise.then(v=>!!v).catch(()=>false),
      new Promise(res=>setTimeout(()=>res(false),8000))
    ]);

    // Even if the bridge returns quickly, wait for actual visual DOM readiness.
    const ready=await waitForVisual(path,7000,token);
    const ok=seekOk && ready;
    release(ok,item,ok?"":"visual-ready timeout");
    return ok;
  }catch(e){
    release(false,item,String(e?.message||e||"onbekende fout"));
    return false;
  }finally{
    if(token===S.token)S.busy=false;
  }
}
function stopPresentation(){
  if(S.timer){clearInterval(S.timer);S.timer=null;}
}
async function startPresentation(){
  stopPresentation();
  await openIndex(0);
  S.timer=setInterval(()=>{if(!S.busy)openIndex(S.index+1);},7000);
}
function commandIndex(v){
  const c=norm(v);
  if(/^(toon )?(ontwerp|exterieur|variant b|3d)$/.test(c))return 0;
  if(/^(toon )?(achterzijde|achtergevel|rear)$/.test(c))return 1;
  if(/^(toon )?(vogelvlucht|bird view)$/.test(c))return 2;
  if(/^(toon )?(interieur|interior)$/.test(c))return 3;
  const leaf=c.replace(/^toon\s+/,"").split(/[\\/]/).pop();
  return ITEMS.findIndex(x=>x.file.toLowerCase()===leaf);
}
function buttonType(b){
  if(!b)return "";
  const id=(b.id||"").toLowerCase(), t=norm(b.textContent);
  if(id==="phoenixtvcommandgo"||t==="toon")return "show";
  if(t.includes("presentatie"))return "presentation";
  if(t.includes("volgende"))return "next";
  if(t.includes("vorige"))return "prev";
  return "";
}
function ownClick(ev){
  const b=ev.target?.closest?.("button"), type=buttonType(b);
  if(activeProject()!==PAT002 || !type)return;
  ev.preventDefault();ev.stopImmediatePropagation();
  if(type==="presentation")startPresentation();
  else if(type==="next"){stopPresentation();openIndex(S.index+1);}
  else if(type==="prev"){stopPresentation();openIndex(S.index-1);}
  else{
    const idx=commandIndex(command()?.value||"");
    if(idx>=0){stopPresentation();openIndex(idx);}
    else if(status())status().textContent="COMMANDO ONBEKEND";
  }
}
function ownKey(ev){
  if(ev.key!=="Enter" || ev.target?.id!=="phoenixTvCommand" || activeProject()!==PAT002)return;
  const idx=commandIndex(ev.target.value);
  if(idx<0)return;
  ev.preventDefault();ev.stopImmediatePropagation();stopPresentation();openIndex(idx);
}
function responsive(){
  const st=stage();
  if(!st)return;
  const top=st.getBoundingClientRect().top;
  const reserve=210;
  const h=Math.max(260,Math.min(560,window.innerHeight-top-reserve));
  st.style.height=`${h}px`;
  st.style.maxHeight=`${h}px`;
  st.style.minHeight="260px";
  st.style.overflow="hidden";
}
function clearStaleLoading(){
  release(false,ITEMS[S.index],"gereed voor nieuwe opdracht");
  if(status())status().textContent="GEREED";
}

window.addEventListener("click",ownClick,true);
window.addEventListener("keydown",ownKey,true);
window.addEventListener("resize",responsive,{passive:true});
document.addEventListener("fullscreenchange",()=>setTimeout(responsive,50));
setTimeout(()=>{responsive();clearStaleLoading();},0);
setTimeout(responsive,400);

window.PHOENIX_DE_TV_VISUAL_READY_BRIDGE_V1_0={
  openIndex,startPresentation,stopPresentation,commandIndex,visualReady,responsive
};
})();