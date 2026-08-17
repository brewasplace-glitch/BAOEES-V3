// PROJECT PHOENIX DE TV OPEN-SOURCE MEDIA PLAYER ENGINE v1.0
(()=>{"use strict";
function host(){
 return document.getElementById("phoenixTvStage") ||
        document.getElementById("phoenixTvOutput") ||
        document.querySelector("[data-phoenix-tv-stage]") ||
        document.querySelector(".phoenix-tv-stage") ||
        document.querySelector(".tv-stage");
}
function active(){
 const r=window.PHOENIX_TV_PROJECT_SCOPED_VISUAL_ROUTING_V1_0;
 try{return r&&typeof r.authoritativeActiveProjectId==="function"?r.authoritativeActiveProjectId():"PHOENIX-PAT-002";}
 catch(_){return "PHOENIX-PAT-002";}
}
function mount(){
 const h=host(); if(!h)return false;
 h.style.height="500px";h.style.maxHeight="calc(100vh - 360px)";h.style.minHeight="320px";h.style.visibility="";
 h.innerHTML="";
 const f=document.createElement("iframe");
 f.id="phoenixOpenSourceMediaPlayer";
 f.title="PHOENIX DE TV Open-Source Media Player";
 f.src=`http://127.0.0.1:8770/player/?project=${encodeURIComponent(active()||"PHOENIX-PAT-002")}`;
 f.style.cssText="width:100%;height:100%;border:0;background:#02070d;";
 h.appendChild(f);
 const st=document.getElementById("phoenixTvStatus");if(st)st.textContent="OPEN-SOURCE PLAYER";
 return true;
}
setTimeout(mount,250);
window.PHOENIX_DE_TV_OPEN_SOURCE_MEDIA_PLAYER_V1_0={mount,active};
})();