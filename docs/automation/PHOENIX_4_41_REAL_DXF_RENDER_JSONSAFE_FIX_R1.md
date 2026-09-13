# PHOENIX 4.41 — Real DXF Render JSON-Safe FIX R1

Baseline: `40f195f63055792a894154d89bfcce1c5a70a489`

The real DE TV test exposed `Object of type WindowsPath is not JSON serializable`.

That exception is in the renderer failure/diagnostics path. It masks the real DXF
renderer error. FIX R1 converts all `Path` values to strings before diagnostics
or HTTP JSON serialization and adds a forced dual-render-failure regression test.

The DXF render chain, DE TV hard-mount, CORS and LibreCAD fallback are unchanged.
