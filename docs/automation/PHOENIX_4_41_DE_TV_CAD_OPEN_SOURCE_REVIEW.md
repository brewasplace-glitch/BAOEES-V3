# PHOENIX 4.41 — DE TV CAD open-source review

Evaluated:
- dxf-viewer 1.0.48 — MPL-2.0, WebGL/three.js, current browser DXF viewer.
- dxf-parser 1.1.2 — MIT, mature JavaScript DXF parser.

Selected for v1.0: reuse the already validated Phoenix stack:
- ezdxf 1.4.4;
- GNU LibreDWG 0.14;
- LibreCAD 2.2.1.5.

Reason: avoids introducing a second CAD parser/rendering pipeline while still
providing an embedded DE TV view. Browser-native file selection is used only as
thin UI glue.
