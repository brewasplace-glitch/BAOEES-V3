(()=>{"use strict";
const project=new URLSearchParams(location.search).get("project")||"PHOENIX-PAT-002";
const base=`projects/runtime/${project}/results/generated_visual_media/blender_presentation/`;
const items=[
 {label:"Ontwerp · exterieur voorzijde",file:"phoenix_exterior_front.png"},
 {label:"Ontwerp · achterzijde",file:"phoenix_exterior_rear.png"},
 {label:"Ontwerp · vogelvlucht",file:"phoenix_bird_view.png"},
 {label:"Ontwerp · interieur cutaway",file:"phoenix_interior_cutaway.png"}
];
let i=0,timer=null;
const stage=document.getElementById("stage"),meta=document.getElementById("meta");
const mediaUrl=(file)=>`/media?path=${encodeURIComponent(base+file)}`;
function render(n){
 i=(n+items.length)%items.length;
 const x=items[i];
 stage.innerHTML="";
 const img=document.createElement("img");
 img.alt=x.label;
 img.onload=()=>{
   const liveLabel=`${i+1}/${items.length} Â· ${x.label}`;
   meta.textContent=liveLabel;
   if(typeof phoenixParentState==="function") phoenixParentState("GEREED",liveLabel);
 };
 img.onerror=()=>{stage.textContent="MEDIA NIET BESCHIKBAAR";meta.textContent=x.file;if(typeof phoenixParentState==="function")phoenixParentState("MEDIA NIET BESCHIKBAAR",x.file);};
 img.src=mediaUrl(x.file);
 stage.appendChild(img);
}
function stop(){if(timer){clearInterval(timer);timer=null;}}
function play(){stop();render(0);timer=setInterval(()=>render(i+1),7000);}
function cmd(v){
 const s=String(v||"").trim().toLowerCase().replace(/\s+/g," ");
 if(/^(toon )?(ontwerp|exterieur|variant b|3d)$/.test(s))return 0;
 if(/^(toon )?(achterzijde|achtergevel|rear)$/.test(s))return 1;
 if(/^(toon )?(vogelvlucht|bird view)$/.test(s))return 2;
 if(/^(toon )?(interieur|interior)$/.test(s))return 3;
 return -1;
}
document.getElementById("prev").onclick=()=>{stop();render(i-1)};
document.getElementById("next").onclick=()=>{stop();render(i+1)};
document.getElementById("play").onclick=play;
document.getElementById("show").onclick=()=>{const n=cmd(document.getElementById("command").value);if(n>=0){stop();render(n)}};
document.getElementById("command").onkeydown=e=>{if(e.key==="Enter")document.getElementById("show").click()};
document.getElementById("full").onclick=()=>document.documentElement.requestFullscreen?.();
window.PHOENIX_OPEN_SOURCE_MEDIA_PLAYER={render,play,stop,cmd,items};

/* PHOENIX DE TV SIDECAR PARENT COMMAND BRIDGE v1.1 NONRECURSIVE */
function phoenixParentState(state,label){
  try{
    parent.postMessage({
      type:"phoenix-detv-player-state",
      state:String(state||"GEREED"),
      label:String(label||"")
    },"http://127.0.0.1:8765");
  }catch(_){}
}
window.addEventListener("message",ev=>{
  if(!["http://127.0.0.1:8765","http://localhost:8765"].includes(ev.origin)) return;
  const d=ev.data;
  if(!d || d.type!=="phoenix-detv-command") return;
  const action=String(d.action||"");
  if(action==="prev"){
    stop(); render(i-1);
  }else if(action==="next"){
    stop(); render(i+1);
  }else if(action==="play"){
    play();
  }else if(action==="command"){
    const n=cmd(String(d.value||""));
    if(n>=0){ stop(); render(n); }
  }
  phoenixParentState("GEREED",meta ? meta.textContent : "");
});
window.addEventListener("load",()=>{
  try{
    parent.postMessage({
      type:"phoenix-detv-player-ready",
      project,
      label:meta ? meta.textContent : ""
    },"http://127.0.0.1:8765");
  }catch(_){}
},{once:true});

/* PHOENIX DE TV LIVE META SYNC v1.0
   Embedded mode removes duplicate sidecar controls while keeping the player engine,
   rendering logic and hidden internal meta source intact. */
const phoenixEmbeddedMode=(new URLSearchParams(location.search).get("embedded")==="1");

function phoenixUiNorm(value){
  return String(value||"").trim().toLowerCase().replace(/\s+/g," ");
}

function phoenixCommonAncestor(nodes){
  const valid=(nodes||[]).filter(Boolean);
  if(!valid.length)return null;
  let n=valid[0];
  while(n && n!==document.documentElement){
    if(valid.every(x=>n.contains(x)))return n;
    n=n.parentElement;
  }
  return null;
}

function phoenixHideEmbeddedGroup(nodes){
  const valid=(nodes||[]).filter(Boolean);
  if(!valid.length)return;

  const common=phoenixCommonAncestor(valid);
  const unsafe=common && (
    common===document.body ||
    common===document.documentElement ||
    common.querySelector("#stage,#meta,img,video,canvas,iframe")
  );

  if(common && !unsafe){
    common.dataset.phoenixEmbeddedHidden="1";
    common.style.display="none";
    return;
  }

  valid.forEach(n=>{
    n.dataset.phoenixEmbeddedHidden="1";
    n.style.display="none";
  });
}

function phoenixApplyEmbeddedUiConsolidation(){
  if(!phoenixEmbeddedMode)return false;

  document.documentElement.dataset.phoenixEmbedded="1";
  document.documentElement.style.overflow="hidden";
  if(document.body)document.body.style.overflow="hidden";

  const navButtons=[...document.querySelectorAll("button")].filter(button=>{
    const text=phoenixUiNorm(button.textContent);
    return (
      text.includes("vorige") ||
      text.includes("volgende") ||
      text.includes("presentatie") ||
      text.includes("vol scherm") ||
      text.includes("fullscreen")
    );
  });

  phoenixHideEmbeddedGroup(navButtons);

  const command=document.getElementById("command");
  const show=document.getElementById("show");
  phoenixHideEmbeddedGroup([command,show]);

  // Parent Phoenix owns the visible metadata line in embedded mode.
  // Keep this node alive as the authoritative state source for postMessage.
  if(meta){
    meta.dataset.phoenixEmbeddedMetaSource="1";
    meta.style.display="none";
  }

  return true;
}

if(phoenixEmbeddedMode){
  if(document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded",phoenixApplyEmbeddedUiConsolidation,{once:true});
  }else{
    phoenixApplyEmbeddedUiConsolidation();
  }
  window.addEventListener("load",phoenixApplyEmbeddedUiConsolidation,{once:true});
}
})();