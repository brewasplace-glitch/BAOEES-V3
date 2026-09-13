# PHOENIX 4.41 — LibreCAD Tolerant DXF→SVG Embedded Fallback v1.0

Prepared against baseline: `febf9003163fa32f77eb2d33fa76f755af6d5c34`

Status: **PREPARED — NOT EXECUTED**

## Proven reason for this fallback

The real `steel-beam-detail.dxf` is readable by LibreCAD but both ezdxf strict and
recover parsing fail on:

`missing 'AcDbPolyline' subclass in LWPOLYLINE(#None)`

The existing browser primitive fallback also depends on ezdxf parsing, so it
cannot recover this file.

## New render chain

1. ezdxf SVG;
2. ezdxf-derived browser primitive canvas;
3. **LibreCAD/libdxfrw `dxf2svg` tolerant conversion**;
4. external `Open in LibreCAD` only if all embedded paths fail.

The input DXF is never rewritten.

## Windows/LibreCAD 2.2.1.5 handling

LibreCAD 2.2.1.5 has a known `dxf2svg --outfile` problem when the output path is
absolute. Phoenix therefore supplies only a bare relative SVG filename. The
stable release resolves that filename beside the input DXF, so Phoenix performs
the conversion only on its session copy, verifies the SVG exists and is nonzero,
sanitizes it, and embeds that SVG into DE TV.

The installer also searches the latest failed real DXF session. If one is found,
it runs a non-mutating real-file conversion probe on a temporary copy before
commit/push.
