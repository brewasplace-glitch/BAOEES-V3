// PROJECT PHOENIX DE TV PROJECT-SCOPED SEMANTIC VISUAL ROUTING + QUALITY GATE v1.0
(() => {
  'use strict';
  const PROJECT_RE=/\bPHOENIX-PAT-\d+\b/i;
  let busy=false,lastKind=null,lastProject=null;

  const norm=s=>String(s||'').trim().replace(/\\/g,'/');
  function visible(el){ if(!el||!(el instanceof Element)) return false; const r=el.getBoundingClientRect(),s=getComputedStyle(el); return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'; }

  function activeProjectId(){
    const hits=[];
    document.querySelectorAll('select,input,[data-project-id],[data-project],[value]').forEach(el=>{
      if(el.closest&&el.closest('#projectList')) return;
      for(const raw of [el.dataset?.projectId,el.dataset?.project,el.value,el.getAttribute?.('value')]){
        const m=String(raw||'').match(PROJECT_RE); if(m) hits.push(m[0].toUpperCase());
      }
    });
    if(hits.length) return hits[hits.length-1];
    const c=[];
    document.querySelectorAll('body *').forEach(el=>{
      if(!visible(el) || (el.closest&&el.closest('#projectList'))) return;
      const t=(el.textContent||'').trim(),m=t.match(PROJECT_RE); if(!m) return;
      let score=t.length<80?10:0;
      const sig=((el.id||'')+' '+String(el.className||'')).toLowerCase();
      if(/progress|status|session|project/.test(sig)) score+=20;
      if(el.closest&&el.closest('.progresspanel')) score+=30;
      c.push({id:m[0].toUpperCase(),score});
    });
    c.sort((a,b)=>b.score-a.score);
    return c.length?c[0].id:null;
  }

  function semanticKind(q){
    q=norm(q).toLowerCase();
    if(/(3d\s*viewer|3d-viewer|viewer\s*3d|toon\s*3d)/i.test(q)) return 'viewer_3d';
    if(/(automatische?\s*(video|videopresentatie)|auto[_ -]?video|videopresentatie)/i.test(q)) return 'auto_video';
    if(/(situatie\s*tekening|situatietekening|site[_ -]?plan|terrein\s*tekening)/i.test(q)) return 'site_plan';
    return null;
  }

  function artifactFor(pid,kind,dxf=false){
    const base=`projects/runtime/${pid}`;
    if(kind==='viewer_3d') return `${base}/results/generated_visual_media/viewer_3d/phoenix_3d_viewer.html`;
    if(kind==='auto_video') return `${base}/results/generated_visual_media/auto_video/phoenix_automatic_video.avi`;
    if(kind==='site_plan') return `${base}/results/session_adapters/architecture/drawings/site_plan.${dxf?'dxf':'svg'}`;
    return null;
  }

  function gate(title,msg){
    const s=document.getElementById('phoenixTvStage'),m=document.getElementById('phoenixTvMeta');
    if(s) s.innerHTML=`<div style="padding:18px;color:#dceeff"><strong>${title}</strong><br>${msg}</div>`;
    if(m) m.textContent=`PROJECT-SCOPED QUALITY GATE · ${msg}`;
  }

  function submit(path){
    if(busy||!path) return;
    const i=document.getElementById('phoenixTvCommand'),b=document.getElementById('phoenixTvCommandGo');
    if(!i||!b) return;
    busy=true;i.value='toon '+path;
    setTimeout(()=>{ b.click(); setTimeout(()=>busy=false,600); },20);
  }

  document.addEventListener('click',ev=>{
    if(busy) return;
    const b=ev.target?.closest?.('#phoenixTvCommandGo'); if(!b) return;
    const i=document.getElementById('phoenixTvCommand'); if(!i) return;
    const kind=semanticKind(i.value); if(!kind) return;
    const pid=activeProjectId();
    ev.preventDefault();ev.stopImmediatePropagation();
    if(!pid){ gate('DE TV PROJECT-SCOPE GEBLOKKEERD','Actief project kon niet betrouwbaar worden vastgesteld; cross-project fallback is verboden.'); return; }
    lastKind=kind;lastProject=pid;submit(artifactFor(pid,kind,false));
  },true);

  function metaPath(){
    const m=document.getElementById('phoenixTvMeta'),t=norm(m?.textContent);
    const x=t.match(/projects\/runtime\/(PHOENIX-PAT-\d+)\/[^·\s]+/i);
    return x?{path:x[0],pid:x[1].toUpperCase()}:null;
  }

  function blankFraction(img){
    try{
      if(!img?.complete||!img.naturalWidth||!img.naturalHeight) return null;
      const w=Math.min(320,img.naturalWidth),h=Math.min(220,img.naturalHeight),c=document.createElement('canvas');
      c.width=w;c.height=h;const x=c.getContext('2d',{willReadFrequently:true});x.fillStyle='#fff';x.fillRect(0,0,w,h);x.drawImage(img,0,0,w,h);
      const d=x.getImageData(0,0,w,h).data;let ink=0,total=w*h;
      for(let k=0;k<d.length;k+=4){ if(d[k+3]>15&&(d[k]<235||d[k+1]<235||d[k+2]<235)) ink++; }
      return ink/total;
    }catch(_){ return null; }
  }

  function check(){
    if(!lastProject||busy) return;
    const mp=metaPath();
    if(mp&&mp.pid!==lastProject){
      gate('DE TV CROSS-PROJECT ROUTING GEBLOKKEERD',`Artifact ${mp.pid} geweigerd; actief project is ${lastProject}.`);
      setTimeout(()=>submit(artifactFor(lastProject,lastKind,false)),40);return;
    }
    if(lastKind==='site_plan'){
      const img=document.getElementById('phoenixTvStage')?.querySelector('img'); if(!img) return;
      const run=()=>{ const f=blankFraction(img); if(f!==null&&f<0.0035){ gate('SITUATIETEKENING KWALITEITSGATE',`SVG voor ${lastProject} is vrijwel blanco (${(f*100).toFixed(2)}% beeldinhoud). Project-eigen DXF wordt geopend.`); setTimeout(()=>submit(artifactFor(lastProject,'site_plan',true)),80); } };
      img.complete?setTimeout(run,80):img.addEventListener('load',()=>setTimeout(run,80),{once:true});
    }
  }

  const start=()=>{
    const o=new MutationObserver(check),s=document.getElementById('phoenixTvStage'),m=document.getElementById('phoenixTvMeta');
    if(s)o.observe(s,{childList:true,subtree:true,characterData:true,attributes:true});
    if(m)o.observe(m,{childList:true,subtree:true,characterData:true});
  };
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',start,{once:true}):start();
  window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0={activeProjectId,semanticKind,artifactFor};
})();
