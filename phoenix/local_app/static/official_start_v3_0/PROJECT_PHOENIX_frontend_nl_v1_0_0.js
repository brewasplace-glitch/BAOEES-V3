(() => {
"use strict";

// Frontend-only localization. Backend/API contracts remain English.
const EXACT = new Map([
  ["AUTONOMOUS PROJECT MODE", "AUTONOME PROJECTMODUS"],
  ["Autonomous Project Mode", "Autonome projectmodus"],
  ["SYSTEM STATUS", "SYSTEEMSTATUS"],
  ["System Status", "Systeemstatus"],
  ["Digital Twin", "Digitale Tweeling"],
  ["AI Agents", "AI-agenten"],
  ["Asset Management", "Assetbeheer"],
  ["Production", "Productievrijgave"],
  ["PAT PENDING · RELEASE LOCKED", "PAT IN AFWACHTING · VRIJGAVE GEBLOKKEERD"],
  ["RUNTIME CONNECTING", "RUNTIME VERBINDEN"],
  ["Session Adapter", "Sessieadapter"],
  ["Session-Driven Orchestrator", "Sessiegestuurde Orchestrator"],
  ["Desired Output", "Gewenste uitvoer"],
  ["Result Index", "Resultatenindex"],
  ["Project Bootstrap", "Projectinitialisatie"],
  ["Human Review Required", "Menselijke controle vereist"],
  ["Release Locked", "Vrijgave geblokkeerd"],
  ["Workflow", "Werkstroom"],
  ["Project Analysis", "Projectanalyse"],
  ["QA/QC", "Kwaliteitscontrole"],
]);

const STATUS = new Map([
  ["IDLE", "GEREED"],
  ["QUEUED", "IN WACHTRIJ"],
  ["PENDING", "WACHTEND"],
  ["RUNNING", "BEZIG"],
  ["PASSED", "GESLAAGD"],
  ["SUCCEEDED", "GESLAAGD"],
  ["BLOCKED", "GEBLOKKEERD"],
  ["FAILED", "MISLUKT"],
  ["UNKNOWN", "ONBEKEND"],
]);

const REASONS = new Map([
  ["DIMENSIONED_ARCHITECTURAL_MODEL_REQUIRED", "Maatvoerend architectuurmodel vereist"],
  ["CAD_BIM_IMPORT_ADAPTER_REQUIRED", "CAD/BIM-importkoppeling vereist"],
  ["ARCHITECTURAL_MODEL_NOT_AVAILABLE", "Architectuurmodel niet beschikbaar"],
  ["ARCHITECTURAL_MODEL_REQUIRED", "Architectuurmodel vereist"],
  ["DETAILED_ELEMENTS_REQUIRED", "Gedetailleerde bouwelementen vereist"],
  ["STRUCTURAL_PROJECT_PROFILE_REQUIRED", "Constructief projectprofiel vereist"],
  ["STRUCTURAL_V8_CHAIN_INCOMPLETE", "Constructieve v8-keten is onvolledig"],
  ["V8_1_TO_V8_12_VALIDATED_INPUT_MAPPING_REQUIRED", "Gevalideerde invoerkoppeling voor v8.1 t/m v8.12 vereist"],
  ["PROJECT_LOCATION_JURISDICTION_REQUIRED", "Projectlocatie en jurisdictie vereist"],
  ["RATEBOOK_REQUIRED", "Kostenkengetallen/ratebook vereist"],
  ["CURRENCY_REQUIRED", "Projectvaluta vereist"],
  ["BLOCKED_DEPENDENCY", "Geblokkeerd door afhankelijkheid"],
  ["SESSION_ADAPTER_RUNNER_MISSING", "Sessieadapter ontbreekt"],
  ["ADAPTER_RESULT_MISSING", "Resultaat van sessieadapter ontbreekt"],
  ["SESSION_ADAPTER_FAILED", "Sessieadapter mislukt"],
  ["UPSTREAM_NOT_PASSED", "Voorgaande stap niet geslaagd"],
  ["MISSING_GENERIC_CAPABILITY", "Generieke capability ontbreekt"],
  ["DISCOVERED_UNADAPTED", "Engine gevonden maar nog niet gekoppeld"],
]);

const PHRASES = [
  ["Autonomous Engineering & Infrastructure Intelligence Platform", "Autonoom Engineering- & Infrastructuurplatform"],
  ["Phoenix Autonomous Session-Driven Orchestrator", "Phoenix Autonome Sessiegestuurde Orchestrator"],
  ["Autonomous Session-Driven Orchestrator", "Autonome Sessiegestuurde Orchestrator"],
  ["Autonomous Project Mode", "Autonome projectmodus"],
  ["Session Adapter", "Sessieadapter"],
  ["Result Index", "Resultatenindex"],
  ["Production release", "Productievrijgave"],
  ["production release", "productievrijgave"],
  ["Release remains locked", "Vrijgave blijft geblokkeerd"],
  ["Workflow gestart", "Werkstroom gestart"],
  ["Workflow gereed", "Werkstroom gereed"],
  ["Workflow mislukt", "Werkstroom mislukt"],
  ["capability blocker(s)", "capability-blokkering(en)"],
  ["capability", "capability"], // technical architecture term intentionally retained
];

function skipNode(node){
  const p = node.parentElement;
  if (!p) return false;
  return !!p.closest('pre,code,kbd,samp,[data-phoenix-technical="true"]');
}

function translateToken(text){
  const trimmed = text.trim();
  if (EXACT.has(trimmed)) return text.replace(trimmed, EXACT.get(trimmed));
  if (STATUS.has(trimmed)) return text.replace(trimmed, STATUS.get(trimmed));
  if (REASONS.has(trimmed)) return text.replace(trimmed, REASONS.get(trimmed));
  let out = text;
  for (const [en,nl] of PHRASES) out = out.replaceAll(en,nl);
  // Translate status values only when they appear as standalone UI values after common labels.
  out = out.replace(/\bStatus:\s*(RUNNING|PASSED|SUCCEEDED|BLOCKED|FAILED|PENDING|QUEUED|IDLE)\b/g,
    (_,s) => `Status: ${STATUS.get(s) || s}`);
  return out;
}

function translateTextNode(node){
  if (skipNode(node)) return;
  const next = translateToken(node.nodeValue || '');
  if (next !== node.nodeValue) node.nodeValue = next;
}

function translateAttributes(el){
  for (const attr of ['placeholder','title','aria-label']) {
    if (!el.hasAttribute || !el.hasAttribute(attr)) continue;
    const before = el.getAttribute(attr) || '';
    const after = translateToken(before);
    if (after !== before) el.setAttribute(attr, after);
  }
}

function walk(root){
  if (!root) return;
  if (root.nodeType === Node.TEXT_NODE) { translateTextNode(root); return; }
  if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return;
  if (root.nodeType === Node.ELEMENT_NODE) translateAttributes(root);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  let n;
  while ((n = walker.nextNode())) {
    if (n.nodeType === Node.TEXT_NODE) translateTextNode(n);
    else translateAttributes(n);
  }
}

function installBadge(){
  if (document.getElementById('phoenixLanguageBadge')) return;
  const chips = document.querySelector('.topchips');
  if (!chips) return;
  const badge = document.createElement('div');
  badge.id = 'phoenixLanguageBadge';
  badge.className = 'chip';
  badge.textContent = 'TAAL · NEDERLANDS';
  badge.title = 'Gebruikersinterface: Nederlands. Technische backend-contracten: Engels.';
  chips.appendChild(badge);
}

function initial(){
  walk(document.body);
  installBadge();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initial, {once:true});
else initial();

// Translate only real DOM changes. This does not poll and does not alter backend data.
const observer = new MutationObserver(mutations => {
  for (const m of mutations) {
    if (m.type === 'characterData') translateTextNode(m.target);
    for (const node of m.addedNodes) walk(node);
  }
  installBadge();
});
observer.observe(document.documentElement, {subtree:true, childList:true, characterData:true});
})();
