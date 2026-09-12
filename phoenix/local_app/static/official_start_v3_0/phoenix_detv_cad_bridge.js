(() => {
"use strict";
if (window.__PHOENIX_DETV_CAD_NATIVE_V441__) return;
window.__PHOENIX_DETV_CAD_NATIVE_V441__=true;
window.__PHOENIX_DETV_CAD_HARD_MOUNT_V1__=true;

const SIDECAR="http://127.0.0.1:8765";
const SUSPICIOUS=/Ã|Â|ðŸ|â€|âœ|â˜|âš|â†|â‡|âŒ|â”|â–|â—|ï¸|�/;

function cp1252Byte(ch){
  const c=ch.codePointAt(0);
  const inv={
    0x20AC:0x80,0x201A:0x82,0x0192:0x83,0x201E:0x84,0x2026:0x85,
    0x2020:0x86,0x2021:0x87,0x02C6:0x88,0x2030:0x89,0x0160:0x8A,
    0x2039:0x8B,0x0152:0x8C,0x017D:0x8E,0x2018:0x91,0x2019:0x92,
    0x201C:0x93,0x201D:0x94,0x2022:0x95,0x2013:0x96,0x2014:0x97,
    0x02DC:0x98,0x2122:0x99,0x0161:0x9A,0x203A:0x9B,0x0153:0x9C,
    0x017E:0x9E,0x0178:0x9F
  };
  if(inv[c]!==undefined)return inv[c];
  return c<=255?c:null;
}
function decodeCp1252Utf8(text){
  const bytes=[];
  for(const ch of text){
    const b=cp1252Byte(ch);
    if(b===null)return text;
    bytes.push(b);
  }
  try{return new TextDecoder("utf-8",{fatal:true}).decode(new Uint8Array(bytes))}
  catch(_){return text}
}
function cleanText(text){
  if(!text||!SUSPICIOUS.test(text))return text;
  let out=decodeCp1252Utf8(text);
  if(out!==text)return out;

  // If an already-damaged icon prefix is incomplete and cannot be recovered,
  // remove only the short mojibake prefix before a readable label.
  out=text.replace(
    /^\s*(?:Ã.|Â.|ð\S{0,7}|â\S{0,7}|ï\S{0,5}|�+)\s+(?=[A-Za-zÀ-ÿ])/,
    ""
  );
  return out;
}
function repairNode(node){
  if(node.nodeType===Node.TEXT_NODE){
    const fixed=cleanText(node.nodeValue);
    if(fixed!==node.nodeValue)node.nodeValue=fixed;
    return;
  }
  if(node.nodeType!==Node.ELEMENT_NODE)return;
  if(["SCRIPT","STYLE","TEXTAREA","IFRAME"].includes(node.tagName))return;
  const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);
  let n; while((n=walker.nextNode()))repairNode(n);
}
function repairDocumentText(){repairNode(document.body)}
window.repairDocumentText=repairDocumentText;

function syncRuntimeVersionText(root=document.body){
  if(!root)return;
  const repair=node=>{
    if(node.nodeType!==Node.TEXT_NODE)return;
    const before=node.nodeValue||"";
    const after=before
      .replace(/START\s+v3\.0\.2/g,"START v4.41")
      .replace(/START\s+v3\.0(?!\d)/g,"START v4.41");
    if(after!==before)node.nodeValue=after;
  };
  if(root.nodeType===Node.TEXT_NODE){repair(root);return}
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  let node;
  while((node=walker.nextNode()))repair(node);
}
window.syncRuntimeVersionText=syncRuntimeVersionText;

const style=document.createElement("style");
style.textContent=`
#phoenix-cad-toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 8px 10px;padding:8px;border-top:1px solid rgba(120,170,220,.22);position:static!important;right:auto!important;bottom:auto!important;z-index:auto!important}
#phoenix-cad-toolbar button{border:1px solid #28567c;border-radius:8px;padding:8px 12px;cursor:pointer;font-weight:700;background:#0d2a42;color:#eaf6ff}
#phoenix-cad-toolbar button:hover{background:#123a59}
#phoenix-cad-status-dot{width:8px;height:8px;border-radius:50%;display:inline-block;background:#888;margin-right:6px}
#phoenix-cad-detv-mount{position:absolute;inset:0;z-index:40;background:#071019;overflow:hidden;border-radius:inherit;min-height:150px}
#phoenix-cad-frame{width:100%;height:100%;border:0;background:#0b1118;display:block}
#phoenix-cad-mount-close{position:absolute;right:7px;top:7px;z-index:45;border-radius:999px;border:1px solid rgba(255,255,255,.28);width:30px;height:30px;background:#101c29;color:#fff;cursor:pointer;font-size:18px;line-height:26px;padding:0}
#phoenix-cad-mount-state{position:absolute;left:8px;top:8px;z-index:44;padding:4px 7px;border-radius:6px;background:rgba(3,12,20,.82);color:#a9d8ff;font:600 11px/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;pointer-events:none}
#phoenix-cad-detv-mount[data-ready="1"] #phoenix-cad-mount-state{opacity:.18}
#phoenix-cad-detv-mount[data-ready="1"]:hover #phoenix-cad-mount-state{opacity:1}`;
document.head.appendChild(style);

function exactText(el,text){
  return (el.textContent||"").trim().replace(/\s+/g," ")===text;
}
function findDeTvAnchor(){
  const nodes=[...document.querySelectorAll("h1,h2,h3,h4,strong,span,div")];
  return nodes.find(el=>exactText(el,"DE TV"))||null;
}
function findDeTvPanel(){
  const anchor=findDeTvAnchor();
  if(!anchor)return null;
  let cur=anchor;
  for(let i=0;i<7&&cur;i++,cur=cur.parentElement){
    const r=cur.getBoundingClientRect();
    const txt=(cur.textContent||"");
    if(r.width>=250&&r.height>=220&&txt.includes("DE TV"))return cur;
  }
  return anchor.parentElement;
}
function resolveProjectHint(){
  const g=[window.PHOENIX_ACTIVE_PROJECT_ID,window.__PHOENIX_ACTIVE_PROJECT_ID__,window.activeProjectId,window.currentProjectId].filter(Boolean);
  if(g.length)return String(g[0]);
  try{
    for(let i=0;i<localStorage.length;i++){
      const k=localStorage.key(i);
      if(!k||!/active.*project|project.*active|current.*project/i.test(k))continue;
      const v=localStorage.getItem(k); if(!v)continue;
      try{
        const o=JSON.parse(v);
        for(const key of ["project_id","projectId","id","slug","name"]){
          if(o&&o[key])return String(o[key]);
        }
      }catch(_){if(v.length<160)return v}
    }
  }catch(_){}
  return "";
}

let frame=null,hidden=null,dot=null,mount=null,pendingFile=null,viewerReady=false;
let mountHost=null,mountState=null;
window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__={
  protocol:"v1",mode:"IDLE",viewerReady:false,lastFile:"",lastResult:"",mountTarget:""
};

function findDeTvViewport(panel){
  if(!panel)return null;
  const candidates=[...panel.querySelectorAll("div,section,main,article")].filter(el=>{
    if(el.id==="phoenix-cad-toolbar"||el.closest("#phoenix-cad-toolbar"))return false;
    const r=el.getBoundingClientRect();
    if(r.width<240||r.height<120)return false;
    const text=(el.textContent||"").replace(/\s+/g," ").trim();
    return text.includes("Selecteer output")&&text.includes("DE TV");
  });
  candidates.sort((a,b)=>{
    const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
    return (ar.width*ar.height)-(br.width*br.height);
  });
  if(candidates.length)return candidates[0];

  const dark=[...panel.querySelectorAll("div,section,main,article")].filter(el=>{
    if(el.id==="phoenix-cad-toolbar"||el.closest("#phoenix-cad-toolbar"))return false;
    const r=el.getBoundingClientRect();
    if(r.width<240||r.height<120)return false;
    const bg=getComputedStyle(el).backgroundColor;
    const nums=(bg.match(/\d+/g)||[]).map(Number);
    return nums.length>=3&&nums[0]<35&&nums[1]<40&&nums[2]<45;
  });
  dark.sort((a,b)=>{
    const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
    return (ar.width*ar.height)-(br.width*br.height);
  });
  return dark[0]||null;
}

function removeCadMount(){
  if(mount&&mount.isConnected)mount.remove();
  mount=null;frame=null;mountState=null;pendingFile=null;viewerReady=false;mountHost=null;
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.mode="IDLE";
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.viewerReady=false;
}

function ensureHardMount(){
  const panel=findDeTvPanel();
  if(!panel)throw new Error("DE TV panel niet gevonden");
  let target=findDeTvViewport(panel);
  let targetKind="DE_TV_VIEWPORT";
  if(!target){target=panel;targetKind="DE_TV_PANEL_FALLBACK"}

  if(mount&&mount.isConnected&&mountHost===target)return mount;
  removeCadMount();

  const position=getComputedStyle(target).position;
  if(position==="static"||!position)target.style.position="relative";
  target.style.overflow="hidden";

  mount=document.createElement("div");
  mount.id="phoenix-cad-detv-mount";
  mount.dataset.ready="0";
  mount.dataset.mountTarget=targetKind;
  mount.innerHTML='<div id="phoenix-cad-mount-state">CAD VIEWER STARTEN…</div><button id="phoenix-cad-mount-close" title="Terug naar DE TV">×</button><iframe id="phoenix-cad-frame" title="PHOENIX DE TV Embedded CAD Viewer"></iframe>';
  target.appendChild(mount);

  mountHost=target;
  frame=mount.querySelector("#phoenix-cad-frame");
  mountState=mount.querySelector("#phoenix-cad-mount-state");
  mount.querySelector("#phoenix-cad-mount-close").onclick=removeCadMount;
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.mountTarget=targetKind;
  return mount;
}

function updateMountState(text){
  if(mountState)mountState.textContent=text;
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.lastResult=text;
}

function sendPendingFile(){
  if(!viewerReady||!pendingFile||!frame||!frame.contentWindow)return false;
  updateMountState(`DXF/DWG LADEN · ${pendingFile.name}`);
  frame.contentWindow.postMessage(
    {type:"phoenix-cad-file",protocol:"v1",file:pendingFile},
    SIDECAR
  );
  return true;
}

function hardMountViewer(mode,file){
  ensureHardMount();
  pendingFile=file||null;
  viewerReady=false;
  mount.dataset.ready="0";
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.mode=mode;
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.viewerReady=false;
  window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.lastFile=file?file.name:"";
  updateMountState(file?`VIEWER STARTEN · ${file.name}`:"VIEWER STARTEN");
  frame.src=`${SIDECAR}/viewer?mode=${encodeURIComponent(mode)}&compact=1&hardmount=1&project_hint=${encodeURIComponent(resolveProjectHint())}`;
}

function installNativeControls(){
  const old=document.getElementById("phoenix-cad-toolbar");
  if(old&&old.dataset.native==="1")return true;
  if(old)old.remove();

  const panel=findDeTvPanel();
  if(!panel)return false;

  const toolbar=document.createElement("div");
  toolbar.id="phoenix-cad-toolbar";toolbar.dataset.native="1";toolbar.dataset.integration="DETV_NATIVE_CAD_CONTROLS";
  const project=document.createElement("button");project.type="button";project.innerHTML='<span id="phoenix-cad-status-dot"></span>Project CAD';
  const open=document.createElement("button");open.type="button";open.textContent="Open CAD bestand…";
  hidden=document.createElement("input");hidden.type="file";hidden.accept=".dxf,.dwg";hidden.style.display="none";

  toolbar.append(project,open,hidden);
  panel.appendChild(toolbar);
  dot=project.querySelector("#phoenix-cad-status-dot");
  project.onclick=()=>hardMountViewer("project");
  open.onclick=()=>{hidden.value="";hidden.click()};
  hidden.onchange=()=>{
    const f=hidden.files&&hidden.files[0];
    if(!f)return;
    if(!/\.(dxf|dwg)$/i.test(f.name)){alert("Kies een DXF- of DWG-bestand.");return}
    hardMountViewer("handoff",f);
  };
  return true;
}
window.addEventListener("message",event=>{
  if(event.origin!==SIDECAR)return;
  if(!frame||event.source!==frame.contentWindow)return;
  const data=event.data||{};
  if(data.type==="phoenix-cad-viewer-ready"){
    viewerReady=true;
    if(mount)mount.dataset.ready="1";
    window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.viewerReady=true;
    updateMountState("CAD VIEWER GEREED");
    sendPendingFile();
    return;
  }
  if(data.type==="phoenix-cad-file-loaded"){
    updateMountState(`${data.name||"CAD"} · ${data.embedded_status||"PASS"}`);
    window.__PHOENIX_DETV_CAD_HARD_MOUNT_STATUS__.lastFile=data.name||"";
    return;
  }
  if(data.type==="phoenix-cad-file-error"){
    updateMountState(`CAD FOUT · ${data.error||"onbekend"}`);
    return;
  }
  if(data.type==="phoenix-cad-project-loaded"){
    updateMountState(`PROJECT CAD · ${data.count||0} bestand(en)`);
  }
});

async function health(){
  try{
    const r=await fetch(`${SIDECAR}/health`,{cache:"no-store",mode:"cors"});
    if(!r.ok)throw new Error(`CAD sidecar HTTP ${r.status}`);
    const j=await r.json();
    const ok=j.status==="PASS"&&j.service==="PHOENIX_DETV_CAD_SIDECAR";
    if(dot){
      dot.style.background=ok?"#2ecc71":"#f39c12";
      dot.title=ok?`CAD sidecar ${j.version||""} connected`:"CAD sidecar unhealthy";
    }
    return ok;
  }catch(err){
    if(dot){
      dot.style.background="#e74c3c";
      dot.title=`CAD sidecar browser health failed: ${err.message||err}`;
    }
    return false;
  }
}
function activate(){
  repairDocumentText();
  syncRuntimeVersionText(document.body);
  installNativeControls();
  health();
}
activate();
let scheduled=false;
const observer=new MutationObserver(()=>{
  if(scheduled)return;
  scheduled=true;
  setTimeout(()=>{scheduled=false;activate()},80);
});
observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
setInterval(health,15000);
document.addEventListener("keydown",e=>{
  if(e.key==="Escape"&&mount&&mount.isConnected)removeCadMount();
});
})();

// DETV_HARD_MOUNT_CAD_VIEWER_PROTOCOL=v1
