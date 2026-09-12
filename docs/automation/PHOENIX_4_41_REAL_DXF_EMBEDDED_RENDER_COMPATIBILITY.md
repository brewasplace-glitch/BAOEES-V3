# PHOENIX 4.41 — Real DXF Embedded Render Compatibility

Baseline: `38f9e0fe841b1d0a4c587772b618316a28746e05`

## Proven blocker

The selected DXF reaches the Phoenix session and opens correctly in LibreCAD, but
the embedded DE TV renderer returns `FAILED_DXF_RENDER`.

## Repair chain

1. Official ezdxf `SVGBackend` API with entity-by-entity exception isolation.
2. Legacy Phoenix `SVGRenderBackend`, also with entity-by-entity isolation.
3. Independent browser-canvas primitive fallback generated from the DXF modelspace
   without the SVG backend.
4. LibreCAD external fallback only if all embedded paths fail.

Each real file creates `render_diagnostics.json` in its Phoenix CAD session with:
- DXF version and strict/recover mode;
- entity inventory;
- primary renderer exceptions/tracebacks;
- skipped entity handles/types/layers;
- primitive fallback statistics.

The fallback is intentionally visual/read-only. It does not claim AutoCAD-perfect
fidelity and may simplify advanced entities.
