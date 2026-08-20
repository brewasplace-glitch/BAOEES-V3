(() => {
"use strict";

const BOOT = window.PHOENIX_START_CAPABILITY_BOOTSTRAP || {};
const TOKEN = String(BOOT.token || "");
const ROOT_ID = "phoenix-start-capability-drawer";
const STYLE_ID = "phoenix-start-capability-style";
const STATUS_POLL_MS = 6000;

let lastCapabilityKey = "";
let lastProjectKey = "";
let lastJobKey = "";
let refreshTimer = null;
let refreshInFlight = false;

const esc = value => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || response.statusText);
  return value;
}

function post(path, body) {
  return api(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Phoenix-Token":TOKEN
    },
    body: JSON.stringify(body || {})
  });
}

function installStyles() {
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
#${ROOT_ID}{
  position:fixed;
  right:18px;
  bottom:18px;
  top:auto;
  width:min(390px,calc(100vw - 36px));
  z-index:2147483000;
  display:flex;
  flex-direction:column-reverse;
  align-items:flex-end;
  gap:8px;
  pointer-events:none;
  font:13px/1.4 "Segoe UI",Arial,sans-serif;
  color:#eef6ff
}
#${ROOT_ID} *{box-sizing:border-box}
#${ROOT_ID} .phx-cap-toggle{
  pointer-events:auto;
  display:block;
  border:1px solid rgba(90,180,255,.65);
  border-radius:999px;
  padding:9px 14px;
  background:rgba(2,18,40,.96);
  color:#dff2ff;
  font-weight:750;
  cursor:pointer;
  box-shadow:0 8px 28px rgba(0,0,0,.32)
}
#${ROOT_ID} .phx-cap-panel{
  pointer-events:auto;
  width:100%;
  max-height:min(64vh,560px);
  overflow:auto;
  padding:14px;
  border:1px solid rgba(90,180,255,.34);
  border-radius:16px;
  background:rgba(3,16,35,.97);
  box-shadow:0 18px 48px rgba(0,0,0,.40);
  backdrop-filter:blur(12px)
}
#${ROOT_ID} .phx-cap-panel[hidden]{display:none}
#${ROOT_ID} h2{font-size:15px;margin:0 0 5px}
#${ROOT_ID} .phx-cap-sub{font-size:11px;color:#9fb6cc;margin-bottom:10px}
#${ROOT_ID} select{
  width:100%;
  padding:8px;
  border-radius:9px;
  border:1px solid #33506d;
  background:#081b31;
  color:#eef6ff;
  margin:7px 0 10px
}
#${ROOT_ID} .phx-cap-card{
  border:1px solid rgba(255,255,255,.12);
  border-radius:12px;
  padding:10px;
  margin-top:8px;
  background:rgba(255,255,255,.04)
}
#${ROOT_ID} .phx-cap-title{font-weight:760}
#${ROOT_ID} .phx-cap-desc{font-size:11px;color:#aebfd0;margin:4px 0 8px}
#${ROOT_ID} .phx-cap-row{display:flex;gap:8px;align-items:center;justify-content:space-between}
#${ROOT_ID} .phx-cap-state{font-size:10px;font-weight:800;letter-spacing:.05em}
#${ROOT_ID} .ready{color:#7ee6a8}
#${ROOT_ID} .blocked{color:#ffd166}
#${ROOT_ID} button.phx-cap-run{
  border:0;
  border-radius:9px;
  padding:8px 10px;
  background:#0b71d9;
  color:white;
  font-weight:750;
  cursor:pointer
}
#${ROOT_ID} button.phx-cap-run:disabled{background:#435268;cursor:not-allowed}
#${ROOT_ID} .phx-cap-job{
  margin-top:10px;
  padding:9px;
  border-radius:9px;
  background:#020c18;
  color:#c9deef;
  white-space:pre-wrap;
  overflow-wrap:anywhere;
  max-height:150px;
  overflow:auto
}`;
  document.head.appendChild(style);
}

function ensureRoot() {
  let root = document.getElementById(ROOT_ID);
  if (root) return root;

  installStyles();
  root = document.createElement("section");
  root.id = ROOT_ID;
  root.setAttribute("aria-label", "Phoenix start capabilities");
  root.innerHTML = `
    <button type="button" class="phx-cap-toggle" aria-expanded="false">AUTONOME PHOENIX-FLOW</button>
    <div class="phx-cap-panel" hidden>
      <h2>Startscherm · Autonome capabilities</h2>
      <div class="phx-cap-sub">Registry-gestuurd · nieuwe capabilities verschijnen automatisch</div>
      <label>Project
        <select class="phx-cap-project">
          <option value="">Selecteer project…</option>
        </select>
      </label>
      <div class="phx-cap-list"></div>
      <div class="phx-cap-job">Geen actieve autonome run.</div>
    </div>`;
  document.body.appendChild(root);

  const toggle = root.querySelector(".phx-cap-toggle");
  const panel = root.querySelector(".phx-cap-panel");

  toggle.addEventListener("click", () => {
    const open = panel.hasAttribute("hidden");
    if (open) panel.removeAttribute("hidden");
    else panel.setAttribute("hidden", "");
    toggle.setAttribute("aria-expanded", String(open));
  });

  if (location.hash === "#architectural-ae") {
    panel.removeAttribute("hidden");
    toggle.setAttribute("aria-expanded", "true");
  }

  return root;
}

function stableKey(value) {
  return JSON.stringify(value || null);
}

function syncProjects(root, projects) {
  const normalized = (projects || []).map(project => ({
    project_id: String(project.project_id || ""),
    name: String(project.name || project.project_id || ""),
    file: String(project.file || "")
  }));
  const nextKey = stableKey(normalized);
  if (nextKey === lastProjectKey) return;
  lastProjectKey = nextKey;

  const select = root.querySelector(".phx-cap-project");
  const current = select.value;
  const fragment = document.createDocumentFragment();
  fragment.appendChild(new Option("Selecteer project…", ""));

  normalized.forEach(project => {
    fragment.appendChild(
      new Option(`${project.name} · ${project.project_id}`, project.file)
    );
  });

  select.replaceChildren(fragment);
  if ([...select.options].some(option => option.value === current)) {
    select.value = current;
  }
}

function actionButton(capability, root) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "phx-cap-run";
  button.textContent = capability.available
    ? "START A–E PROJECTFLOW"
    : "NIET BESCHIKBAAR";
  button.disabled = !capability.available;

  button.addEventListener("click", async () => {
    const project = root.querySelector(".phx-cap-project").value;
    const action = capability.action || {};

    if (action.requires_project && !project) {
      setJobText(root, "Selecteer eerst een project.");
      return;
    }

    button.disabled = true;
    try {
      const job = await post(action.path, { project_file: project });
      setJobText(
        root,
        `Run gestart: ${job.job_id}\nProject: ${job.project_id}\nStatus: ${job.status}`
      );
      lastJobKey = "";
      scheduleRefresh(700);
    } catch (error) {
      setJobText(root, `Startfout: ${error.message}`);
    } finally {
      window.setTimeout(() => {
        button.disabled = !capability.available;
      }, 900);
    }
  });

  return button;
}

function syncCapabilities(root, capabilities) {
  const normalized = (capabilities || []).map(capability => ({
    id: String(capability.id || ""),
    label: String(capability.label || ""),
    description: String(capability.description || ""),
    available: Boolean(capability.available),
    status: String(capability.status || ""),
    action: capability.action || {}
  }));
  const nextKey = stableKey(normalized);
  if (nextKey === lastCapabilityKey) return;
  lastCapabilityKey = nextKey;

  const list = root.querySelector(".phx-cap-list");
  const fragment = document.createDocumentFragment();

  normalized.forEach(capability => {
    const card = document.createElement("article");
    card.className = "phx-cap-card";
    card.innerHTML = `
      <div class="phx-cap-title">${esc(capability.label)}</div>
      <div class="phx-cap-desc">${esc(capability.description)}</div>
      <div class="phx-cap-row">
        <span class="phx-cap-state ${capability.available ? "ready" : "blocked"}">${esc(capability.status)}</span>
      </div>`;

    const action = capability.action || {};
    if (action.kind === "project_api_post" && action.path) {
      card.querySelector(".phx-cap-row").appendChild(
        actionButton(capability, root)
      );
    }
    fragment.appendChild(card);
  });

  if (!normalized.length) {
    const empty = document.createElement("div");
    empty.textContent = "Geen start-capabilities geregistreerd.";
    fragment.appendChild(empty);
  }

  list.replaceChildren(fragment);
}

function setJobText(root, text) {
  const node = root.querySelector(".phx-cap-job");
  const value = String(text || "");
  if (node.textContent !== value) node.textContent = value;
}

function syncJob(root, orchestration) {
  const latest = orchestration?.latest_job || null;
  const key = stableKey(latest);
  if (key === lastJobKey) return;
  lastJobKey = key;

  if (!latest) {
    setJobText(root, "Geen actieve autonome run.");
    return;
  }

  let text =
    `Laatste run: ${latest.job_id}\n` +
    `Project: ${latest.project_id}\n` +
    `Status: ${latest.status}`;

  if (latest.recommended_variant_id) {
    text += `\nAanbevolen variant: ${latest.recommended_variant_id}`;
  }
  if (latest.delivery_manifest) {
    text += `\nDelivery: ${latest.delivery_manifest}`;
  }
  setJobText(root, text);
}

function applyStatus(status) {
  const root = ensureRoot();
  const orchestration = status.architectural_orchestration || {};
  const projects = status.architectural_orchestration?.projects || [];
  const capabilities = Array.isArray(status.start_capabilities)
    ? status.start_capabilities
    : [];

  syncProjects(root, projects);
  syncCapabilities(root, capabilities);
  syncJob(root, orchestration);
}

async function refresh() {
  if (refreshInFlight || document.hidden) return;
  refreshInFlight = true;

  try {
    applyStatus(await api("/api/status"));
  } catch (error) {
    const root = ensureRoot();
    setJobText(root, `Runtimefout: ${error.message}`);
  } finally {
    refreshInFlight = false;
  }
}

function scheduleRefresh(delay = STATUS_POLL_MS) {
  if (refreshTimer !== null) {
    window.clearTimeout(refreshTimer);
  }
  refreshTimer = window.setTimeout(async () => {
    await refresh();
    scheduleRefresh(STATUS_POLL_MS);
  }, delay);
}

function boot() {
  ensureRoot();
  refresh();
  scheduleRefresh(STATUS_POLL_MS);

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      if (refreshTimer !== null) {
        window.clearTimeout(refreshTimer);
        refreshTimer = null;
      }
      return;
    }
    refresh();
    scheduleRefresh(STATUS_POLL_MS);
  });
}

document.readyState === "loading"
  ? document.addEventListener("DOMContentLoaded", boot, { once: true })
  : boot();
})();
