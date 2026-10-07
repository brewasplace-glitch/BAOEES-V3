(()=>{"use strict";
const tech=new Set(["digital_twin","ai_agents","simulations","documents","reports","asset_management","dashboard"]);
let managementOpen=false;
const q=id=>document.getElementById(id);
function nav(m){return document.querySelector(`#leftNav .navbtn[data-module="${m}"]`)}
function cleanNav(){
 document.querySelectorAll("#leftNav .navbtn[data-module]").forEach(button=>{
  if(tech.has(String(button.dataset.module||""))){button.hidden = true;button.setAttribute("aria-hidden","true");}
 });
 const b=q("phoenixManageNav")||nav("settings");
 if(b){b.id="phoenixManageNav";b.hidden=false;b.removeAttribute("aria-hidden");}
}
function panelOf(id){const x=q(id);return x?x.closest(".panel"):null}
function simplify(){
 const reg=panelOf("projectList");
 if(reg){reg.classList.add("phoenix-r2-project-registry-hidden");reg.hidden=true;reg.setAttribute("aria-hidden","true");}
 const ac=document.querySelector('.modecard[data-mode="autonomous"]');
 const mp=ac?ac.closest(".panel"):null;
 if(mp){mp.classList.add("phoenix-r2-project-mode-hidden");mp.hidden=true;mp.setAttribute("aria-hidden","true");}
 const ps=q("projectSelect"),def=ps?ps.closest(".panel"):null,row=def?def.parentElement:null;
 if(row&&row.classList.contains("twocol"))row.classList.add("phoenix-r2-project-definition-wide");
 const center=document.querySelector(".center"),up=q("dropzone"),uprow=up?up.closest(".twocol"):null;
 if(center&&row&&uprow&&row!==uprow)center.insertBefore(row,uprow);
 if(center&&!q("phoenixR2FlowBanner")){
  const b=document.createElement("div");b.id="phoenixR2FlowBanner";b.className="phoenix-r2-flow-banner";
  b.innerHTML="<strong>Projectflow:</strong> Nieuw project &rarr; locatie &rarr; uploads &rarr; projectomschrijving &rarr; gewenste uitvoer &rarr; Start project";
  center.insertBefore(b,center.firstElementChild);
 }
}
function setManagement(open){
 managementOpen=!!open;document.body.classList.toggle("phoenix-management-open",managementOpen);
 [q("phoenixModulesPanel"),q("phoenixWorkflowsPanel"),q("phoenix-start-capability-drawer")].forEach(n=>{
  if(!n)return;n.hidden=!managementOpen;n.setAttribute("aria-hidden",managementOpen?"false":"true");if("open" in n)n.open=managementOpen;
 });
 const b=q("phoenixManageNav")||nav("settings");
 if(b){b.classList.toggle("active",managementOpen);b.setAttribute("aria-expanded",managementOpen?"true":"false");}
}
function bind(){
 const b=q("phoenixManageNav")||nav("settings");
 if(!b||b.dataset.phxR2==="1")return;
 b.dataset.phxR2="1";b.addEventListener("click",e=>{e.preventDefault();e.stopImmediatePropagation();setManagement(!managementOpen)},true);
}
function apply(){cleanNav();simplify();bind();setManagement(false);document.documentElement.setAttribute("data-phoenix-startscreen-consolidation","4.6.19-r2")}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",apply,{once:true});else apply();
new MutationObserver(()=>{cleanNav();const drawer=q("phoenix-start-capability-drawer");if(drawer){drawer.hidden = !managementOpen;drawer.setAttribute("aria-hidden",managementOpen?"false":"true")}}).observe(document.documentElement,{childList:true,subtree:true});
window.PHOENIX_STARTSCREEN_CONSOLIDATION=Object.freeze({version:"4.6.19-r2",openManagement:()=>setManagement(true),closeManagement:()=>setManagement(false)});
})();