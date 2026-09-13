# PHOENIX 4.41 — LibreCAD DXF→SVG open-source review

LibreCAD is GPL-2.0 and uses libdxfrw for DXF/DWG input. Its official repository
documents `librecad dxf2svg foo.dxf`.

For stable LibreCAD 2.2.1.5 on Windows, upstream issue #2801 documents that an
absolute `--outfile` for dxf2svg/dxf2png may silently produce no file. A bare
relative output filename works and is resolved beside the input DXF.

Phoenix therefore:
- reuses the already installed LibreCAD 2.2.1.5;
- supplies a bare relative output filename;
- runs against a Phoenix session copy, not the user's source file;
- verifies output existence/size instead of trusting exit code 0;
- sanitizes the generated SVG before DE TV embedding.
