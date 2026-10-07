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

// PHOENIX_4_6_19_R3_FINAL_USER_UI_POLISH
function r3FixRuntimeVersion(){
 const el=q("runtimeState");
 if(!el)return;
 const text=String(el.textContent||"");
 if(text.includes("START v4.41")) el.textContent=text.replace("START v4.41","START v4.6.19");
}
function r3CompactTvTitle(){
 const title=document.querySelector("#phoenixTvPanel .tvtitle");
 if(!title)return;
 const spans=title.querySelectorAll("span");
 if(spans.length>=2)spans[1].textContent="DE TV";
 let context=title.querySelector(".tvtitle-context");
 if(!context){
  context=document.createElement("span");
  context.className="tvtitle-context";
  title.appendChild(context);
 }
 context.textContent=" / DIGITAL TWIN / RESULTATEN";
}
function r3MoveEngineeringControlsToManagement(){
 const toolbar=q("phoenix-material-mode-toolbar");
 const modules=q("phoenixModulesPanel");
 const body=modules?modules.querySelector(".phoenix-modules-body"):null;
 if(toolbar&&body&&toolbar.parentElement!==body){
  body.insertBefore(toolbar,body.firstChild);
  toolbar.setAttribute("data-phoenix-management-only","true");
 }
}
function r3HideAutonomousFlowDuplicate(){
 document.querySelectorAll("button").forEach(button=>{
  const t=String(button.textContent||"").trim().toUpperCase();
  if(t==="AUTONOME PHOENIX-FLOW"){
   button.classList.add("phoenix-r3-autonomous-flow-duplicate");
   button.hidden=true;
   button.setAttribute("aria-hidden","true");
  }
 });
}
function r3CollapseOutputLevel(){
 const panels=Array.from(document.querySelectorAll(".panel"));
 const panel=panels.find(p=>String(p.textContent||"").includes("OUTPUTNIVEAU PROJECT"));
 if(!panel||q("phoenixR3OutputLevelToggle"))return;
 const toggle=document.createElement("button");
 toggle.id="phoenixR3OutputLevelToggle";
 toggle.type="button";
 toggle.className="phoenix-r3-advanced-toggle";
 toggle.textContent="Uitvoeringsniveau: A - Professionele projectoutput (geavanceerde opties)";
 panel.parentElement.insertBefore(toggle,panel);
 panel.classList.add("phoenix-r3-advanced-hidden");
 panel.hidden=true;
 toggle.setAttribute("aria-expanded","false");
 toggle.addEventListener("click",()=>{
  const open=panel.hidden;
  panel.hidden=!open;
  panel.classList.toggle("phoenix-r3-advanced-hidden",!open);
  toggle.setAttribute("aria-expanded",open?"true":"false");
 });
}
function r3CollapseDesiredOutputs(){
 const groups=q("desiredOutputGroups");
 if(!groups||q("phoenixR3OutputToggle"))return;
 const panel=groups.closest(".panel");
 if(!panel)return;
 const toolbar=panel.querySelector(".outputtoolbar");
 const toggle=document.createElement("button");
 toggle.id="phoenixR3OutputToggle";
 toggle.type="button";
 toggle.className="phoenix-r3-output-toggle";
 toggle.textContent="UITVOERLIJST TONEN";
 groups.classList.add("phoenix-r3-output-collapsed");
 groups.hidden=true;
 toggle.setAttribute("aria-expanded","false");
 if(toolbar)toolbar.appendChild(toggle);else panel.insertBefore(toggle,groups);
 toggle.addEventListener("click",()=>{
  const open=groups.hidden;
  groups.hidden=!open;
  groups.classList.toggle("phoenix-r3-output-collapsed",!open);
  toggle.textContent=open?"UITVOERLIJST VERBERGEN":"UITVOERLIJST TONEN";
  toggle.setAttribute("aria-expanded",open?"true":"false");
 });
}
function r3RemoveDuplicateResultsButton(){
 const button=q("resultsBtn");
 if(!button)return;
 button.classList.add("phoenix-r3-duplicate-results");
 button.hidden=true;
 button.setAttribute("aria-hidden","true");
}
function r3SuppressStaleSession(){
 const start=q("startBtn");
 const progress=q("progressLabel");
 const percent=q("progressPercent");
 const step=q("progressStep");
 const track=document.querySelector(".progresstrack");
 const meta=document.querySelector(".progressmeta");
 const project=q("projectSelect");
 if(!start||!progress||!percent||!step)return;
 const stale=(String(progress.textContent||"").includes("Phoenix Autonome Sessiestuurde Orchestrator")||
              String(step.textContent||"").includes("Generic Sessieadapters")||
              String(step.textContent||"").includes("PHOENIX-PAT-003"));
 const noProject=!project||!String(project.value||"").trim();
 if(stale&&noProject){
  [meta,track,step].forEach(n=>{if(n)n.classList.add("phoenix-r3-session-hidden")});
 }
 if(start.dataset.phxR3SessionBound!=="1"){
  start.dataset.phxR3SessionBound="1";
  start.addEventListener("click",()=>{
   [meta,track,step].forEach(n=>{if(n)n.classList.remove("phoenix-r3-session-hidden")});
  },true);
 }
}
function r3Apply(){
 r3FixRuntimeVersion();
 r3CompactTvTitle();
 r3MoveEngineeringControlsToManagement();
 r3HideAutonomousFlowDuplicate();
 r3CollapseOutputLevel();
 r3CollapseDesiredOutputs();
 r3RemoveDuplicateResultsButton();
 r3SuppressStaleSession();
 document.documentElement.setAttribute("data-phoenix-startscreen-polish","4.6.19-r3");
}
if(document.readyState==="loading"){
 document.addEventListener("DOMContentLoaded",r3Apply,{once:true});
}else{
 r3Apply();
}
new MutationObserver(()=>{
 r3FixRuntimeVersion();
 r3MoveEngineeringControlsToManagement();
 r3HideAutonomousFlowDuplicate();
}).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
window.PHOENIX_STARTSCREEN_CONSOLIDATION=Object.freeze({version:"4.6.19-r3",openManagement:()=>setManagement(true),closeManagement:()=>setManagement(false)});
})();