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
 img.onload=()=>meta.textContent=`${i+1}/${items.length} · ${x.label}`;
 img.onerror=()=>{stage.textContent="MEDIA NIET BESCHIKBAAR";meta.textContent=x.file;};
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
})();