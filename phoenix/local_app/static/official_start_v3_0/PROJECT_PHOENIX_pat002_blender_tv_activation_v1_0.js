// PROJECT PHOENIX PAT-002 REAL IFC -> BLENDER -> DE TV ACTIVATION v1.0
(()=>{"use strict";

const MAP = [
  {rx:/^(toon\s+)?(ontwerp|exterieur|variant\s*b|3d)$/i, file:"phoenix_exterior_front.png", label:"PAT-002 EXTERIEUR"},
  {rx:/^(toon\s+)?interieur$/i, file:"phoenix_interior_cutaway.png", label:"PAT-002 INTERIEUR CUTAWAY"},
  {rx:/^(toon\s+)?(vogelvlucht|bird\s*view)$/i, file:"phoenix_bird_view.png", label:"PAT-002 VOGELVLUCHT"},
  {rx:/^(toon\s+)?(achtergevel|rear|achterzijde)$/i, file:"phoenix_exterior_rear.png", label:"PAT-002 ACHTERZIJDE"},
];

function router(){
  return window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0 || null;
}
function activeProject(){
  const r=router();
  return r && typeof r.authoritativeActiveProjectId==="function" ? r.authoritativeActiveProjectId() : null;
}
function normalize(s){
  return String(s||"").trim().toLowerCase().replace(/\s+/g," ");
}
function matchCommand(raw){
  const cmd=normalize(raw);
  for(const m of MAP){
    if(m.rx.test(cmd)) return m;
  }
  return null;
}
async function openVisual(match){
  const pid=activeProject();
  if(pid!=="PHOENIX-PAT-002") return false;

  const r=router();
  if(!r || typeof r.seekExactArtifact!=="function") return false;

  const path=`projects/runtime/${pid}/results/generated_visual_media/blender_presentation/${match.file}`;
  const ok=await r.seekExactArtifact(path);
  if(ok){
    const meta=document.getElementById("phoenixTvMeta");
    const status=document.getElementById("phoenixTvStatus");
    if(meta) meta.textContent=`${match.label} · ${pid} · IFC → Blender`;
    if(status) status.textContent="GEREED";
    return true;
  }
  return false;
}
async function executeFromInput(){
  const input=document.getElementById("phoenixTvCommand");
  if(!input) return false;
  const m=matchCommand(input.value);
  if(!m) return false;
  return openVisual(m);
}

document.addEventListener("click", async e=>{
  const b=e.target && e.target.closest ? e.target.closest("button") : null;
  if(!b || b.id!=="phoenixTvCommandGo") return;
  const input=document.getElementById("phoenixTvCommand");
  const m=input ? matchCommand(input.value) : null;
  if(!m) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  await openVisual(m);
}, true);

document.addEventListener("keydown", async e=>{
  if(e.key!=="Enter") return;
  if(!e.target || e.target.id!=="phoenixTvCommand") return;
  const m=matchCommand(e.target.value);
  if(!m) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  await openVisual(m);
}, true);

window.PHOENIX_PAT002_BLENDER_TV_V1_0={
  normalize,
  matchCommand,
  activeProject,
  openVisual,
  executeFromInput
};
})();