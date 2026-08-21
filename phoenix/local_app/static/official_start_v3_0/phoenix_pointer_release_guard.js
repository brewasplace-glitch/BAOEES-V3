/* PROJECT PHOENIX — start screen pointer-release guard v1.0
   Scope: official /start-v3/ shell only.
   Purpose: never allow the start page to trap the OS pointer.
*/
(() => {
  "use strict";

  const allowed = (node) =>
    !!node?.closest?.('[data-phoenix-allow-pointer-lock="true"]');

  const releaseUnexpectedPointerLock = () => {
    const locked = document.pointerLockElement;
    if (!locked || allowed(locked)) return;

    try {
      const result = document.exitPointerLock?.();
      if (result && typeof result.catch === "function") {
        result.catch(() => {});
      }
    } catch (_) {
      // The guard must never destabilize the start screen.
    }
  };

  document.addEventListener(
    "pointerlockchange",
    releaseUnexpectedPointerLock,
    { passive: true }
  );

  document.addEventListener(
    "pointerlockerror",
    releaseUnexpectedPointerLock,
    { passive: true }
  );

  window.addEventListener("blur", releaseUnexpectedPointerLock, { passive: true });
  document.addEventListener("visibilitychange", releaseUnexpectedPointerLock, { passive: true });

  releaseUnexpectedPointerLock();
})();
