(() => {
"use strict";
const TOKEN=window.PHOENIX_SESSION_TOKEN;
const headers={"Content-Type":"application/json","X-Phoenix-Token":TOKEN};
let status=null, projectType="BOUW", uploadBatch=null;

const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
const toast=(msg,bad=false)=>{const e=$("toast");e.textContent=msg;e.style.display="block";e.style.borderColor=bad?"#9b3333":"#2b6796";clearTimeout(window.__phxt);window.__phxt=setTimeout(()=>e.style.display="none",4200)};
const showModal=(title,html)=>{$("modalTitle").textContent=title;$("modalBody").innerHTML=html;$("modal").style.display="flex"};
$("modalClose").onclick=()=>$("modal").style.display="none";
$("modal").onclick=e=>{if(e.target===$("modal"))$("modal").style.display="none"};

async function api(path,options={}){
  const r=await fetch(path,{cache:"no-store",...options});
  const v=await r.json();
  if(!r.ok)throw new Error(v.error||r.statusText);
  return v;
}
const post=(path,body={})=>api(path,{method:"POST",headers,body:JSON.stringify(body)});

function renderStatus(s){
  status=s;
  $("runtimeLive").textContent=`RUNTIME ${s.version} · CONNECTED`;
  $("runtimeLive").className="live";
  $("gitState").textContent=s.git.clean?"CLEAN":"CHANGES DETECTED";
  $("gitState").className=s.git.clean?"good":"warn";
  $("branchState").textContent=s.git.branch||"UNKNOWN";
  $("runtimeState").textContent=`v${s.version} · START v${s.start_screen_version}`;
  const psel=$("projectSelect");
  const current=psel.value;
  psel.innerHTML='<option value="">Nieuw / geen bestaand project gekozen</option>'+
    s.projects.map(p=>`<option value="${esc(p.project_id)}">${esc(p.name)} · ${esc(p.project_id)}</option>`).join("");
  if([...psel.options].some(o=>o.value===current))psel.value=current;

  const mods=new Map((s.modules||[]).map(x=>[x.id,x]));
  document.querySelectorAll("[data-module]").forEach(btn=>{
    const m=mods.get(btn.dataset.module);
    btn.disabled=!!m && !m.available;
    if(m)btn.title=m.available?`Open ${m.label}`:`${m.label} is nog niet als repositorydoel beschikbaar`;
  });

  renderWorkflows(s.workflows||[]);
  renderProjects(s.projects||[]);
}

function renderWorkflows(items){
  const root=$("workflowList");
  if(!items.length){root.innerHTML='<div class="project">Geen workflows geregistreerd.</div>';return}
  root.innerHTML=items.map(w=>`<div class="workflow">
    <div><b>${esc(w.label)}</b><div><span class="tag">${esc(w.id)}</span> ${w.available?'<span class="good">BESCHIKBAAR</span>':'<span class="warn">NIET BESCHIKBAAR</span>'}</div></div>
    <button data-workflow="${esc(w.id)}" ${w.available?"":"disabled"}>START</button>
  </div>`).join("");
  root.querySelectorAll("[data-workflow]").forEach(b=>b.onclick=()=>startWorkflow(b.dataset.workflow));
}

function renderProjects(items){
  const root=$("projectList");
  if(!items.length){root.innerHTML='<div class="project">Geen projectconfiguraties gevonden.</div>';return}
  root.innerHTML=items.map(p=>`<div class="project"><div><b>${esc(p.name)}</b><div><span class="tag">${esc(p.project_id)}</span></div></div><button data-select-project="${esc(p.project_id)}">KIES</button></div>`).join("");
  root.querySelectorAll("[data-select-project]").forEach(b=>b.onclick=()=>{$("projectSelect").value=b.dataset.selectProject;toast("Project geselecteerd: "+b.dataset.selectProject)});
}

async function refresh(){
  try{renderStatus(await api("/api/status"))}
  catch(e){$("runtimeLive").textContent="RUNTIME ERROR";$("runtimeLive").className="live warn";toast(e.message,true)}
}

async function openModule(id){
  try{const r=await post(`/api/modules/${encodeURIComponent(id)}/open`);toast(`Geopend: ${r.label}`)}
  catch(e){toast(e.message,true)}
}

async function startWorkflow(id){
  try{
    const job=await post(`/api/workflows/${encodeURIComponent(id)}/run`);
    toast(`Workflow gestart: ${job.label} · ${job.job_id}`);
    showModal("Workflow gestart",`<pre>${esc(JSON.stringify(job,null,2))}</pre>`);
    refresh();
  }catch(e){toast(e.message,true)}
}

document.querySelectorAll(".type").forEach(b=>b.onclick=()=>{
  projectType=b.dataset.type;
  document.querySelectorAll(".type").forEach(x=>x.classList.toggle("active",x===b));
  toast("Projecttype geselecteerd: "+projectType);
});
document.querySelectorAll("[data-module]").forEach(b=>b.onclick=()=>openModule(b.dataset.module));

$("systemBtn").onclick=async()=>{
  try{const s=await api("/api/status");showModal("SYSTEM STATUS",`<pre>${esc(JSON.stringify(s,null,2))}</pre>`)}
  catch(e){toast(e.message,true)}
};

$("uploadBtn").onclick=()=>$("filePicker").click();
$("filePicker").onchange=async e=>{
  const files=[...e.target.files];
  if(!files.length)return;
  const total=files.reduce((n,f)=>n+f.size,0);
  if(total>120*1024*1024){toast("Uploadbatch is groter dan 120 MB.",true);return}
  $("uploadState").textContent=`Uploaden: ${files.length} bestand(en)…`;
  try{
    const encoded=[];
    for(const file of files){
      if(file.size>60*1024*1024)throw new Error(`${file.name} is groter dan 60 MB.`);
      const buf=await file.arrayBuffer();
      let binary="", bytes=new Uint8Array(buf), chunk=0x8000;
      for(let i=0;i<bytes.length;i+=chunk)binary+=String.fromCharCode(...bytes.subarray(i,i+chunk));
      encoded.push({name:file.name,base64:btoa(binary)});
    }
    uploadBatch=await post("/api/uploads",{files:encoded});
    $("uploadState").textContent=`Upload opgeslagen: batch ${uploadBatch.batch_id} · ${uploadBatch.file_count} bestand(en)`;
    toast("Upload werkelijk opgeslagen in Phoenix intake.");
  }catch(err){$("uploadState").textContent="Upload mislukt.";toast(err.message,true)}
};

$("speechBtn").onclick=()=>{
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){
    showModal("SPRAAK",'<p>Deze browser biedt geen Web Speech Recognition. Typ of plak de projectopdracht in het tekstvak.</p>');
    return;
  }
  const recognition=new SR();
  recognition.lang="nl-NL";
  recognition.interimResults=false;
  recognition.maxAlternatives=1;
  recognition.onstart=()=>toast("Luisteren… spreek de projectopdracht in.");
  recognition.onerror=e=>toast("Spraakinvoer fout: "+e.error,true);
  recognition.onresult=e=>{
    const text=e.results[0][0].transcript;
    $("brief").value=($("brief").value+" "+text).trim();
    toast("Spraakinvoer toegevoegd aan projectopdracht.");
  };
  recognition.start();
};

$("startBtn").onclick=async()=>{
  try{
    const session=await post("/api/project-analysis/start",{
      project_type:projectType,
      brief:$("brief").value,
      selected_project:$("projectSelect").value,
      upload_batch:uploadBatch?.batch_id||""
    });
    const flows=session.available_workflows||[];
    const html=`<p><b>Sessie:</b> ${esc(session.session_id)}</p>
      <p><b>Status:</b> ${esc(session.status)}</p>
      <p>De analyse-intake is opgeslagen. Kies nu een beschikbare echte Phoenix-workflow:</p>
      <div id="modalFlows">${flows.length?flows.map(w=>`<div class="workflow"><div><b>${esc(w.label)}</b><div><span class="tag">${esc(w.id)}</span></div></div><button data-modal-workflow="${esc(w.id)}">START</button></div>`).join(""):'<p class="warn">Geen uitvoerbare workflow beschikbaar.</p>'}</div>
      <p><button id="openRuntime" class="action">OPEN VOLLEDIGE RUNTIME</button></p>`;
    showModal("PROJECTANALYSE GESTART",html);
    document.querySelectorAll("[data-modal-workflow]").forEach(b=>b.onclick=()=>startWorkflow(b.dataset.modalWorkflow));
    $("openRuntime").onclick=()=>location.href="/";
    toast("Projectanalyse-sessie gestart.");
  }catch(e){toast(e.message,true)}
};

refresh();
setInterval(refresh,5000);
})();