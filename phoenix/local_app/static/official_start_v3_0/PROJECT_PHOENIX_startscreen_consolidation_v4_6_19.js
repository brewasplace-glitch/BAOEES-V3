(() => {
  "use strict";

  const TECHNICAL_NAV_MODULES = new Set([
    "digital_twin",
    "ai_agents",
    "simulations",
    "documents",
    "reports",
    "asset_management",
    "dashboard"
  ]);

  let managementOpen = false;

  function q(id) {
    return document.getElementById(id);
  }

  function setTechnicalNavVisibility() {
    document.querySelectorAll("#leftNav .navbtn[data-module]").forEach((button) => {
      const moduleId = String(button.dataset.module || "");
      if (TECHNICAL_NAV_MODULES.has(moduleId)) {
        button.hidden = true;
        button.setAttribute("aria-hidden", "true");
      }
    });
  }

  function setAdminPanels(open) {
    managementOpen = Boolean(open);

    const modules = q("phoenixModulesPanel");
    const workflows = q("phoenixWorkflowsPanel");
    [modules, workflows].forEach((panel) => {
      if (!panel) return;
      panel.hidden = !managementOpen;
      panel.open = managementOpen;
      panel.setAttribute("aria-hidden", managementOpen ? "false" : "true");
    });

    const drawer = q("phoenix-start-capability-drawer");
    if (drawer) {
      drawer.hidden = !managementOpen;
      drawer.setAttribute("aria-hidden", managementOpen ? "false" : "true");
    }

    const manage = q("phoenixManageNav") ||
      document.querySelector('#leftNav .navbtn[data-module="settings"]');
    if (manage) {
      manage.classList.toggle("active", managementOpen);
      manage.setAttribute("aria-expanded", managementOpen ? "true" : "false");
      manage.title = managementOpen
        ? "Sluit technische beheerfuncties"
        : "Open technische beheerfuncties";
    }
  }

  function bindManagement() {
    const manage = q("phoenixManageNav") ||
      document.querySelector('#leftNav .navbtn[data-module="settings"]');
    if (!manage || manage.dataset.phxConsolidationBound === "1") return;

    manage.dataset.phxConsolidationBound = "1";
    manage.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      setAdminPanels(!managementOpen);
    }, true);
  }

  function normalizeVisibleLabels() {
    const tvTitle = document.querySelector("#phoenixTvPanel .tvtitle span:last-child");
    if (tvTitle) {
      tvTitle.textContent = "DE TV Â· DIGITAL TWIN / RESULTATEN";
    }

    const projectsHeading = Array.from(document.querySelectorAll(".sidepanel h2"))
      .find((node) => String(node.textContent || "").trim() === "Projecten");
    if (projectsHeading) {
      projectsHeading.textContent = "Projecten";
    }
  }

  function apply() {
    setTechnicalNavVisibility();
    bindManagement();
    normalizeVisibleLabels();
    setAdminPanels(managementOpen);
    document.documentElement.setAttribute("data-phoenix-startscreen-consolidation", "4.6.19-r1");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply, { once: true });
  } else {
    apply();
  }

  // The capability drawer is mounted asynchronously; keep it behind Beheer.
  const observer = new MutationObserver(() => {
    const drawer = q("phoenix-start-capability-drawer");
    if (drawer) setAdminPanels(managementOpen);
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.PHOENIX_STARTSCREEN_CONSOLIDATION = Object.freeze({
    version: "4.6.19-r1",
    openManagement: () => setAdminPanels(true),
    closeManagement: () => setAdminPanels(false)
  });
})();