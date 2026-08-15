// PROJECT PHOENIX DE TV VISUAL ARTIFACT ROUTING v1.0
(()=>{"use strict";
const V=/\.(svg|png|jpe?g|webp|dxf|dwg|html?|gltf|glb|webm|mp4|mov|avi|pdf)$/i;
const T=/\.(jsonl?|log|txt|md)$/i,N=/(manifest|register|evidence|metadata|contract|state|summary|index)/i;
const vis=p=>V.test(String(p||"").trim()), tech=p=>{p=String(p||"").trim();return T.test(p)||(N.test(p)&&!vis(p))};
function parse(t){t=String(t||"").trim();if(!t.startsWith("{"))return null;try{const o=JSON.parse(t),c=[];["artifact","file","path","output","viewer","video"].forEach(k=>typeof o[k]==="string"&&c.push(o[k]));Array.isArray(o.evidence)&&o.evidence.forEach(x=>typeof x==="string"&&c.push(x));return c.find(vis)||null}catch(e){return null}}
function sibling(meta,a){meta=String(meta||"").replace(/\\/g,"/");const m=meta.match(/(?:^|·)\s*(projects\/runtime\/[^·]+|outputs\/[^·]+)\s*$/i);if(!m||a.includes("/"))return a;const p=m[1].trim(),i=p.lastIndexOf("/");return (i>=0?p.slice(0,i+1):"")+a}
function go(path){const i=document.getElementById("phoenixTvCommand"),b=document.getElementById("phoenixTvCommandGo");if(!i||!b||!path)return;i.value="toon "+path;setTimeout(()=>b.click(),20)}
function repair(){const s=document.getElementById("phoenixTvStage"),m=document.getElementById("phoenixTvMeta");if(!s)return;const a=parse(s.textContent);if(a&&!tech(a))go(sibling(m?m.textContent:"",a))}
function start(){const s=document.getElementById("phoenixTvStage");if(!s)return;new MutationObserver(repair).observe(s,{childList:true,subtree:true,characterData:true});repair()}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{once:true}):start();
window.PHOENIX_TV_VISUAL_ROUTING_V1_0={vis,tech,parse};
})();