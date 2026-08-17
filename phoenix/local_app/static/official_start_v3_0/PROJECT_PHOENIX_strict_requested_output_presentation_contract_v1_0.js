// PROJECT PHOENIX STRICT REQUESTED OUTPUT PRESENTATION CONTRACT v1.0
(()=>{"use strict";
const MAP=[
 {id:"viewer_3d",rx:/\b3d\s*viewer\b/i,label:"3D Viewer",path:p=>`projects/runtime/${p}/results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html`},
 {id:"walkthrough",rx:/walk[\s-]*through/i,label:"Walk-through",path:p=>`projects/runtime/${p}/results/generated_visual_media/walkthrough/phoenix_walkthrough.html`},
 {id:"drivethrough",rx:/drive[\s-]*through/i,label:"Drive-through",path:p=>`projects/runtime/${p}/results/generated_visual_media/drivethrough/phoenix_drivethrough.html`},
 {id:"bird_view",rx:/(vogelvlucht|bird[\s_-]*view)/i,label:"Vogelvlucht",path:p=>`projects/runtime/${p}/results/generated_visual_media/bird_view/phoenix_bird_view.html`},
 {id:"auto_video",rx:/(automatische\s*videopresentatie|auto[\s_-]*video)/i,label:"Automatische videopresentatie",path:p=>`projects/runtime/${p}/results/generated_visual_media/auto_video/phoenix_auto_video_presentation.html`}
];
let list=[],pos=0,busy=false;
function router(){return window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0||null}
function pid(){const r=router();return r&&typeof r.authoritativeActiveProjectId==="function"?r.authoritativeActiveProjectId():null}
function checkedOutputs(){
 const out=[];
 document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb=>{
   let n=cb,txt="";
   for(let i=0;i<4&&n;i++,n=n.parentElement)txt+=" "+(n.innerText||n.textContent||"");
   for(const m of MAP)if(m.rx.test(txt)&&!out.some(x=>x.id===m.id))out.push(m);
 });
 return out;
}
function status(){
 const meta=document.getElementById("phoenixTvMeta");
 if(meta&&list.length)meta.textContent=`${pos+1}/${list.length} · ${list[pos].label} · ${list[pos].path}`;
}
async function openAt(i){
 if(busy||!list.length)return;busy=true;pos=(i+list.length)%list.length;
 const r=router();if(!r||typeof r.seekExactArtifact!=="function"){busy=false;return}
 const ok=await r.seekExactArtifact(list[pos].path);if(ok)status();busy=false;
}
function build(){
 const p=pid();if(!p)return false;
 const selected=checkedOutputs();
 list=selected.map(m=>({id:m.id,label:m.label,path:m.path(p),project:p}));
 pos=0;
 if(!list.length)return false;
 openAt(0);return true;
}
document.addEventListener("click",e=>{
 const b=e.target?.closest?.("button");if(!b)return;
 if(b.id==="phoenixTvSelected"){e.preventDefault();e.stopImmediatePropagation();build();return}
 if(!list.length)return;
 if(b.id==="phoenixTvNext"){e.preventDefault();e.stopImmediatePropagation();openAt(pos+1);return}
 if(b.id==="phoenixTvPrev"){e.preventDefault();e.stopImmediatePropagation();openAt(pos-1);return}
},true);
window.PHOENIX_STRICT_PRESENTATION_V1_0={checkedOutputs,build,getPlaylist:()=>list.slice()};
})();