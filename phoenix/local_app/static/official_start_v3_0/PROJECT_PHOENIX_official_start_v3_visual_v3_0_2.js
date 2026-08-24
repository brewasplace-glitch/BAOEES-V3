(() => {
"use strict";

const TOKEN = window.PHOENIX_SESSION_TOKEN;
const headers = {"Content-Type": "application/json", "X-Phoenix-Token": TOKEN};
const desiredCatalog = Array.isArray(window.PHOENIX_DESIRED_OUTPUTS) ? window.PHOENIX_DESIRED_OUTPUTS : [];

let state = {
  monitorTimer: null,
  monitorJobId: null,
  autonomousModalJobId: null,
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

function setText(id, value){
  const el = $(id);
  const next = String(value ?? "");
  if(el && el.textContent !== next) el.textContent = next;
}
function setWidth(id, value){
  const el = $(id);
  const next = String(value);
  if(el && el.style.width !== next) el.style.width = next;
}
function stableJson(value){
  try { return JSON.stringify(value); } catch { return ""; }
}


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
  setText("gitState", git.clean ? "CLEAN" : "CHANGES DETECTED");
  setText("branchState", git.branch || "UNKNOWN");
  setText("runtimeState", `v${window.PHOENIX_RUNTIME_VERSION} · START v${window.PHOENIX_START_SCREEN_VERSION}`);
  setText("chipRuntime", `RUNTIME ${window.PHOENIX_RUNTIME_VERSION} · CONNECTED`);
  setText("sysCard", git.clean ? "● ALLE SYSTEMEN ACTIEF" : "● REPOSITORY WIJZIGINGEN");
}

function renderStatusHeavy(status){
  const signature = stableJson({
    projects: status.projects || [],
    workflows: status.workflows || [],
    modules: status.modules || []
  });
  if(state.__heavySignature === signature){
    renderStatusDelta({
      git: status.git,
      latest_job: status.latest_job,
      project_count: (status.projects || []).length,
      workflow_count: (status.workflows || []).length,
      module_count: (status.modules || []).length,
    });
    state.status = status;
    return;
  }
  state.__heavySignature = signature;
  state.status = status;
  renderStatusDelta({
    git: status.git,
    latest_job: status.latest_job,
    project_count: (status.projects || []).length,
    workflow_count: (status.workflows || []).length,
    module_count: (status.modules || []).length,
  });

  const psel = $("projectSelect");
  const current = psel.value;
  const projectHtml = '<option value="">Nieuw / geen bestaand project gekozen</option>' +
    (status.projects || []).map(p => `<option value="${esc(p.project_id)}">${esc(p.name)} · ${esc(p.project_id)}</option>`).join("");
  if(psel.innerHTML !== projectHtml) psel.innerHTML = projectHtml;
  if ([...psel.options].some(o => o.value === current)) psel.value = current;

  const workflowHtml = (status.workflows || []).filter(w => !w.ui_hidden).map(w => `
    <div class="listrow">
      <div>
        <div><strong>${esc(w.label)}</strong></div>
        <div class="meta">${esc(w.id)} · ${w.available ? "BESCHIKBAAR" : "NIET BESCHIKBAAR"}</div>
      </div>
      <button class="mini" data-workflow="${esc(w.id)}" ${w.available ? "" : "disabled"}>START</button>
    </div>
  `).join("") || '<div class="listrow"><div>Geen workflows geregistreerd.</div></div>';
  if($("workflowList").innerHTML !== workflowHtml){
    $("workflowList").innerHTML = workflowHtml;
    document.querySelectorAll("[data-workflow]").forEach(b => b.onclick = () => startWorkflow(b.dataset.workflow));
  }

  const projectListHtml = (status.projects || []).map(p => `
    <div class="listrow">
      <div>
        <div><strong>${esc(p.name)}</strong></div>
        <div class="meta">${esc(p.project_id)}</div>
      </div>
      <button class="mini" data-select-project="${esc(p.project_id)}">KIES</button>
    </div>
  `).join("") || '<div class="listrow"><div>Geen projectconfiguraties gevonden.</div></div>';
  if($("projectList").innerHTML !== projectListHtml){
    $("projectList").innerHTML = projectListHtml;
    document.querySelectorAll("[data-select-project]").forEach(b => b.onclick = () => {
      $("projectSelect").value = b.dataset.selectProject;
      toast("Project geselecteerd: " + b.dataset.selectProject);
    });
  }

  const modules = status.modules || [];
  const wanted = ["bouwkundig","constructief","civiel","infra","vergunningen","kosten_planning","qaqc","release_control","knowledge","digital_twin","projects","system_status"];
  const filtered = modules.filter(m => wanted.includes(m.id));
  const moduleHtml = filtered.map(m => `
    <button class="modbtn" data-module="${esc(m.id)}">
      <span class="name">${esc(m.label)}</span>
      <span class="sub">${esc(m.description)}</span>
    </button>
  `).join("");
  if($("moduleGrid").innerHTML !== moduleHtml){
    $("moduleGrid").innerHTML = moduleHtml;
    document.querySelectorAll(".modbtn[data-module]").forEach(b => b.onclick = () => openModule(b.dataset.module));
  }
  document.querySelectorAll(".navbtn[data-module]").forEach(b => b.onclick = () => openModule(b.dataset.module));
}
function renderProgress(progress){
  const signature = stableJson({
    percent: progress.percent || 0,
    status: progress.status || "",
    label: progress.label || "",
    step_label: progress.step_label || "",
    job_id: progress.job_id || ""
  });
  if(state.__progressSignature === signature) return;
  state.__progressSignature = signature;
  state.progress = progress;
  setWidth("progressFill", `${progress.percent || 0}%`);
  setText("progressPercent", `${progress.percent || 0}%`);
  setText("progressLabel", progress.label || "Geen actieve Phoenix-bewerking.");
  setText("progressStep", progress.step_label || "Wacht op nieuwe bewerking.");
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
  let view = null;
  if(moduleId === "system_status"){ return openSystemStatus(); }
  if(moduleId === "results"){ return openResults(); }

  try{
    view = await api(`/api/modules/${encodeURIComponent(moduleId)}/view`);
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

function stopActiveMonitor(){
  if(state.monitorTimer){
    clearTimeout(state.monitorTimer);
    state.monitorTimer = null;
  }
  state.monitorJobId = null;
}


function updateAutonomousRunModal(job){
  if(!job || state.autonomousModalJobId !== job.job_id) return;
  const statusEl = $("autonomousRunStatus");
  if(!statusEl) return;
  statusEl.textContent = String(job.status || "UNKNOWN").toUpperCase();
  const pct = Number.isFinite(Number(job.progress_percent)) ? Number(job.progress_percent) : null;
  setText("autonomousRunProgress", pct === null ? "—" : `${pct}%`);
  setText("autonomousRunStep", job.progress_step || "—");
  const count = Number(job.blocker_count || 0);
  setText("autonomousRunBlockers", String(count));
}

async function monitorActiveJob(jobId){
  stopActiveMonitor();
  state.monitorJobId = jobId;

  const tick = async () => {
    if(state.monitorJobId !== jobId) return;
    try{
      const job = await api(`/api/jobs/${encodeURIComponent(jobId)}`);
      const status = String(job.status || "").toUpperCase();
      updateAutonomousRunModal(job);

      // Update only the progress strip; never rebuild the dashboard.
      const percent =
        Number.isFinite(Number(job.progress_percent)) ? Number(job.progress_percent) :
        status === "PASSED" || status === "SUCCEEDED" ? 100 :
        status === "FAILED" ? 100 :
        status === "BLOCKED" ? 70 :
        status === "RUNNING" ? 55 : 10;

      renderProgress({
        active: status === "RUNNING" || status === "PENDING" || status === "QUEUED",
        percent,
        status,
        label: job.label || "Phoenix workflow",
        step_label:
          job.progress_step ||
          (status === "PASSED" || status === "SUCCEEDED" ? "Workflow gereed." :
          status === "BLOCKED" ? "Autonome run gecontroleerd geblokkeerd." :
          status === "FAILED" ? "Workflow mislukt." :
          status === "RUNNING" ? "Phoenix voert de geselecteerde workflow uit." :
          "Workflow wordt voorbereid."),
        job_id: job.job_id,
        output_dir: job.output_dir,
        log_path: job.log_path
      });

      if(status === "RUNNING" || status === "PENDING" || status === "QUEUED"){
        state.monitorTimer = setTimeout(tick, 2500);
      }else{
        stopActiveMonitor();
        if(status === "BLOCKED"){
          const count = Number(job.blocker_count || 0);
          toast(`Autonome run gecontroleerd geblokkeerd · ${count} capability blocker(s). Open RESULTATEN voor details.`, true);
        }else if(status === "FAILED"){
          toast("Phoenix workflow is mislukt. Open RESULTATEN / log voor details.", true);
        }else if(status === "PASSED" || status === "SUCCEEDED"){
          toast("Phoenix autonome workflow gereed.");
        }
        // Refresh the heavier data once, only after a real state transition.
        await refreshHeavy();
      }
    }catch(err){
      stopActiveMonitor();
      toast("Voortgangscontrole gestopt: " + err.message, true);
    }
  };

  await tick();
}

async function startWorkflow(id){
  try{
    const job = await post(`/api/workflows/${encodeURIComponent(id)}/run`);
    showModal("Workflow gestart", `<pre>${esc(JSON.stringify(job, null, 2))}</pre>`);
    toast(`Workflow gestart: ${job.label} · ${job.job_id}`);
    await monitorActiveJob(job.job_id);
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
$("manualRefreshBtn").onclick = async () => {
  await refreshAll();
  toast("Phoenix-status handmatig vernieuwd.");
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

    if(state.projectMode === "autonomous"){
      const job = await post("/api/autonomous/start", {session_id: session.session_id});
      state.autonomousModalJobId = job.job_id;
      showModal("AUTONOME PRODUCTIERUN GESTART", `
        <p><b>Sessie:</b> ${esc(session.session_id)}</p>
        <p><b>Project:</b> ${esc(session.bootstrap?.project_id || "—")}</p>
        <p><b>Gewenste outputselecties:</b> ${esc(String((session.desired_outputs || []).length))}</p>
        <p><b>Autonomous Project Mode:</b> Phoenix heeft zelf de Session-Driven Orchestrator gestart.</p>
        <p><b>Job:</b> ${esc(job.job_id)}</p>
        <p><b>Status:</b> <span id="autonomousRunStatus">${esc(job.status)}</span></p>
        <p><b>Voortgang:</b> <span id="autonomousRunProgress">—</span></p>
        <p><b>Stap:</b> <span id="autonomousRunStep">—</span></p>
        <p><b>Blokkeringen:</b> <span id="autonomousRunBlockers">0</span></p>
        <p>Er is geen technische workflowselectie door de gebruiker nodig.</p>
      `);
      toast("Autonomous Session-Driven Orchestrator gestart.");
      await monitorActiveJob(job.job_id);
      return;
    }

    const flows = (session.available_workflows || []).filter(w => !w.ui_hidden);
    showModal("PROJECTANALYSE GESTART", `
      <p><b>Sessie:</b> ${esc(session.session_id)}</p>
      <p><b>Status:</b> ${esc(session.status)}</p>
      <p><b>Gewenste outputselecties:</b> ${esc(String((session.desired_outputs || []).length))}</p>
      <p>Kies een beschikbare Phoenix-workflow:</p>
      <div>${flows.length ? flows.map(w => `
        <div class="listrow">
          <div><strong>${esc(w.label)}</strong><div class="meta">${esc(w.id)}</div></div>
          <button class="mini" data-modal-workflow="${esc(w.id)}">START</button>
        </div>
      `).join("") : "<p>Geen uitvoerbare workflow beschikbaar.</p>"}</div>
    `);
    document.querySelectorAll("[data-modal-workflow]").forEach(
      b => b.onclick = () => startWorkflow(b.dataset.modalWorkflow)
    );
    toast("Projectanalyse-sessie gestart.");
  }catch(err){ toast(err.message, true); }
};

(async function init(){
  const defaults = await api("/api/desired-outputs");
  setDesired(defaults.default || []);
  loadMyStandard();
  renderDesiredOutputs();

  // One initial dashboard read only.
  await refreshAll();

  // Zero idle polling: if a job is already active, monitor only that job.
  const initial = state.progress || {};
  if(initial.active && initial.job_id){
    await monitorActiveJob(initial.job_id);
  }
})();
})();
// PROJECT PHOENIX PROFESSIONAL COUNTRY-AWARE END-TO-END A/B ROUTING v1.0
(() => {
  const id = "phoenix-professional-country-aware-ab-v1";
  if (document.getElementById(id)) return;
  const script = document.createElement("script");
  script.id = id;
  script.src = "/start-v3/PROJECT_PHOENIX_professional_country_aware_end_to_end_ab_v1_0.js";
  script.async = false;
  (document.head || document.documentElement).appendChild(script);
})();
