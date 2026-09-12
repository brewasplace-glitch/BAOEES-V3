# PHOENIX 4.41 — DXF render open-source review

## ezdxf 1.4.4
MIT licensed. The documented Drawing add-on supports an SVG backend, and Phoenix
already has this exact runtime installed.

Selected for:
- resilient SVG primary rendering;
- recover-mode parsing;
- entity inventory;
- primitive extraction for the browser-canvas fallback.

## dxf-viewer 1.0.48
MPL-2.0 JavaScript/WebGL viewer using three.js. It remains a valid future
high-performance browser renderer.

Deferred in this repair because the current target already has a working ezdxf
runtime and the proven failure is inside the existing SVG path. Adding npm,
three.js, opentype.js and bundling would broaden the change surface before the
actual failing entity/renderer path has been diagnosed.
