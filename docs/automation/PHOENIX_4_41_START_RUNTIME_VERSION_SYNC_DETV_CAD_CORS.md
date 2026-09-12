# PHOENIX 4.41 — Start Runtime Version Sync + DE TV CAD Browser CORS Fix

Baseline: `e7bd5eead42092fa3876c0abd2a29f216e631fea`

This block repairs only two visible/runtime issues:

1. visible start-shell labels are synchronized from `START v3.0.2` to
   `START v4.41`, while the engine runtime value such as `v1.8.7` is preserved;
2. the loopback CAD sidecar returns allowlisted CORS headers for the Phoenix
   start application at port 8766.

The CAD sidecar remains bound to `127.0.0.1:8765`.

Allowed origins:
- `http://127.0.0.1:8766`
- `http://localhost:8766`

No wildcard origin is enabled.

`PLAYER OFFLINE` belongs to the existing media-player path and is intentionally
out of scope for this repair.
