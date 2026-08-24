(() => {
  'use strict';

  const LEVEL_A = 'A';
  const LEVEL_B = 'B';
  const STATE_A = 'A-PROFESSIONAL';
  const STATE_B_PENDING = 'B-PENDING';
  const STORE_PREFIX = 'phoenix.professionalOutputLevel.';
  const WORKFLOW = 'PHX.PROFESSIONAL_COUNTRY_AWARE_DESIGN_TO_CONSTRUCTION_COST_V1';
  const briefMarkerRe = /\n?\[PHOENIX_(?:PROFESSIONAL_OUTPUT_LEVEL_TARGET|COUNTRY_AWARE_COSTING|END_TO_END_MASTER_WORKFLOW)=[^\]]+\]\s*/g;

  const normalize = (value) => String(value || '').toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ').trim();

  const professionalPatterns = [
    /situat|site plan/,
    /plattegr|floor plan/,
    /gevel|elevation/,
    /doorsned|section/,
    /\b3d\b|viewer 3d|bim|ifc/,
    /construct|structur/,
    /bestek|specificat/,
    /hoeveel|quantit|takeoff/,
    /kosten|cost estimat/,
    /qa qc|qaqc|quality/,
    /bron|source|evidence|traceab/,
    /docx|pdf|rapport|report/,
    /dxf|dwg|cad/,
    /xlsx|excel/,
    /project zip|project_zip|eindpakket|final package/
  ];

  const formalPatterns = [
    /engineering review|review package|profession.*review/,
    /release package|vrijgave|release/,
    /revision|revisie|change impact/
  ];

  function projectKey() {
    const select = document.getElementById('projectSelect');
    return String(select && select.value ? select.value : 'NEW_PROJECT').trim() || 'NEW_PROJECT';
  }

  function storageKey() {
    return STORE_PREFIX + projectKey();
  }

  function getTarget() {
    const stored = localStorage.getItem(storageKey());
    return stored === LEVEL_B ? LEVEL_B : LEVEL_A;
  }

  function setTarget(level) {
    const target = level === LEVEL_B ? LEVEL_B : LEVEL_A;
    localStorage.setItem(storageKey(), target);
    updateUi(target);
    applyRequiredOutputs(target);
  }

  function catalogItems() {
    const groups = Array.isArray(window.PHOENIX_DESIRED_OUTPUTS) ? window.PHOENIX_DESIRED_OUTPUTS : [];
    const result = [];
    for (const group of groups) {
      for (const item of (group.items || [])) {
        if (!item || !item.id) continue;
        result.push({
          id: String(item.id),
          label: String(item.label || item.id),
          group: String(group.group || '')
        });
      }
    }
    return result;
  }

  function matchingOutputIds(level) {
    const patterns = level === LEVEL_B
      ? professionalPatterns.concat(formalPatterns)
      : professionalPatterns;
    const ids = [];
    for (const item of catalogItems()) {
      const haystack = normalize(`${item.id} ${item.label} ${item.group}`);
      if (patterns.some((pattern) => pattern.test(haystack)) && !ids.includes(item.id)) {
        ids.push(item.id);
      }
    }
    return ids;
  }

  function checkboxOutputId(cb) {
    const candidates = [
      cb.dataset && cb.dataset.outputId,
      cb.value,
      cb.name,
      cb.id
    ];
    const known = new Set(catalogItems().map((x) => x.id));
    for (const candidate of candidates) {
      const value = String(candidate || '').trim();
      if (known.has(value)) return value;
    }
    const row = cb.closest('.outputitem') || cb.parentElement;
    const text = normalize(row ? row.textContent : '');
    for (const item of catalogItems()) {
      const label = normalize(item.label);
      if (label && (text === label || text.includes(label))) return item.id;
    }
    return null;
  }

  function applyRequiredOutputs(level) {
    const wanted = new Set(matchingOutputIds(level));
    const root = document.getElementById('desiredOutputGroups');
    if (!root) return;
    for (const cb of root.querySelectorAll('input[type="checkbox"]')) {
      const id = checkboxOutputId(cb);
      if (id && wanted.has(id)) cb.checked = true;
    }
  }

  function stateLabel(level) {
    return level === LEVEL_B
      ? 'B-PENDING · formele review/release-gates vereist'
      : 'A-PROFESSIONAL · professionele projectoutput';
  }

  function updateUi(level) {
    const a = document.getElementById('phoenix-output-level-a');
    const b = document.getElementById('phoenix-output-level-b');
    const status = document.getElementById('phoenix-output-level-status');
    if (a) a.dataset.active = String(level === LEVEL_A);
    if (b) b.dataset.active = String(level === LEVEL_B);
    for (const card of [a, b]) {
      if (!card) continue;
      card.style.boxShadow = card.dataset.active === 'true'
        ? '0 0 0 2px #25b6ff,0 0 20px rgba(37,182,255,.18)'
        : 'none';
      card.style.borderColor = card.dataset.active === 'true' ? '#25b6ff' : '#1c446e';
    }
    if (status) status.textContent = stateLabel(level);
  }

  function installPanel() {
    if (document.getElementById('phoenix-professional-output-level-panel')) return;
    const outputRoot = document.getElementById('desiredOutputGroups');
    const outputPanel = outputRoot && outputRoot.closest('.panel');
    if (!outputPanel || !outputPanel.parentElement) return;

    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.id = 'phoenix-professional-output-level-panel';
    panel.innerHTML = `
      <div class="sectionlabel">
        <div class="badge">A/B</div>
        <div>OUTPUTNIVEAU PROJECT</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">
        <button type="button" id="phoenix-output-level-a"
          style="text-align:left;border:1px solid #1c446e;border-radius:14px;background:#071626;color:#eef7ff;padding:14px;cursor:pointer;min-height:124px">
          <strong style="display:block;font-size:16px;color:#73e0a3">A — PROFESSIONELE PROJECTOUTPUT</strong>
          <span style="display:block;margin-top:8px;color:#c9d8ea;font-size:12px">
            Ontwerp, tekeningen, constructie, constructierapport, bestek, bestekstekeningen,
            hoeveelheden, landspecifieke kostenraming, QA/QC en eindpakket.
            Geen formele uitvoeringsvrijgaveclaim.
          </span>
        </button>
        <button type="button" id="phoenix-output-level-b"
          style="text-align:left;border:1px solid #1c446e;border-radius:14px;background:#071626;color:#eef7ff;padding:14px;cursor:pointer;min-height:124px">
          <strong style="display:block;font-size:16px;color:#ffcd61">B — FORMEEL GECONTROLEERD / VOOR UITVOERING</strong>
          <span style="display:block;margin-top:8px;color:#c9d8ea;font-size:12px">
            Zelfde project doorzetten vanuit A. Phoenix start B-PENDING en houdt FOR CONSTRUCTION
            geblokkeerd totdat bestaande professionele review- en release-gates aantoonbaar zijn gesloten.
          </span>
        </button>
      </div>
      <div style="margin-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <span id="phoenix-output-level-status"
          style="padding:7px 10px;border:1px solid #31556f;border-radius:999px;background:#061522;color:#dceaf6;font-weight:700"></span>
        <span style="color:#8aa6c0;font-size:12px">
          Bij relevante wijziging na B-RELEASED: automatisch terug naar B-REVIEW-REQUIRED.
          Kostenraming gebruikt het land van het project; ontbrekende lokale prijsevidence blijft expliciet geblokkeerd.
        </span>
      </div>`;

    outputPanel.parentElement.insertBefore(panel, outputPanel);

    document.getElementById('phoenix-output-level-a')
      ?.addEventListener('click', () => setTarget(LEVEL_A));
    document.getElementById('phoenix-output-level-b')
      ?.addEventListener('click', () => setTarget(LEVEL_B));
    document.getElementById('projectSelect')
      ?.addEventListener('change', () => {
        const target = getTarget();
        updateUi(target);
        applyRequiredOutputs(target);
      });

    const target = getTarget();
    updateUi(target);
    setTimeout(() => applyRequiredOutputs(target), 0);
  }

  function addPayloadOutputs(payload, level) {
    const wanted = matchingOutputIds(level);
    const existing = Array.isArray(payload.desired_outputs)
      ? payload.desired_outputs.map(String)
      : [];
    payload.desired_outputs = Array.from(new Set(existing.concat(wanted)));
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = function(input, init) {
    try {
      const method = String((init && init.method) || 'GET').toUpperCase();
      if (method === 'POST' && init && typeof init.body === 'string') {
        const payload = JSON.parse(init.body);
        const looksLikeProjectStart = payload && typeof payload === 'object' && (
          typeof payload.brief === 'string' ||
          Array.isArray(payload.desired_outputs) ||
          payload.project_mode
        );
        if (looksLikeProjectStart) {
          const level = getTarget();
          payload.professional_output_level_target = level;
          payload.professional_output_state = level === LEVEL_B ? STATE_B_PENDING : STATE_A;
          payload.professional_end_to_end_workflow = WORKFLOW;
          payload.country_aware_costing_required = true;
          payload.formal_release_fail_closed = true;
          payload.automatic_professional_approval = false;
          payload.automatic_for_construction_release = false;
          payload.same_project_a_to_b = true;

          addPayloadOutputs(payload, level);

          if (typeof payload.brief === 'string') {
            const clean = payload.brief.replace(briefMarkerRe, '').trimEnd();
            payload.brief = clean +
              `\n\n[PHOENIX_PROFESSIONAL_OUTPUT_LEVEL_TARGET=${level}]` +
              '\n[PHOENIX_COUNTRY_AWARE_COSTING=REQUIRED]' +
              '\n[PHOENIX_END_TO_END_MASTER_WORKFLOW=v1.0]';
          }
          init = Object.assign({}, init, {body: JSON.stringify(payload)});
        }
      }
    } catch (_) {}
    return nativeFetch(input, init);
  };

  function setup() {
    installPanel();
    const observer = new MutationObserver(() => {
      if (!document.getElementById('phoenix-professional-output-level-panel')) installPanel();
    });
    observer.observe(document.documentElement, {childList:true, subtree:true});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setup, {once:true});
  } else {
    setup();
  }
})();