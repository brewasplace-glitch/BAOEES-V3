(() => {
"use strict";
const DATA_URL="phoenix_start_screen_runtime.json", PANEL_ID="phoenix-v3-system-deck";
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
function stateClass(v){const s=String(v||"").toUpperCase();if(s.includes("READY")||s.includes("PASSED")||s.includes("ACTIVE")||s.includes("CLEAN")||s.includes("SYNCHRONIZED"))return"phx3-good";if(s.includes("LOCKED")||s.includes("PENDING")||s.includes("REQUIRED")||s.includes("CHECK"))return"phx3-warn";return"phx3-neutral";}
function styles(){if(document.getElementById("phoenix-v3-style"))return;const s=document.createElement("style");s.id="phoenix-v3-style";s.textContent=`
:root{--phx3-panel:rgba(14,18,26,.90);--phx3-card:rgba(255,255,255,.055);--phx3-border:rgba(180,196,220,.18);--phx3-muted:rgba(229,235,244,.68);--phx3-good:#83e6ad;--phx3-warn:#ffd166}
#${PANEL_ID}{max-width:1240px;margin:18px auto 28px;padding:22px 22px 18px;border:1px solid var(--phx3-border);border-radius:20px;background:var(--phx3-panel);box-shadow:0 20px 70px rgba(0,0,0,.25);backdrop-filter:blur(12px);color:#eef4fb;font-family:inherit}
#${PANEL_ID} *{box-sizing:border-box}#${PANEL_ID} .phx3-top{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}#${PANEL_ID} .phx3-brand{display:flex;gap:14px;align-items:center}
#${PANEL_ID} .phx3-mark{width:44px;height:44px;border-radius:14px;border:1px solid var(--phx3-border);display:grid;place-items:center;font-weight:800;background:rgba(255,255,255,.055)}
#${PANEL_ID} h1{font-size:1.28rem;line-height:1.15;margin:0;letter-spacing:.025em}#${PANEL_ID} .phx3-sub{margin-top:5px;font-size:.82rem;color:var(--phx3-muted)}
#${PANEL_ID} .phx3-live{font-size:.74rem;padding:7px 10px;border:1px solid var(--phx3-border);border-radius:999px;color:var(--phx3-good)}
#${PANEL_ID} .phx3-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px}
#${PANEL_ID} .phx3-card{min-height:76px;padding:13px 14px;border:1px solid var(--phx3-border);border-radius:14px;background:var(--phx3-card)}
#${PANEL_ID} .phx3-label{font-size:.68rem;text-transform:uppercase;letter-spacing:.085em;color:var(--phx3-muted)}
#${PANEL_ID} .phx3-value{margin-top:7px;font-weight:720;line-height:1.25;overflow-wrap:anywhere}
#${PANEL_ID} .phx3-good{color:var(--phx3-good)}#${PANEL_ID} .phx3-warn{color:var(--phx3-warn)}
#${PANEL_ID} .phx3-chain{margin-top:15px;padding-top:13px;border-top:1px solid var(--phx3-border)}
#${PANEL_ID} .phx3-chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px}#${PANEL_ID} .phx3-chip{padding:6px 9px;border-radius:999px;border:1px solid var(--phx3-border);background:rgba(255,255,255,.04);font-size:.72rem}
#${PANEL_ID} .phx3-footer{margin-top:13px;font-size:.7rem;color:var(--phx3-muted);line-height:1.45}
@media(max-width:900px){#${PANEL_ID} .phx3-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:540px){#${PANEL_ID} .phx3-grid{grid-template-columns:1fr}}`;document.head.appendChild(s);}
const card=(l,v)=>`<div class="phx3-card"><div class="phx3-label">${esc(l)}</div><div class="phx3-value ${stateClass(v)}">${esc(v)}</div></div>`;
function render(d){document.getElementById(PANEL_ID)?.remove();styles();const r=d.repository||{},p=d.product_status||{},a=d.automation||{},ch=Array.isArray(d.structural_chain)?d.structural_chain:[];const e=document.createElement("section");e.id=PANEL_ID;e.innerHTML=`
<div class="phx3-top"><div class="phx3-brand"><div class="phx3-mark">P3</div><div><h1>PROJECT PHOENIX 3.0</h1><div class="phx3-sub">Official Start Screen · Digital Twin · Autonomous Engineering · Controlled Release</div></div></div><div class="phx3-live">AUTOSYNC ACTIVE</div></div>
<div class="phx3-grid">${card("Repository",r.clean?"CLEAN":"CHANGES DETECTED")}${card("Branch",r.branch||"UNKNOWN")}${card("Local / Remote",r.local_remote_synchronized?"SYNCHRONIZED":"CHECK REQUIRED")}${card("Structural chain",p.structural_chain_closed_through||"NOT DETECTED")}${card("Building / Structural",p.building_structural_candidate||"UNKNOWN")}${card("Production Acceptance Test",p.production_acceptance_test||"UNKNOWN")}${card("Production Release",p.production_release||"UNKNOWN")}${card("Module registration",a.manual_dashboard_registration_required?"MANUAL":"AUTOMATIC")}</div>
<div class="phx3-chain"><div class="phx3-label">Structural engineering lifecycle detected from repository</div><div class="phx3-chips">${ch.map(x=>`<span class="phx3-chip">${esc(x.version)} · ${esc(x.name)}</span>`).join("")||`<span class="phx3-chip">No v8.x structural engines detected</span>`}</div></div>
<div class="phx3-footer">Latest repository state: ${esc(r.head||"UNKNOWN")} · ${esc(r.head_subject||"")}<br>Runtime status generated: ${esc(d.generated_utc||"UNKNOWN")}</div>`;const m=document.querySelector("main");m&&m.parentNode?m.parentNode.insertBefore(e,m):document.body.insertBefore(e,document.body.firstChild);}
async function load(){try{const r=await fetch(`${DATA_URL}?t=${Date.now()}`,{cache:"no-store"});if(!r.ok)throw new Error(`HTTP ${r.status}`);render(await r.json());}catch(e){console.warn("Phoenix 3.0 runtime status could not be loaded:",e);}}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",load,{once:true}):load();
})();