# PROJECT PHOENIX DE TV OPEN-SOURCE PLAYER ROBUST MOUNT + ACTIVATION REPAIR v1.0

Baseline: `7ac0fd28987241a8c568746c8b3a266d126a4ebd`.

Primary open-source engine: Xibo Player SDK.
Fallback candidate: Anthias.

The media sidecar on port 8770 and real PAT-002 PNG delivery are already proven. This repair therefore
does not rebuild media serving. It repairs only the browser-side activation layer.

The script first checks `/health`, then discovers the actual visible DE TV card using both the known
command input and semantic text/controls. It inserts the dedicated player iframe immediately above the
existing TV control block, hides only the legacy output/display area, and preserves the surrounding
Phoenix shell and controls.

A MutationObserver remounts the player if later Phoenix DOM regeneration removes it.
