# PHOENIX 4.41 — Embedded DXF open-source review

`dxf-viewer` 1.0.48 (MPL-2.0) was reviewed as a current browser-native WebGL DXF
viewer. Phoenix already has a proven ezdxf 1.4.4 SVG renderer on the target
machine, and the current failure is mount/handoff rather than DXF parsing.

Decision: keep ezdxf for this repair and fix the DE TV hard mount. This limits
change scope and preserves LibreCAD as the external fidelity fallback.
