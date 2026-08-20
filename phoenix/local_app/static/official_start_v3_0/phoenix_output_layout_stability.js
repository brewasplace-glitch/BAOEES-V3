/* PROJECT PHOENIX — official start screen output layout + pointer stability v1.0 */
(() => {
  "use strict";

  const normalize = (value) =>
    String(value || "")
      .replace(/\s+/g, " ")
      .trim()
      .toUpperCase();

  const candidates = () =>
    Array.from(
      document.querySelectorAll(
        "button, [role='button'], label, h1, h2, h3, h4, span, strong, div"
      )
    );

  const findByLabels = (labels) => {
    const wanted = labels.map(normalize);
    const nodes = candidates();

    for (const exact of wanted) {
      const node = nodes.find((el) => normalize(el.textContent) === exact);
      if (node) return node;
    }

    for (const exact of wanted) {
      const node = nodes.find((el) => {
        const text = normalize(el.textContent);
        return text && text.includes(exact) && text.length <= exact.length + 40;
      });
      if (node) return node;
    }

    return null;
  };

  const findChoiceCard = (node) => {
    if (!node) return null;
    let current = node;

    for (let depth = 0; current && depth < 7; depth += 1) {
      const classText = normalize(current.className);
      const tag = normalize(current.tagName);

      if (
        tag === "BUTTON" ||
        current.getAttribute?.("role") === "button" ||
        /CARD|TILE|OPTION|CHOICE|OUTPUT|MODE|FLOW/.test(classText)
      ) {
        return current;
      }
      current = current.parentElement;
    }

    return node.parentElement;
  };

  const placeOutputModes = () => {
    if (document.getElementById("phoenix-output-mode-row")) return true;

    const heading = findByLabels(["GEWENSTE OUTPUT"]);
    const standardNode = findByLabels([
      "MIJN STANDAARD",
      "PHOENIX STANDAARD",
      "STANDAARD"
    ]);
    const flowNode = findByLabels([
      "AUTONOME PHOENIX-FLOW",
      "AUTONOME PHOENIX FLOW"
    ]);

    if (!heading || !standardNode || !flowNode) return false;

    const standardCard = findChoiceCard(standardNode);
    const flowCard = findChoiceCard(flowNode);

    if (!standardCard || !flowCard || standardCard === flowCard) return false;
    if (standardCard.contains(flowCard) || flowCard.contains(standardCard)) return false;

    const row = document.createElement("div");
    row.id = "phoenix-output-mode-row";
    row.className = "phoenix-output-mode-row";
    row.setAttribute("data-phoenix-output-layout", "standard-plus-autonomous-flow");

    heading.insertAdjacentElement("afterend", row);

    standardCard.classList.add("phoenix-output-choice");
    flowCard.classList.add("phoenix-output-choice");

    row.append(standardCard, flowCard);
    return true;
  };

  const initialize = () => {
    document.documentElement.classList.add("phoenix-pointer-stable");

    let attempts = 0;
    const maxAttempts = 24;

    const tryOnce = () => {
      if (placeOutputModes()) return;
      attempts += 1;
      if (attempts < maxAttempts) {
        window.setTimeout(tryOnce, 150);
      }
    };

    tryOnce();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
