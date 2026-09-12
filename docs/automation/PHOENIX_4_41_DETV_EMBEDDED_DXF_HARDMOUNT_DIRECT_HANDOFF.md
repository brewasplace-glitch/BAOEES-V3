# PHOENIX 4.41 — DE TV Embedded DXF Viewer Hard-Mount + Direct File Handoff

Baseline: `908840c9c1db8d8eea0a57c7b3b57b6e6684b5d9`

The real `steel-beam-detail.dxf` test proved file selection, Phoenix session
storage and LibreCAD fallback. The remaining blocker is visual: the drawing must
appear in the DE TV output area itself.

This repair removes the body-level CAD modal and hard-mounts a compact CAD iframe
inside the DE TV output viewport. The selected file is queued until the iframe
sends `phoenix-cad-viewer-ready`; only then is the File object handed off. The
viewer replies with `phoenix-cad-file-loaded` or `phoenix-cad-file-error`.

Message origins are validated. LibreCAD remains an optional external fallback.
