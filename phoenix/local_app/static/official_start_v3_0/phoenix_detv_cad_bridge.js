(() => {
"use strict";
if (window.__PHOENIX_DETV_CAD_BRIDGE_V1__) return;
window.__PHOENIX_DETV_CAD_BRIDGE_V1__=true;
const SIDECAR="http://127.0.0.1:8765";
const style=document.createElement("style");
style.textContent=`
#phoenix-cad-toolbar{position:fixed;right:18px;bottom:18px;z-index:2147483000;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
#phoenix-cad-toolbar button{border:1px solid rgba(255,255,255,.25);border-radius:10px;padding:10px 14px;cursor:pointer;font-weight:650;box-shadow:0 8px 28px rgba(0,0,0,.28);background:#17202a;color:#fff}
#phoenix-cad-modal{position:fixed;inset:0;z-index:2147483100;background:rgba(0,0,0,.72);display:none;align-items:center;justify-content:center;padding:20px}
#phoenix-cad-modal.open{display:flex}
#phoenix-cad-shell{width:min(1500px,96vw);height:min(920px,94vh);border-radius:14px;overflow:hidden;background:#0d1117;box-shadow:0 24px 80px rgba(0,0,0,.55);border:1px solid rgba(255,255,255,.15);position:relative}
#phoenix-cad-frame{width:100%;height:100%;border:0;background:#fff}
#phoenix-cad-close{position:absolute;right:10px;top:10px;z-index:3;border-radius:999px;border:0;width:38px;height:38px;background:#111827;color:#fff;cursor:pointer;font-size:20px}
#phoenix-cad-status-dot{width:9px;height:9px;border-radius:50%;display:inline-block;background:#888;margin-right:7px}`;
document.head.appendChild(style);

const toolbar=document.createElement("div"); toolbar.id="phoenix-cad-toolbar";
const projectBtn=document.createElement("button"); projectBtn.type="button"; projectBtn.innerHTML='<span id="phoenix-cad-status-dot"></span>Project CAD';
const openBtn=document.createElement("button"); openBtn.type="button"; openBtn.textContent="Open CAD bestand…";
const hidden=document.createElement("input"); hidden.type="file"; hidden.accept=".dxf,.dwg"; hidden.style.display="none";
toolbar.append(projectBtn,openBtn,hidden); document.body.appendChild(toolbar);

const modal=document.createElement("div"); modal.id="phoenix-cad-modal";
modal.innerHTML='<div id="phoenix-cad-shell"><button id="phoenix-cad-close" title="Sluiten">×</button><iframe id="phoenix-cad-frame" title="PHOENIX DE TV CAD Viewer"></iframe></div>';
document.body.appendChild(modal);
const frame=modal.querySelector("#phoenix-cad-frame"), close=modal.querySelector("#phoenix-cad-close"), dot=projectBtn.querySelector("#phoenix-cad-status-dot");

function resolveProjectHint(){
  const g=[window.PHOENIX_ACTIVE_PROJECT_ID,window.__PHOENIX_ACTIVE_PROJECT_ID__,window.activeProjectId,window.currentProjectId].filter(Boolean);
  if(g.length)return String(g[0]);
  try{
    for(let i=0;i<localStorage.length;i++){
      const k=localStorage.key(i); if(!k||!/active.*project|project.*active|current.*project/i.test(k))continue;
      const v=localStorage.getItem(k); if(!v)continue;
      try{const o=JSON.parse(v); for(const key of ["project_id","projectId","id","slug","name"])if(o&&o[key])return String(o[key]);}
      catch(_){if(v.length<160)return v;}
    }
  }catch(_){}
  return "";
}
function openModal(mode,file){
  modal.classList.add("open");
  frame.src=`${SIDECAR}/viewer?mode=${encodeURIComponent(mode)}&project_hint=${encodeURIComponent(resolveProjectHint())}`;
  if(file){
    frame.addEventListener("load",()=>setTimeout(()=>frame.contentWindow.postMessage({type:"phoenix-cad-file",file},SIDECAR),120),{once:true});
  }
}
projectBtn.onclick=()=>openModal("project");
openBtn.onclick=()=>{hidden.value="";hidden.click();};
hidden.onchange=()=>{const f=hidden.files&&hidden.files[0]; if(!f)return; if(!/\.(dxf|dwg)$/i.test(f.name)){alert("Kies een DXF- of DWG-bestand.");return;} openModal("handoff",f);};
close.onclick=()=>{modal.classList.remove("open");frame.src="about:blank";};
modal.onclick=e=>{if(e.target===modal)close.click();};
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&modal.classList.contains("open"))close.click();});
async function health(){try{const r=await fetch(`${SIDECAR}/health`,{cache:"no-store"});const j=await r.json();dot.style.background=j.status==="PASS"?"#2ecc71":"#f39c12";}catch(_){dot.style.background="#e74c3c";}}
health(); setInterval(health,15000);
})();
