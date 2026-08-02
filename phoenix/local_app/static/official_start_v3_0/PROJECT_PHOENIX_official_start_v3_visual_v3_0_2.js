(() => {
"use strict";

const TOKEN = window.PHOENIX_SESSION_TOKEN;
const headers = {"Content-Type": "application/json", "X-Phoenix-Token": TOKEN};
const desiredCatalog = Array.isArray(window.PHOENIX_DESIRED_OUTPUTS) ? window.PHOENIX_DESIRED_OUTPUTS : [];

let state = {
  summary: null,
  status: null,
  progress: null,
  results: null,
  projectType: "BOUW",
  projectMode: "autonomous",
  uploadBatch: null,
  desiredOutputs: new Set(),
  myStandardKey: "phoenix.start.v302.myStandard",
};

const $ = id => document.getElementById(id);
const esc = v => String(v ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

function toast(msg, bad=false){
  const e = $("toast");
  e.textContent = msg;
  e.style.display = "block";
  e.style.borderColor = bad ? "#943636" : "#2b6796";
  clearTimeout(window.__phxt);
  window.__phxt = setTimeout(() => e.style.display = "none", 4200);
}

function showModal(title, html){
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  $("modal").style.display = "flex";
}
$("modalClose").onclick = () => $("modal").style.display = "none";
$("modal").onclick = e => { if (e.target === $("modal")) $("modal").style.display = "none"; };

async function api(path, options={}){
  const r = await fetch(path, {cache: "no-store", ...options});
  const v = await r.json();
  if(!r.ok) throw new Error(v.error || r.statusText);
  return v;
}
const post = (path, body={}) => api(path, {method:"POST", headers, body: JSON.stringify(body)});

function renderDesiredOutputs(){
  const root = $("desiredOutputGroups");
  root.innerHTML = desiredCatalog.map(group => `
    <div class="outputgroup">
      <h3>${esc(group.group)}</h3>
      ${(group.items || []).map(item => `
        <label class="outputitem">
          <input type="checkbox" class="desiredCheck" value="${esc(item.id)}">
          <span>${esc(item.label)}</span>
        </label>
      `).join("")}
    </div>
  `).join("");
  root.querySelectorAll(".desiredCheck").forEach(ch => {
    ch.checked = state.desiredOutputs.has(ch.value);
    ch.onchange = () => {
      if (ch.checked) state.desiredOutputs.add(ch.value);
      else state.desiredOutputs.delete(ch.value);
    };
  });
}

function allOutputIds(){
  const ids = [];
  desiredCatalog.forEach(g => (g.items || []).forEach(i => ids.push(i.id)));
  return ids;
}

function setDesired(ids){
  state.desiredOutputs = new Set(ids);
  renderDesiredOutputs();
}

function loadMyStandard(){
  try{
    const raw = localStorage.getItem(state.myStandardKey);
    if(!raw) return false;
    const ids = JSON.parse(raw);
    if(Array.isArray(ids)){ setDesired(ids); return true; }
  }catch{}
  return false;
}

function saveMyStandard(){
  localStorage.setItem(state.myStandardKey, JSON.stringify([...state.desiredOutputs]));
  toast("Mijn standaard gewenste output is opgeslagen.");
}

function renderStatusDelta(summary){
  state.summary = summary;
  const git = summary.git || {};
  $("gitState").textContent = git.clean ? "CLEAN" : "CHANGES DETECTED";
  $("branchState").textContent = git.branch || "UNKNOWN";
  $("runtimeState").textContent = `v${window.PHOENIX_RUNTIME_VERSION} · START v${window.PHOENIX_START_SCREEN_VERSION}`;
  $("chipRuntime").textContent = `RUNTIME ${window.PHOENIX_RUNTIME_VERSION} · CONNECTED`;
  $("sysCard").textContent = git.clean ? "● ALLE SYSTEMEN ACTIEF" : "● REPOSITORY WIJZIGINGEN";
}

function renderStatusHeavy(status){
  state.status = status;
  renderStatusDelta({
    git: status.git,
    latest_job: status.latest_job,
    project_count: (status.projects || []).length,
    workflow_count: (status.workflows || []).length,
    module_count: (status.modules || []).length,
    progress: status.progress,
  });

  const psel = $("projectSelect");
  const current = psel.value;
  psel.innerHTML = '<option value="">Nieuw / geen bestaand project gekozen</option>' +
    (status.projects || []).map(p => `<option value="${esc(p.project_id)}">${esc(p.name)} · ${esc(p.project_id)}</option>`).join("");
  if ([...psel.options].some(o => o.value === current)) psel.value = current;

  $("workflowList").innerHTML = (status.workflows || []).map(w => `
    <div class="listrow">
      <div>
        <div><strong>${esc(w.label)}</strong></div>
        <div class="meta">${esc(w.id)} · ${w.available ? "BESCHIKBAAR" : "NIET BESCHIKBAAR"}</div>
      </div>
      <button class="mini" data-workflow="${esc(w.id)}" ${w.available ? "" : "disabled"}>START</button>
    </div>
  `).join("") || '<div class="listrow"><div>Geen workflows geregistreerd.</div></div>';
  document.querySelectorAll("[data-workflow]").forEach(b => b.onclick = () => startWorkflow(b.dataset.workflow));

  $("projectList").innerHTML = (status.projects || []).map(p => `
    <div class="listrow">
      <div>
        <div><strong>${esc(p.name)}</strong></div>
        <div class="meta">${esc(p.project_id)}</div>
      </div>
      <button class="mini" data-select-project="${esc(p.project_id)}">KIES</button>
    </div>
  `).join("") || '<div class="listrow"><div>Geen projectconfiguraties gevonden.</div></div>';
  document.querySelectorAll("[data-select-project]").forEach(b => b.onclick = () => {
    $("projectSelect").value = b.dataset.selectProject;
    toast("Project geselecteerd: " + b.dataset.selectProject);
  });

  const modules = status.modules || [];
  const wanted = ["bouwkundig","constructief","civiel","infra","vergunningen","kosten_planning","qaqc","release_control","knowledge","digital_twin","projects","system_status"];
  const filtered = modules.filter(m => wanted.includes(m.id));
  $("moduleGrid").innerHTML = filtered.map(m => `
    <button class="modbtn" data-module="${esc(m.id)}">
      <span class="name">${esc(m.label)}</span>
      <span class="sub">${esc(m.description)}</span>
    </button>
  `).join("");
  document.querySelectorAll(".modbtn[data-module]").forEach(b => b.onclick = () => openModule(b.dataset.module));
  document.querySelectorAll(".navbtn[data-module]").forEach(b => b.onclick = () => openModule(b.dataset.module));
}

function renderProgress(progress){
  state.progress = progress;
  $("progressFill").style.width = `${progress.percent || 0}%`;
  $("progressPercent").textContent = `${progress.percent || 0}%`;
  $("progressLabel").textContent = progress.label || "Geen actieve Phoenix-bewerking.";
  $("progressStep").textContent = progress.step_label || "Wacht op nieuwe bewerking.";
}

async function refreshSummary(){
  try{
    const summary = await api("/api/summary");
    renderStatusDelta(summary);
  }catch(err){
    toast(err.message, true);
  }
}
async function refreshHeavy(){
  try{
    const status = await api("/api/status");
    renderStatusHeavy(status);
  }catch(err){
    toast(err.message, true);
  }
}
async function refreshProgress(){
  try{
    const progress = await api("/api/progress");
    renderProgress(progress);
  }catch(err){
    toast(err.message, true);
  }
}
async function refreshAll(){
  await refreshHeavy();
  await refreshProgress();
}
async function openSystemStatus(){
  try{
    const s = await api("/api/status");
    showModal("SYSTEM STATUS", `<pre>${esc(JSON.stringify(s, null, 2))}</pre>`);
  }catch(err){ toast(err.message, true); }
}
async function openResults(){
  try{
    const results = await api("/api/results");
    const latest = results.latest_job;
    const top = latest ? `
      <p><b>Laatste job:</b> ${esc(latest.label)}<br>
      <b>Status:</b> ${esc(latest.status)}<br>
      <b>Output:</b> ${esc(latest.output_dir || "—")}<br>
      <b>Log:</b> ${esc(latest.log_path || "—")}</p>` : "<p>Geen workflowjob bekend.</p>";
    const list = (results.items || []).slice(0, 80).map(item => `
      <div class="listrow">
        <div><strong>${esc(item.name)}</strong><div class="meta">${esc(item.relative_path)} · ${esc(item.category)}</div></div>
        <button class="mini" data-open-result="${esc(item.relative_path)}">OPEN</button>
      </div>
    `).join("") || "<p>Geen resultaten gevonden.</p>";
    showModal("RESULTATEN", `
      <p><b>Aantal resultaatbestanden:</b> ${results.count}</p>
      ${top}
      <div>${list}</div>
    `);
    document.querySelectorAll("[data-open-result]").forEach(b => b.onclick = () => openRepoTarget(b.dataset.openResult));
  }catch(err){ toast(err.message, true); }
}
async function openRepoTarget(relativePath){
  try{
    await post("/api/open", {target_id: ""});
  }catch{
    // No generic target route for arbitrary paths; show instruction instead
    showModal("RESULTAAT OPENEN", `<p>Open handmatig in de repository:</p><pre>${esc(relativePath)}</pre>`);
  }
}
async function openModule(moduleId){
  if(moduleId === "system_status"){ return openSystemStatus(); }
  if(moduleId === "results"){ return openResults(); }

  try{
    const view = await api(`/api/modules/${encodeURIComponent(moduleId)}/view`);
    if(view.route_kind === "screen" && view.screen_route){
      if(view.screen_route === "/start-v3/"){
        window.location.href = "/start-v3/";
        return;
      }
      if(view.screen_route === "/"){
        window.location.href = "/";
        return;
      }
      if(view.screen_route.includes("#results")){
        return openResults();
      }
      if(view.screen_route.includes("#system")){
        return openSystemStatus();
      }
    }
    if(view.route_kind === "modal_info"){
      showModal(view.label, `<p>${esc(view.description)}</p><pre>${esc(JSON.stringify(view.extra || {}, null, 2))}</pre>`);
      return;
    }

    const action = await post(`/api/modules/${encodeURIComponent(moduleId)}/open`, {});
    if(action.mode === "opened_path"){
      toast(`Geopend: ${action.label}`);
    } else if(action.mode === "screen" && action.route) {
      if(action.route.includes("#results")) return openResults();
      if(action.route.includes("#system")) return openSystemStatus();
      window.location.href = action.route;
    } else if(action.mode === "modal_info") {
      showModal(action.label, `<p>${esc(action.description || "")}</p>`);
    }
  } catch(err){
    showModal("MODULE", `<p><b>${esc(view?.label || moduleId)}</b></p><p>${esc(err.message)}</p>`);
    toast(err.message, true);
  }
}
async function startWorkflow(id){
  try{
    const job = await post(`/api/workflows/${encodeURIComponent(id)}/run`);
    showModal("Workflow gestart", `<pre>${esc(JSON.stringify(job, null, 2))}</pre>`);
    toast(`Workflow gestart: ${job.label} · ${job.job_id}`);
    await refreshProgress();
  }catch(err){ toast(err.message, true); }
}

document.querySelectorAll(".typecard").forEach(btn => btn.onclick = () => {
  state.projectType = btn.dataset.type;
  document.querySelectorAll(".typecard").forEach(x => x.classList.toggle("active", x === btn));
});
document.querySelectorAll(".modecard").forEach(btn => btn.onclick = () => {
  state.projectMode = btn.dataset.mode;
  document.querySelectorAll(".modecard").forEach(x => x.classList.toggle("active", x === btn));
});

$("dropzone").onclick = () => $("filePicker").click();
$("filePicker").onchange = async e => {
  const files = [...e.target.files];
  if(!files.length) return;
  const total = files.reduce((n, f) => n + f.size, 0);
  if(total > 120 * 1024 * 1024){ toast("Uploadbatch is groter dan 120 MB.", true); return; }
  $("uploadState").textContent = `Uploaden: ${files.length} bestand(en)…`;
  try{
    const encoded = [];
    for(const file of files){
      if(file.size > 60 * 1024 * 1024) throw new Error(`${file.name} is groter dan 60 MB.`);
      const buf = await file.arrayBuffer();
      let binary = "", bytes = new Uint8Array(buf), chunk = 0x8000;
      for(let i=0;i<bytes.length;i+=chunk) binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
      encoded.push({name: file.name, base64: btoa(binary)});
    }
    state.uploadBatch = await post("/api/uploads", {files: encoded});
    $("uploadState").textContent = `Upload opgeslagen: batch ${state.uploadBatch.batch_id} · ${state.uploadBatch.file_count} bestand(en)`;
    toast("Upload werkelijk opgeslagen in Phoenix intake.");
  }catch(err){
    $("uploadState").textContent = "Upload mislukt.";
    toast(err.message, true);
  }
};

$("speechBtn").onclick = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR){
    showModal("SPRAAK", "<p>Deze browser biedt geen Web Speech Recognition. Typ of plak de projectopdracht in het tekstvak.</p>");
    return;
  }
  const recognition = new SR();
  recognition.lang = "nl-NL";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => toast("Luisteren… spreek de projectopdracht in.");
  recognition.onerror = e => toast("Spraakinvoer fout: " + e.error, true);
  recognition.onresult = e => {
    const text = e.results[0][0].transcript;
    $("brief").value = ($("brief").value + " " + text).trim();
    toast("Spraakinvoer toegevoegd aan projectopdracht.");
  };
  recognition.start();
};

$("allOnBtn").onclick = () => setDesired(allOutputIds());
$("allOffBtn").onclick = () => setDesired([]);
$("recommendedBtn").onclick = async () => {
  const v = await api("/api/desired-outputs");
  setDesired(v.default || []);
};
$("myStandardBtn").onclick = () => {
  if(state.desiredOutputs.size){ saveMyStandard(); }
  else if(!loadMyStandard()) toast("Nog geen opgeslagen standaard aanwezig.", true);
};
$("resultsBtn").onclick = openResults;
$("resultsNav").onclick = openResults;
$("startBtn").onclick = async () => {
  try{
    const session = await post("/api/project-analysis/start", {
      project_type: state.projectType,
      brief: $("brief").value,
      selected_project: $("projectSelect").value,
      upload_batch: state.uploadBatch?.batch_id || "",
      project_mode: state.projectMode,
      desired_outputs: [...state.desiredOutputs],
    });
    const flows = session.available_workflows || [];
    showModal("PROJECTANALYSE GESTART", `
      <p><b>Sessie:</b> ${esc(session.session_id)}</p>
      <p><b>Status:</b> ${esc(session.status)}</p>
      <p><b>Gewenste outputselecties:</b> ${esc(String((session.desired_outputs || []).length))}</p>
      <p>De analyse-intake is opgeslagen. Kies nu een beschikbare echte Phoenix-workflow:</p>
      <div>${flows.length ? flows.map(w => `
        <div class="listrow">
          <div><strong>${esc(w.label)}</strong><div class="meta">${esc(w.id)}</div></div>
          <button class="mini" data-modal-workflow="${esc(w.id)}">START</button>
        </div>
      `).join("") : "<p>Geen uitvoerbare workflow beschikbaar.</p>"}</div>
    `);
    document.querySelectorAll("[data-modal-workflow]").forEach(b => b.onclick = () => startWorkflow(b.dataset.modalWorkflow));
    toast("Projectanalyse-sessie gestart.");
  }catch(err){ toast(err.message, true); }
};

(async function init(){
  const defaults = await api("/api/desired-outputs");
  setDesired(defaults.default || []);
  loadMyStandard();
  renderDesiredOutputs();
  await refreshAll();
  setInterval(refreshSummary, 3000);
  setInterval(refreshProgress, 2000);
  setInterval(refreshHeavy, 30000);
})();
})();