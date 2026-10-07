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
 if(!panel)return;
 let toggle=q("phoenixR3OutputLevelToggle");
 if(!toggle){
  toggle=document.createElement("button");
  toggle.id="phoenixR3OutputLevelToggle";
  toggle.type="button";
  toggle.className="phoenix-r3-advanced-toggle";
  toggle.textContent="Uitvoeringsniveau: A - Professionele projectoutput";
  panel.parentElement.insertBefore(toggle,panel);
  toggle.addEventListener("click",()=>{
   const open=panel.hidden;
   panel.hidden=!open;
   panel.classList.toggle("phoenix-r3-advanced-hidden",!open);
   toggle.setAttribute("aria-expanded",open?"true":"false");
   toggle.textContent=open
    ?"Uitvoeringsniveau verbergen"
    :"Uitvoeringsniveau: A - Professionele projectoutput";
  });
 }
 panel.hidden=true;
 panel.classList.add("phoenix-r3-advanced-hidden");
 panel.setAttribute("aria-hidden","true");
 toggle.setAttribute("aria-expanded","false");
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

 const projectValue=project?String(project.value||"").trim():"";
 const projectText=project&&project.options&&project.selectedIndex>=0
  ?String(project.options[project.selectedIndex].text||"").trim()
  :"";

 const newProjectSelected=(
  !projectValue ||
  projectValue.toLowerCase()==="new" ||
  projectText.toLowerCase().includes("nieuw / geen bestaand project gekozen") ||
  projectText.toLowerCase().includes("geen bestaand project")
 );

 const stale=(
  String(progress.textContent||"").includes("Phoenix Autonome Sessiestuurde Orchestrator") ||
  String(progress.textContent||"").includes("PHOENIX-PAT-003") ||
  String(step.textContent||"").includes("Generic Sessieadapters") ||
  String(step.textContent||"").includes("PHOENIX-PAT-003")
 );

 if(stale&&newProjectSelected){
  [meta,track,step].forEach(n=>{
   if(n){
    n.classList.add("phoenix-r3-session-hidden");
    n.hidden=true;
    n.setAttribute("aria-hidden","true");
   }
  });
 }

 if(start.dataset.phxR31SessionBound!=="1"){
  start.dataset.phxR31SessionBound="1";
  start.addEventListener("click",()=>{
   [meta,track,step].forEach(n=>{
    if(n){
     n.classList.remove("phoenix-r3-session-hidden");
     n.hidden=false;
     n.removeAttribute("aria-hidden");
    }
   });
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

// PHOENIX_4_6_19_R3_2_LIVE_UI_ENFORCEMENT
let r32UserOpenedOutputLevel=false;
let r32ProjectRunStarted=false;
let r32EnforceTimer=null;

function r32GetOutputLevelPanel(){
 const panels=Array.from(document.querySelectorAll(".panel"));
 return panels.find(p=>String(p.textContent||"").includes("OUTPUTNIVEAU PROJECT"))||null;
}

function r32EnsureOutputLevelClosed(){
 const panel=r32GetOutputLevelPanel();
 const toggle=q("phoenixR3OutputLevelToggle");
 if(!panel||!toggle)return;
 if(!r32UserOpenedOutputLevel){
  panel.hidden=true;
  panel.classList.add("phoenix-r3-advanced-hidden");
  panel.setAttribute("aria-hidden","true");
  toggle.setAttribute("aria-expanded","false");
  toggle.textContent="Uitvoeringsniveau: A - Professionele projectoutput";
 }
}

function r32BindOutputLevelIntent(){
 const toggle=q("phoenixR3OutputLevelToggle");
 const panel=r32GetOutputLevelPanel();
 if(!toggle||!panel||toggle.dataset.phxR32Bound==="1")return;
 toggle.dataset.phxR32Bound="1";
 toggle.addEventListener("click",()=>{
  r32UserOpenedOutputLevel=!panel.hidden;
 },false);
}

function r32NewProjectSelected(){
 const project=q("projectSelect");
 if(!project)return true;
 const value=String(project.value||"").trim().toLowerCase();
 const text=(project.options&&project.selectedIndex>=0)
  ?String(project.options[project.selectedIndex].text||"").trim().toLowerCase()
  :"";
 return (
  !value ||
  value==="new" ||
  text.includes("nieuw / geen bestaand project gekozen") ||
  text.includes("geen bestaand project")
 );
}

function r32GetSessionNodes(){
 return {
  meta:document.querySelector(".progressmeta"),
  track:document.querySelector(".progresstrack"),
  step:q("progressStep"),
  progress:q("progressLabel"),
  percent:q("progressPercent")
 };
}

function r32LooksLikeStaleSession(nodes){
 if(!nodes)return false;
 const text=[
  nodes.progress?nodes.progress.textContent:"",
  nodes.step?nodes.step.textContent:"",
  nodes.percent?nodes.percent.textContent:""
 ].join(" ");
 return (
  text.includes("Phoenix Autonome Sessiestuurde Orchestrator") ||
  text.includes("PHOENIX-PAT-003") ||
  text.includes("Generic Sessieadapters") ||
  text.includes("92%")
 );
}

function r32HideStaleSessionIfNeeded(){
 const nodes=r32GetSessionNodes();
 if(!nodes.progress||!nodes.step)return;
 const shouldHide=(
  !r32ProjectRunStarted &&
  r32NewProjectSelected() &&
  r32LooksLikeStaleSession(nodes)
 );
 [nodes.meta,nodes.track,nodes.step].forEach(n=>{
  if(!n)return;
  if(shouldHide){
   n.hidden=true;
   n.classList.add("phoenix-r3-session-hidden");
   n.setAttribute("aria-hidden","true");
  }
 });
 if(shouldHide&&nodes.progress)nodes.progress.textContent="Geen actieve Phoenix-bewerking.";
 if(shouldHide&&nodes.percent)nodes.percent.textContent="0%";
}

function r32BindProjectStart(){
 const start=q("startBtn");
 if(!start||start.dataset.phxR32Bound==="1")return;
 start.dataset.phxR32Bound="1";
 start.addEventListener("click",()=>{
  r32ProjectRunStarted=true;
  const nodes=r32GetSessionNodes();
  [nodes.meta,nodes.track,nodes.step].forEach(n=>{
   if(!n)return;
   n.hidden=false;
   n.classList.remove("phoenix-r3-session-hidden");
   n.removeAttribute("aria-hidden");
  });
 },true);
}

function r32BindProjectSelection(){
 const project=q("projectSelect");
 if(!project||project.dataset.phxR32Bound==="1")return;
 project.dataset.phxR32Bound="1";
 project.addEventListener("change",()=>{
  r32ProjectRunStarted=false;
  setTimeout(r32Enforce,0);
 },false);
}

function r32Enforce(){
 r32BindOutputLevelIntent();
 r32BindProjectStart();
 r32BindProjectSelection();
 r32EnsureOutputLevelClosed();
 r32HideStaleSessionIfNeeded();
 document.documentElement.setAttribute("data-phoenix-live-ui-enforcement","4.6.19-r3.2");
}

function r32ScheduleEnforce(){
 if(r32EnforceTimer!==null)return;
 r32EnforceTimer=window.setTimeout(()=>{
  r32EnforceTimer=null;
  r32Enforce();
 },0);
}

if(document.readyState==="loading"){
 document.addEventListener("DOMContentLoaded",()=>{
  r32Enforce();
  window.setTimeout(r32Enforce,100);
  window.setTimeout(r32Enforce,500);
 },{once:true});
}else{
 r32Enforce();
 window.setTimeout(r32Enforce,100);
 window.setTimeout(r32Enforce,500);
}

new MutationObserver(r32ScheduleEnforce).observe(document.documentElement,{
 childList:true,
 subtree:true,
 characterData:true,
 attributes:true,
 attributeFilter:["hidden","class","aria-hidden","value"]
});

window.setInterval(r32Enforce,1500);
window.PHOENIX_STARTSCREEN_CONSOLIDATION=Object.freeze({version:"4.6.19-r3",revision:"4.6.19-r3.1",liveEnforcement:"4.6.19-r3.2",openManagement:()=>setManagement(true),closeManagement:()=>setManagement(false)});
})();