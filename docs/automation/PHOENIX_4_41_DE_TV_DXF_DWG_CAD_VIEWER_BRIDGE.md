# PHOENIX 4.41 — DE TV DXF/DWG CAD Viewer Bridge

Adds **Project CAD** and **Open CAD bestand…** to the detected DE TV/start-page host.

- universal DXF/DWG selection from the normal operating-system file chooser;
- localhost-only sidecar on 127.0.0.1:8765;
- DXF -> SVG rendering with ezdxf 1.4.4;
- DWG -> DXF with GNU LibreDWG 0.14;
- external fallback: LibreCAD 2.2.1.5;
- zoom, pan and layer switching;
- project-scoped routing with a no-silent-guess quality gate;
- Open in LibreCAD.

If no authoritative active-project context can be resolved, recent CAD candidates
may be shown for explicit selection, but Phoenix does not claim they belong to the
active project.


## FIX R1 — Pillow dependency for embedded SVG rendering

The first real Windows execution successfully:
- resolved the authoritative DE TV host at
  `phoenix/local_app/static/official_start_v3_0/index.html`;
- patched and verified the DE TV host;
- verified LibreCAD, LibreDWG and the Phoenix CAD engine;
- passed the CAD engine self-test and DE TV patcher self-test.

The run stopped only when `ezdxf.addons.drawing` imported `PIL.Image`.
The isolated `cad_viewer_v1` runtime contained ezdxf but not Pillow.

FIX R1 makes Pillow 12.3.0 an explicit dependency of the DE TV embedded renderer,
installs it into the same isolated CAD runtime when absent, and verifies both
`PIL` and `PIL.Image` before the sidecar is started.

No DE TV routing, CAD semantics or repository baseline is changed.


## FIX R2 — Windows PowerShell `$Host` collision

FIX R1 stopped in the interrupted-install recovery block because the installer
used a local variable named `$host`. PowerShell variable names are
case-insensitive and `$Host` is a built-in read-only automatic variable.

FIX R2 renames the local recovery variable to `$hostFile` and adds a static
guard against assigning to `$Host`. The Pillow 12.3.0 runtime repair from FIX R1
is preserved unchanged.

No CAD behavior, DE TV routing, host selection, or repository baseline changes.
