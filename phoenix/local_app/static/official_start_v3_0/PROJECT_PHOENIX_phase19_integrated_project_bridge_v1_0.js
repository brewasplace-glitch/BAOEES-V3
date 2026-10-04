(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
  const token = window.PHOENIX_SESSION_TOKEN;

  async function post(path, body) {
    const response = await fetch(path, {
      method: "POST",
      cache: "no-store",
      headers: {"Content-Type":"application/json", "X-Phoenix-Token": token},
      body: JSON.stringify(body),
    });
    const value = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    return value;
  }

  function activeValue(selector, dataName, fallback) {
    const node = document.querySelector(`${selector}.active`) || document.querySelector(selector);
    return node?.dataset?.[dataName] || fallback;
  }

  function selectedOutputs() {
    return [...document.querySelectorAll(".desiredCheck:checked")].map(node => node.value).filter(Boolean);
  }

  function show(title, html) {
    $("modalTitle").textContent = title;
    $("modalBody").innerHTML = html;
    $("modal").style.display = "flex";
  }

  function stageTable(plan) {
    return `<div class="phx19-summary">
      <p><b>Run:</b> ${esc(plan.run_id)} · <b>Status:</b> ${esc(plan.status)}</p>
      <p><b>Autonomieniveau:</b> ${esc(plan.autonomy_level)} · <b>Disciplines:</b> ${esc(plan.discipline_plan?.engines?.length || 0)} · <b>Fasen:</b> ${esc(plan.stage_count)}</p>
      <p><b>Digital Twin:</b> ${esc(plan.shared_model)} · <b>Professionele vrijgave:</b> vereist, nog niet verleend</p>
      ${plan.missing_start_inputs?.length ? `<p class="warn"><b>Ontbrekende startinvoer:</b> ${plan.missing_start_inputs.map(esc).join(", ")}</p>` : ""}
      <h3>Varianten</h3>
      <p>Contract: exact vijf varianten. Phoenix maakt geen fictieve varianten; status: ${esc(plan.stages?.find(x => x.stage_id === "five_design_variants")?.status || "WACHT")}. Selectie: ${esc(plan.selected_variant_id || "nog niet gekozen")}.</p>
      <h3>Geintegreerde projectvoortgang</h3>
      <div style="overflow:auto"><table style="width:100%;border-collapse:collapse">
        <thead><tr><th style="text-align:left">#</th><th style="text-align:left">Fase</th><th style="text-align:left">Status</th><th style="text-align:left">Ontbrekend bewijs</th></tr></thead>
        <tbody>${(plan.stages || []).map(row => `<tr>
          <td>${esc(row.order)}</td><td>${esc(row.stage_id)}</td><td>${esc(row.status)}</td>
          <td>${esc((row.missing_evidence || []).join(", ") || "—")}</td>
        </tr>`).join("")}</tbody>
      </table></div>
      <p><b>Veiligheidsgrens:</b> geen output gefabriceerd, geen engine automatisch geactiveerd en geen professionele vrijgave uitgevoerd.</p>
    </div>`;
  }

  async function startIntegratedProject() {
    const button = $("startBtn");
    button.disabled = true;
    const original = button.textContent;
    button.textContent = "PROJECTORKESTRATIE STARTEN…";
    try {
      const session = await post("/api/project-analysis/start", {
        project_type: activeValue(".typecard", "type", "BOUW"),
        project_mode: activeValue(".modecard", "mode", "autonomous"),
        brief: $("brief")?.value || "",
        selected_project: $("projectSelect")?.value || "",
        desired_outputs: selectedOutputs(),
      });
      const plan = await post("/api/integrated-project/plan", {
        session_id: session.session_id,
        location_reference: "",
      });
      window.PHOENIX_PHASE19_LATEST_PLAN = plan;
      show("GEINTEGREERDE PROJECTORKESTRATIE", stageTable(plan));
    } catch (error) {
      show("PROJECTORKESTRATIE GEBLOKKEERD", `<p>${esc(error.message)}</p><p>Phoenix is fail-closed gestopt; er zijn geen technische resultaten gefabriceerd.</p>`);
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  function install() {
    const button = $("startBtn");
    if (!button || button.dataset.phase19Bridge === "1") return;
    button.dataset.phase19Bridge = "1";
    button.textContent = "START GEINTEGREERD PROJECT";
    button.onclick = startIntegratedProject;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})();
