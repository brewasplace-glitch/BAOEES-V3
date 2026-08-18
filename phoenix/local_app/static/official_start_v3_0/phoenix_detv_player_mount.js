// PROJECT PHOENIX DE TV OPEN-SOURCE PLAYER ROBUST MOUNT + ACTIVATION REPAIR v1.0
(()=>{"use strict";
const VERSION="1.0.0";
const SIDECAR="http://127.0.0.1:8770";
const STATE={mounted:false,lastError:"",attempts:0};

function norm(s){return String(s||"").trim().toLowerCase().replace(/\s+/g," ");}

function activeProject(){
  const r=window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0;
  try{
    const p=r&&typeof r.authoritativeActiveProjectId==="function" ? r.authoritativeActiveProjectId() : null;
    return p || "PHOENIX-PAT-002";
  }catch(_){return "PHOENIX-PAT-002";}
}

async function healthy(){
  try{
    const ac=new AbortController();
    const t=setTimeout(()=>ac.abort(),1800);
    const r=await fetch(`${SIDECAR}/health`,{cache:"no-store",signal:ac.signal});
    clearTimeout(t);
    return r.ok;
  }catch(_){return false;}
}

function findCommandInput(){
  return document.getElementById("phoenixTvCommand") ||
    [...document.querySelectorAll("input")].find(i=>{
      const p=norm(i.placeholder);
      return p.includes("toon plattegronden") || p.includes("toon ontwerp");
    }) || null;
}

function findTvCard(){
  const input=findCommandInput();
  if(input){
    let n=input;
    for(let i=0;i<8 && n;i++,n=n.parentElement){
      const txt=norm(n.textContent);
      if(txt.includes("de tv") && txt.includes("presentatie") && txt.includes("volgende")) return n;
    }
  }

  const all=[...document.querySelectorAll("section,aside,article,div")];
  const candidates=all.filter(n=>{
    const t=norm(n.textContent);
    return t.includes("de tv") && t.includes("presentatie") && t.includes("vorige") && t.includes("volgende");
  });
  candidates.sort((a,b)=>a.getBoundingClientRect().width*b.getBoundingClientRect().height -
                         b.getBoundingClientRect().width*a.getBoundingClientRect().height);
  return candidates[0]||null;
}

function findControlAnchor(card){
  if(!card)return null;
  const input=findCommandInput();
  if(input && card.contains(input)){
    let n=input.parentElement;
    while(n && n.parentElement!==card){
      const txt=norm(n.textContent);
      if(txt.includes("presentatie")||txt.includes("vorige")||txt.includes("volgende")) return n;
      n=n.parentElement;
    }
    return input.parentElement;
  }
  const buttons=[...card.querySelectorAll("button")];
  const b=buttons.find(x=>norm(x.textContent).includes("presentatie"));
  return b?.parentElement||null;
}

function removeOldMounts(card){
  document.querySelectorAll("#phoenixOpenSourceMediaPlayer,#phoenixOpenSourceMediaPlayerMount").forEach(n=>n.remove());
  if(!card)return;
  card.querySelectorAll("[data-phoenix-tv-loading-mask],#phoenixTvVisualReadyOverlay,#phoenixTvAuthoritativeOverlay").forEach(n=>n.remove());
}

function makeMount(card,anchor){
  const mount=document.createElement("div");
  mount.id="phoenixOpenSourceMediaPlayerMount";
  mount.dataset.phoenixOpenSourcePlayer="1";
  mount.style.cssText=[
    "width:100%","height:430px","min-height:300px",
    "max-height:calc(100vh - 390px)","background:#02070d",
    "border-bottom:1px solid #174565","overflow:hidden"
  ].join(";");

  const iframe=document.createElement("iframe");
  iframe.id="phoenixOpenSourceMediaPlayer";
  iframe.title="PHOENIX DE TV Open-Source Media Player";
  iframe.src=`${SIDECAR}/player/?project=${encodeURIComponent(activeProject())}`;
  iframe.style.cssText="display:block;width:100%;height:100%;border:0;background:#02070d;";
  iframe.setAttribute("allow","fullscreen");
  mount.appendChild(iframe);

  if(anchor && anchor.parentElement){
    anchor.parentElement.insertBefore(mount,anchor);
  }else{
    card.appendChild(mount);
  }
  return mount;
}

function hideLegacyDisplay(card,mount,anchor){
  if(!card)return;
  [...card.children].forEach(ch=>{
    if(ch===mount) return;
    if(anchor && (ch===anchor || ch.contains(anchor))) return;
    const t=norm(ch.textContent);
    // Keep title/header; hide only the old output/display block.
    if(t.includes("de tv") && ch.querySelectorAll("button").length===0) return;
    if(ch.querySelectorAll("button,input").length===0 && ch.getBoundingClientRect().height>120){
      ch.dataset.phoenixLegacyTvHidden="1";
      ch.style.display="none";
    }
  });
}

function setStatus(text){
  const n=document.getElementById("phoenixTvStatus");
  if(n)n.textContent=text;
}

async function mount(){
  STATE.attempts++;
  if(!(await healthy())){
    STATE.lastError="SIDECAR_UNHEALTHY";
    setStatus("PLAYER OFFLINE");
    return false;
  }

  const card=findTvCard();
  if(!card){
    STATE.lastError="TV_CARD_NOT_FOUND";
    setStatus("PLAYER WACHT OP TV");
    return false;
  }

  const anchor=findControlAnchor(card);
  removeOldMounts(card);
  const m=makeMount(card,anchor);
  hideLegacyDisplay(card,m,anchor);
  STATE.mounted=true;
  STATE.lastError="";
  setStatus("OPEN-SOURCE PLAYER");
  return true;
}

async function ensureMounted(){
  if(document.getElementById("phoenixOpenSourceMediaPlayer")) return true;
  return mount();
}

function observe(){
  const mo=new MutationObserver(()=>{
    if(!document.getElementById("phoenixOpenSourceMediaPlayer")){
      clearTimeout(observe._t);
      observe._t=setTimeout(ensureMounted,120);
    }
  });
  mo.observe(document.documentElement,{childList:true,subtree:true});
}

async function boot(){
  for(let i=0;i<12;i++){
    if(await ensureMounted()) break;
    await new Promise(r=>setTimeout(r,500));
  }
  observe();
}

if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot,{once:true});
else boot();

window.PHOENIX_DE_TV_OPEN_SOURCE_PLAYER_MOUNT_REPAIR_V1_0={
  VERSION,healthy,findTvCard,findControlAnchor,mount,ensureMounted,state:STATE
};
})();
/* PHOENIX DE TV HARD MOUNT ACTIVATION v1.0
   Route-independent, idempotent activation shim.
   It preserves the existing open-source player implementation and only
   activates known mount hooks/events after the DOM and sidecar are ready. */
;(function phoenixDetvHardMountActivation() {
  "use strict";

  const MARK = "data-phoenix-hard-mount-activation";
  const ROOT_SELECTORS = [
    "[data-phoenix-player-mount]",
    "[data-detv-player-mount]",
    "#phoenix-player",
    "#detv-player",
    "#de-tv-player",
    "#media-player",
    "video[data-phoenix-media]",
    "video"
  ];

  const HOOKS = [
    "mountPhoenixOpenSourcePlayer",
    "mountOpenSourcePlayer",
    "mountDetvPlayer",
    "mountDETVPlayer",
    "activatePhoenixPlayer",
    "initPhoenixPlayer",
    "initDetvPlayer",
    "initDETVPlayer"
  ];

  function findRoot() {
    for (const selector of ROOT_SELECTORS) {
      const node = document.querySelector(selector);
      if (node) return node;
    }
    return document.documentElement;
  }

  function attempt(reason) {
    const root = findRoot();
    if (root && root.getAttribute && root.getAttribute(MARK) === "mounted") return;

    let invoked = false;
    for (const name of HOOKS) {
      const fn = window[name];
      if (typeof fn === "function") {
        try {
          fn();
          invoked = true;
          break;
        } catch (err) {
          console.warn("[PHOENIX DE TV] mount hook failed:", name, err);
        }
      }
    }

    try {
      document.dispatchEvent(new CustomEvent("phoenix:detv-player-mount", {
        bubbles: true,
        detail: { reason: reason || "hard-mount" }
      }));
    } catch (_) {}

    if (root && root.setAttribute) {
      root.setAttribute(MARK, invoked ? "mounted" : "attempted");
    }
  }

  function schedule(reason) {
    attempt(reason);
    setTimeout(function () { attempt(reason + ":250ms"); }, 250);
    setTimeout(function () { attempt(reason + ":1000ms"); }, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      schedule("dom-ready");
    }, { once: true });
  } else {
    schedule("dom-already-ready");
  }

  window.addEventListener("load", function () { attempt("window-load"); }, { once: true });
  document.addEventListener("phoenix:sidecar-ready", function () { schedule("sidecar-ready"); });
  document.addEventListener("phoenix:player-ready", function () { attempt("player-ready"); });
})();