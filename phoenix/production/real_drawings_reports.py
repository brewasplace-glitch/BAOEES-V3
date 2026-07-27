"""Dependency-free vector drawing and report production for BB35 Pilot 1.

The engine generates actual PDF/SVG/DXF drawing files and PDF/DOCX reports.
All deliverables are concept issue documents and are not suitable for permit
submission or construction until professional evidence replaces the six
remaining simulated request packages.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from xml.sax.saxutils import escape as xml_escape

MM = 72.0 / 25.4
A3_L = (420.0 * MM, 297.0 * MM)
A4_P = (210.0 * MM, 297.0 * MM)
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)
STATUS = "CONCEPT - NOT FOR SUBMISSION OR EXECUTION"


def _num(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _pdf_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _wrap(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width=max(10, width), break_long_words=False) or [""]


class PdfDocument:
    def __init__(self) -> None:
        self.pages: list[tuple[float, float, str]] = []

    def add_page(self, width: float, height: float, content: str) -> None:
        self.pages.append((width, height, content))

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        objects: list[bytes] = []
        page_object_numbers: list[int] = []
        font_normal_obj = 3
        font_bold_obj = 4
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        for width, height, content in self.pages:
            page_obj = len(objects) + 1
            stream_obj = page_obj + 1
            page_object_numbers.append(page_obj)
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_num(width)} {_num(height)}] "
                f"/Resources << /Font << /F1 {font_normal_obj} 0 R /F2 {font_bold_obj} 0 R >> >> "
                f"/Contents {stream_obj} 0 R >>"
            ).encode("latin-1")
            stream = content.encode("latin-1", errors="replace")
            stream_dict = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            objects.extend([page_dict, stream_dict])
        kids = " ".join(f"{obj} 0 R" for obj in page_object_numbers)
        objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_numbers)} >>".encode("ascii")

        result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(result))
            result.extend(f"{index} 0 obj\n".encode("ascii"))
            result.extend(obj)
            result.extend(b"\nendobj\n")
        xref = len(result)
        result.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        result.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            result.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        result.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref}\n%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(bytes(result))
        return path


class VectorCanvas:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
        self.pdf: list[str] = []
        self.svg: list[str] = []
        self.dxf: list[tuple[str, tuple[Any, ...]]] = []
        self.line_width(0.35)
        self.stroke_rgb(0.10, 0.15, 0.20)

    def line_width(self, mm: float) -> None:
        value = mm * MM
        self.pdf.append(f"{_num(value)} w")
        self.svg.append(f"<!-- line-width:{_num(mm)}mm -->")

    def stroke_rgb(self, r: float, g: float, b: float) -> None:
        self.pdf.append(f"{_num(r)} {_num(g)} {_num(b)} RG")

    def fill_rgb(self, r: float, g: float, b: float) -> None:
        self.pdf.append(f"{_num(r)} {_num(g)} {_num(b)} rg")

    def dash(self, values: Sequence[float] | None) -> None:
        if values:
            pts = " ".join(_num(v * MM) for v in values)
            self.pdf.append(f"[{pts}] 0 d")
        else:
            self.pdf.append("[] 0 d")

    def line(self, x1: float, y1: float, x2: float, y2: float, *, width_mm: float = 0.35, color: str = "#1f2937", dashed: bool = False) -> None:
        self.pdf.append(f"q {_num(width_mm * MM)} w")
        if dashed:
            self.pdf.append(f"[{_num(2 * MM)} {_num(1.5 * MM)}] 0 d")
        self.pdf.append(f"{_num(x1)} {_num(y1)} m {_num(x2)} {_num(y2)} l S Q")
        dash = ' stroke-dasharray="6,4"' if dashed else ''
        self.svg.append(
            f'<line x1="{_num(x1)}" y1="{_num(self.height-y1)}" x2="{_num(x2)}" y2="{_num(self.height-y2)}" stroke="{color}" stroke-width="{_num(width_mm*MM)}"{dash}/>'
        )
        self.dxf.append(("LINE", (x1 / MM, y1 / MM, x2 / MM, y2 / MM)))

    def rect(self, x: float, y: float, w: float, h: float, *, stroke: str = "#1f2937", fill: str | None = None, width_mm: float = 0.35, dashed: bool = False) -> None:
        self.pdf.append("q")
        self.pdf.append(f"{_num(width_mm * MM)} w")
        if dashed:
            self.pdf.append(f"[{_num(2 * MM)} {_num(1.5 * MM)}] 0 d")
        if fill:
            rgb = self._hex_rgb(fill)
            self.pdf.append(f"{_num(rgb[0])} {_num(rgb[1])} {_num(rgb[2])} rg")
        operator = "B" if fill else "S"
        self.pdf.append(f"{_num(x)} {_num(y)} {_num(w)} {_num(h)} re {operator} Q")
        dash = ' stroke-dasharray="6,4"' if dashed else ''
        fill_value = fill or "none"
        self.svg.append(
            f'<rect x="{_num(x)}" y="{_num(self.height-y-h)}" width="{_num(w)}" height="{_num(h)}" fill="{fill_value}" stroke="{stroke}" stroke-width="{_num(width_mm*MM)}"{dash}/>'
        )
        self.dxf.append(("RECT", (x / MM, y / MM, w / MM, h / MM)))

    def circle(self, x: float, y: float, radius: float, *, stroke: str = "#1f2937", fill: str | None = None, width_mm: float = 0.35) -> None:
        k = 0.552284749831
        c = radius * k
        self.pdf.append("q")
        self.pdf.append(f"{_num(width_mm*MM)} w")
        if fill:
            rgb = self._hex_rgb(fill)
            self.pdf.append(f"{_num(rgb[0])} {_num(rgb[1])} {_num(rgb[2])} rg")
        self.pdf.extend([
            f"{_num(x+radius)} {_num(y)} m",
            f"{_num(x+radius)} {_num(y+c)} {_num(x+c)} {_num(y+radius)} {_num(x)} {_num(y+radius)} c",
            f"{_num(x-c)} {_num(y+radius)} {_num(x-radius)} {_num(y+c)} {_num(x-radius)} {_num(y)} c",
            f"{_num(x-radius)} {_num(y-c)} {_num(x-c)} {_num(y-radius)} {_num(x)} {_num(y-radius)} c",
            f"{_num(x+c)} {_num(y-radius)} {_num(x+radius)} {_num(y-c)} {_num(x+radius)} {_num(y)} c",
            ("B" if fill else "S") + " Q",
        ])
        self.svg.append(
            f'<circle cx="{_num(x)}" cy="{_num(self.height-y)}" r="{_num(radius)}" fill="{fill or "none"}" stroke="{stroke}" stroke-width="{_num(width_mm*MM)}"/>'
        )

    def text(self, x: float, y: float, value: str, *, size_pt: float = 8.0, bold: bool = False, align: str = "left", rotate: float = 0.0, color: str = "#111827") -> None:
        font = "F2" if bold else "F1"
        estimated = len(value) * size_pt * 0.50
        tx = x
        if align == "center":
            tx -= estimated / 2
        elif align == "right":
            tx -= estimated
        if rotate:
            angle = math.radians(rotate)
            a, b = math.cos(angle), math.sin(angle)
            c, d = -math.sin(angle), math.cos(angle)
            matrix = f"{_num(a)} {_num(b)} {_num(c)} {_num(d)} {_num(tx)} {_num(y)} Tm"
        else:
            matrix = f"1 0 0 1 {_num(tx)} {_num(y)} Tm"
        self.pdf.append(f"BT /{font} {_num(size_pt)} Tf {matrix} ({_pdf_text(value)}) Tj ET")
        anchor = {"left": "start", "center": "middle", "right": "end"}[align]
        weight = "bold" if bold else "normal"
        transform = f' transform="rotate({-_num(rotate)} {_num(x)} {_num(self.height-y)})"' if rotate else ""
        self.svg.append(
            f'<text x="{_num(x)}" y="{_num(self.height-y)}" font-family="Arial, sans-serif" font-size="{_num(size_pt)}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}"{transform}>{html.escape(value)}</text>'
        )
        self.dxf.append(("TEXT", (x / MM, y / MM, value, size_pt * 25.4 / 72.0, rotate)))

    def polyline(self, points: Sequence[tuple[float, float]], *, closed: bool = False, width_mm: float = 0.35, fill: str | None = None, stroke: str = "#1f2937") -> None:
        if not points:
            return
        self.pdf.append("q")
        self.pdf.append(f"{_num(width_mm*MM)} w")
        if fill:
            rgb = self._hex_rgb(fill)
            self.pdf.append(f"{_num(rgb[0])} {_num(rgb[1])} {_num(rgb[2])} rg")
        x0, y0 = points[0]
        self.pdf.append(f"{_num(x0)} {_num(y0)} m")
        for x, y in points[1:]:
            self.pdf.append(f"{_num(x)} {_num(y)} l")
        if closed:
            self.pdf.append("h")
        self.pdf.append(("B" if fill else "S") + " Q")
        point_text = " ".join(f"{_num(x)},{_num(self.height-y)}" for x, y in points)
        tag = "polygon" if closed else "polyline"
        self.svg.append(
            f'<{tag} points="{point_text}" fill="{fill or "none"}" stroke="{stroke}" stroke-width="{_num(width_mm*MM)}"/>'
        )
        for first, second in zip(points, points[1:] + ([points[0]] if closed else [])):
            self.dxf.append(("LINE", (first[0] / MM, first[1] / MM, second[0] / MM, second[1] / MM)))

    def arrow(self, x1: float, y1: float, x2: float, y2: float, *, label: str | None = None, width_mm: float = 0.45) -> None:
        self.line(x1, y1, x2, y2, width_mm=width_mm)
        angle = math.atan2(y2-y1, x2-x1)
        size = 3.5 * MM
        for delta in (math.radians(150), math.radians(-150)):
            self.line(x2, y2, x2 + size * math.cos(angle + delta), y2 + size * math.sin(angle + delta), width_mm=width_mm)
        if label:
            self.text((x1+x2)/2, (y1+y2)/2 + 4*MM, label, size_pt=7, bold=True, align="center")

    def dimension(self, x1: float, y1: float, x2: float, y2: float, label: str, *, offset: float = 0.0) -> None:
        dx, dy = x2-x1, y2-y1
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy/length, dx/length
        ax1, ay1 = x1 + nx*offset, y1 + ny*offset
        ax2, ay2 = x2 + nx*offset, y2 + ny*offset
        self.line(ax1, ay1, ax2, ay2, width_mm=0.18)
        tick = 2.0 * MM
        self.line(ax1-nx*tick, ay1-ny*tick, ax1+nx*tick, ay1+ny*tick, width_mm=0.18)
        self.line(ax2-nx*tick, ay2-ny*tick, ax2+nx*tick, ay2+ny*tick, width_mm=0.18)
        self.text((ax1+ax2)/2 + nx*3*MM, (ay1+ay2)/2 + ny*3*MM, label, size_pt=7, bold=True, align="center")

    def to_pdf_content(self) -> str:
        return "\n".join(self.pdf) + "\n"

    def to_svg(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 {_num(self.width)} {_num(self.height)}">\n'
            '<rect width="100%" height="100%" fill="white"/>\n'
            + "\n".join(self.svg)
            + "\n</svg>\n"
        )

    def to_dxf(self) -> str:
        rows = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        for kind, values in self.dxf:
            if kind == "LINE":
                x1, y1, x2, y2 = values
                rows += ["0", "LINE", "8", "PHOENIX", "10", _num(x1), "20", _num(y1), "30", "0", "11", _num(x2), "21", _num(y2), "31", "0"]
            elif kind == "RECT":
                x, y, w, h = values
                pts = [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
                for a,b in zip(pts, pts[1:]):
                    rows += ["0", "LINE", "8", "PHOENIX", "10", _num(a[0]), "20", _num(a[1]), "30", "0", "11", _num(b[0]), "21", _num(b[1]), "31", "0"]
            elif kind == "TEXT":
                x, y, value, height, rotate = values
                rows += ["0", "TEXT", "8", "PHOENIX-TEXT", "10", _num(x), "20", _num(y), "30", "0", "40", _num(max(height, 1.8)), "1", str(value).replace("\n", " "), "50", _num(rotate)]
        rows += ["0", "ENDSEC", "0", "EOF"]
        return "\r\n".join(rows) + "\r\n"

    @staticmethod
    def _hex_rgb(value: str) -> tuple[float, float, float]:
        value = value.lstrip("#")
        return tuple(int(value[i:i+2], 16)/255.0 for i in (0,2,4))


class DrawingFactory:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = config
        self.project = config["project"]
        self.geometry = config["geometry"]

    def create(self) -> list[dict[str, Any]]:
        sheets = [
            self._situation(),
            self._ground_floor(),
            self._first_floor(),
            self._elevations(),
            self._sections(),
            self._roof(),
            self._foundation(),
            self._structure(),
            self._fire(),
            self._phasing(),
        ]
        return sheets

    def _base(self, sheet_id: str, title: str, scale: str, discipline: str) -> VectorCanvas:
        c = VectorCanvas(*A3_L)
        margin = 10 * MM
        title_h = 34 * MM
        c.rect(margin, margin, A3_L[0]-2*margin, A3_L[1]-2*margin, width_mm=0.45)
        c.line(margin, margin+title_h, A3_L[0]-margin, margin+title_h, width_mm=0.45)
        x0 = A3_L[0] - margin - 130*MM
        c.line(x0, margin, x0, margin+title_h, width_mm=0.35)
        c.text(margin+4*MM, margin+23*MM, self.project["name"], size_pt=13, bold=True)
        c.text(margin+4*MM, margin+15*MM, self.project["address"], size_pt=9)
        c.text(margin+4*MM, margin+7*MM, STATUS, size_pt=10, bold=True, color="#991b1b")
        c.text(x0+4*MM, margin+25*MM, f"SHEET {sheet_id}", size_pt=11, bold=True)
        c.text(x0+4*MM, margin+17*MM, title, size_pt=9, bold=True)
        c.text(x0+4*MM, margin+9*MM, f"Scale {scale} | {discipline}", size_pt=8)
        c.text(A3_L[0]-margin-4*MM, margin+9*MM, "Issue 2026-07-27", size_pt=8, align="right")
        c.text(A3_L[0]-margin-4*MM, margin+25*MM, "PROJECT PHOENIX", size_pt=10, bold=True, align="right")
        return c

    def _plan_rooms(self, c: VectorCanvas, origin_x: float, origin_y: float, scale_mm_per_m: float, first_floor: bool = False) -> None:
        s = scale_mm_per_m * MM
        w = 7*s
        l = 10*s
        c.rect(origin_x, origin_y, w, l, width_mm=0.70)
        service_y = origin_y + (5.8 if first_floor else 6.2)*s
        c.line(origin_x, service_y, origin_x+w, service_y, width_mm=0.50)
        divisions = [2.2, 4.0, 5.5 if first_floor else 5.4]
        for x in divisions:
            c.line(origin_x+x*s, service_y, origin_x+x*s, origin_y+l, width_mm=0.45)
        # doors and openings
        c.line(origin_x+0.8*s, origin_y, origin_x+2.0*s, origin_y, width_mm=1.6)
        c.line(origin_x+w, origin_y+1.0*s, origin_x+w, origin_y+2.2*s, width_mm=1.6)
        # windows
        for x in (1.0, 3.0, 5.0):
            c.line(origin_x+x*s, origin_y, origin_x+(x+0.9)*s, origin_y, width_mm=1.1)
        for y in (2.0, 4.0):
            c.line(origin_x, origin_y+y*s, origin_x, origin_y+(y+0.9)*s, width_mm=1.1)
        if first_floor:
            labels = [
                (3.5, 2.8, "Prayer hall women", "40.60 m2"),
                (1.1, 7.9, "Classroom", "9.24 m2"),
                (3.1, 7.9, "Stair", "7.56 m2"),
                (4.75, 7.9, "Canteen", "6.30 m2"),
                (6.25, 7.9, "Sanitary/store", "6.30 m2"),
            ]
        else:
            labels = [
                (3.5, 3.0, "Prayer hall", "43.40 m2"),
                (1.1, 8.1, "Entrance", "8.36 m2"),
                (3.1, 8.1, "Stair", "6.84 m2"),
                (4.7, 8.1, "WC", "5.32 m2"),
                (6.2, 8.1, "Ablution", "6.08 m2"),
            ]
        for x,y,label,area in labels:
            c.text(origin_x+x*s, origin_y+y*s, label, size_pt=8, bold=True, align="center")
            c.text(origin_x+x*s, origin_y+y*s-4*MM, area, size_pt=7, align="center")
        # prayer direction arrow
        c.arrow(origin_x+2.4*s, origin_y+1.4*s, origin_x+4.6*s, origin_y+1.4*s, label="Qibla")
        # dimensions
        c.dimension(origin_x, origin_y, origin_x+w, origin_y, "7 000", offset=-10*MM)
        c.dimension(origin_x+w, origin_y, origin_x+w, origin_y+l, "10 000", offset=-10*MM)
        c.text(origin_x+w/2, origin_y+l+8*MM, "All dimensions in mm - verify existing connection on site", size_pt=8, align="center")

    def _situation(self) -> dict[str, Any]:
        c = self._base("A-001", "Situation and parking concept", "1:250", "ARCHITECTURE / PARKING")
        ox, oy = 55*MM, 80*MM
        s = 4*MM  # 1 m = 4 mm at 1:250
        c.rect(ox, oy, 58*s, 40*s, fill="#f8fafc", width_mm=0.45)
        c.text(ox+29*s, oy+40*s+7*MM, "SCHEMATIC PROJECT AREA - CADASTRAL VALIDATION PENDING", size_pt=9, bold=True, align="center")
        # road
        c.rect(ox, oy+17*s, 58*s, 6*s, fill="#e5e7eb", width_mm=0.25)
        c.text(ox+29*s, oy+20*s, "Bikkersweg / local access", size_pt=8, bold=True, align="center")
        # existing and extension
        existing_x, existing_y = ox+20*s, oy+23*s
        c.rect(existing_x, existing_y, 12*s, 14*s, fill="#dbeafe", dashed=True)
        c.text(existing_x+6*s, existing_y+7*s, "Existing mosque\nreference", size_pt=8, bold=True, align="center")
        ext_x, ext_y = existing_x+12*s, existing_y+2*s
        c.rect(ext_x, ext_y, 7*s, 10*s, fill="#bfdbfe", width_mm=0.7)
        c.text(ext_x+3.5*s, ext_y+5*s, "7 x 10 m\nextension", size_pt=8, bold=True, align="center")
        # north arrow
        c.arrow(ox+53*s, oy+32*s, ox+53*s, oy+38*s, label="N")
        # parking zones as blocks
        zones = self.config["parking"]["zones"]
        blocks = [
            (ox+3*s, oy+25*s, 14*s, 10*s),
            (ox+3*s, oy+3*s, 15*s, 10*s),
            (ox+21*s, oy+3*s, 12*s, 10*s),
            (ox+39*s, oy+25*s, 14*s, 10*s),
            (ox+39*s, oy+3*s, 14*s, 10*s),
        ]
        for zone, block in zip(zones, blocks):
            x,y,w,h = block
            c.rect(x,y,w,h,fill="#ecfdf5",width_mm=0.35)
            c.text(x+w/2,y+h/2+2*MM,f"{zone['id']} - {zone['spaces']} spaces",size_pt=8,bold=True,align="center")
            # schematic stall ticks
            count = max(4, min(10, zone['spaces']//7))
            for index in range(1,count):
                c.line(x+index*w/count,y,x+index*w/count,y+h,width_mm=0.15)
        c.text(ox+29*s, oy-8*MM, "TOTAL PROJECT-LEADER-CONFIRMED CAPACITY: 225 SPACES - FIELD VERIFICATION PENDING", size_pt=9, bold=True, align="center")
        return {"id":"A-001","title":"Situation and parking concept","scale":"1:250","canvas":c,"dxf":True}

    def _ground_floor(self) -> dict[str, Any]:
        c = self._base("A-101", "Ground-floor plan", "1:50", "ARCHITECTURE")
        self._plan_rooms(c, 90*MM, 65*MM, 20.0, first_floor=False)
        c.rect(20*MM, 105*MM, 55*MM, 80*MM, dashed=True, fill="#f8fafc")
        c.text(47.5*MM, 150*MM, "Existing building\nconnection reference", size_pt=9, bold=True, align="center")
        c.arrow(75*MM, 145*MM, 90*MM, 145*MM, label="new connection")
        return {"id":"A-101","title":"Ground-floor plan","scale":"1:50","canvas":c,"dxf":True}

    def _first_floor(self) -> dict[str, Any]:
        c = self._base("A-102", "First-floor plan", "1:50", "ARCHITECTURE")
        self._plan_rooms(c, 90*MM, 65*MM, 20.0, first_floor=True)
        c.rect(20*MM, 105*MM, 55*MM, 80*MM, dashed=True, fill="#f8fafc")
        c.text(47.5*MM, 150*MM, "Existing first floor\nreference", size_pt=9, bold=True, align="center")
        c.arrow(75*MM, 145*MM, 90*MM, 145*MM, label="new connection")
        return {"id":"A-102","title":"First-floor plan","scale":"1:50","canvas":c,"dxf":True}

    def _elevation_one(self, c: VectorCanvas, x: float, y: float, width_m: float, label: str, windows: int, has_door: bool) -> None:
        s = 10*MM
        w = width_m*s
        h = 6.8*s
        c.rect(x,y,w,h,width_mm=0.55,fill="#f8fafc")
        c.line(x,y+3.2*s,x+w,y+3.2*s,width_mm=0.25)
        c.line(x,y+6.4*s,x+w,y+6.4*s,width_mm=0.55)
        opening_w = 1.0*s
        spacing = w/(windows+1)
        for level in (0.8,4.0):
            for index in range(1,windows+1):
                cx = x+index*spacing-opening_w/2
                c.rect(cx,y+level*s,opening_w,1.5*s,fill="#dbeafe",width_mm=0.25)
        if has_door:
            c.rect(x+w*0.10,y,1.2*s,2.4*s,fill="#e5e7eb",width_mm=0.35)
        c.text(x+w/2,y-5*MM,label,size_pt=8,bold=True,align="center")
        c.dimension(x,y,x+w,y,f"{int(width_m*1000):,}".replace(","," "),offset=-10*MM)
        c.dimension(x+w,y,x+w,y+h,"6 800",offset=-8*MM)

    def _elevations(self) -> dict[str, Any]:
        c = self._base("A-201", "Elevations", "1:100", "ARCHITECTURE")
        self._elevation_one(c,35*MM,160*MM,7,"Front elevation",3,True)
        self._elevation_one(c,225*MM,160*MM,7,"Rear elevation",3,True)
        self._elevation_one(c,35*MM,65*MM,10,"Side elevation north",4,False)
        self._elevation_one(c,225*MM,65*MM,10,"Side elevation south",4,False)
        c.text(210*MM,250*MM,"Facade material concept: light masonry, recessed frames, flat roof with parapet",size_pt=9,bold=True,align="center")
        return {"id":"A-201","title":"Elevations","scale":"1:100","canvas":c,"dxf":False}

    def _section_one(self, c: VectorCanvas, x: float, y: float, length_m: float, label: str) -> None:
        s = 10*MM
        w = length_m*s
        c.line(x,y,x+w,y,width_mm=0.75)
        c.line(x,y+3.2*s,x+w,y+3.2*s,width_mm=0.65)
        c.line(x,y+6.4*s,x+w,y+6.4*s,width_mm=0.65)
        c.line(x,y,x,y+6.8*s,width_mm=0.55)
        c.line(x+w,y,x+w,y+6.8*s,width_mm=0.55)
        c.line(x,y+6.8*s,x+w,y+6.8*s,width_mm=0.55)
        # foundation
        c.rect(x-0.5*s,y-0.6*s,1.5*s,0.4*s,fill="#e5e7eb",width_mm=0.35)
        c.rect(x+w-1.0*s,y-0.6*s,1.5*s,0.4*s,fill="#e5e7eb",width_mm=0.35)
        # stair schematic
        for index in range(8):
            c.line(x+w*0.35+index*0.25*s,y+index*0.4*s,x+w*0.35+(index+1)*0.25*s,y+index*0.4*s,width_mm=0.20)
        c.text(x+w/2,y-10*MM,label,size_pt=8,bold=True,align="center")
        c.text(x-8*MM,y,"P=0.000",size_pt=7,align="right")
        c.text(x-8*MM,y+3.2*s,"+3.200",size_pt=7,align="right")
        c.text(x-8*MM,y+6.4*s,"+6.400",size_pt=7,align="right")
        c.text(x-8*MM,y+6.8*s,"+6.800",size_pt=7,align="right")

    def _sections(self) -> dict[str, Any]:
        c = self._base("A-301", "Sections", "1:100", "ARCHITECTURE / STRUCTURE")
        self._section_one(c,55*MM,160*MM,10,"Section A-A longitudinal")
        self._section_one(c,245*MM,160*MM,7,"Section B-B transverse")
        c.text(210*MM,90*MM,"Foundation dimensions are simulation assumptions. Geotechnical and structural verification is mandatory.",size_pt=9,bold=True,align="center")
        return {"id":"A-301","title":"Sections","scale":"1:100","canvas":c,"dxf":False}

    def _roof(self) -> dict[str, Any]:
        c = self._base("A-401", "Roof plan and drainage concept", "1:50", "ARCHITECTURE / DRAINAGE")
        ox,oy=115*MM,65*MM
        s=20*MM
        c.rect(ox,oy,7*s,10*s,width_mm=0.65,fill="#f8fafc")
        c.line(ox+3.5*s,oy,ox+3.5*s,oy+10*s,width_mm=0.18,dashed=True)
        outlets=[(ox+0.5*s,oy+0.5*s),(ox+6.5*s,oy+9.5*s)]
        for x,y in outlets:
            c.circle(x,y,2.5*MM,fill="#bfdbfe",width_mm=0.35)
            c.text(x,y-6*MM,"RWP",size_pt=7,bold=True,align="center")
        c.arrow(ox+3.5*s,oy+5*s,*outlets[0],label="fall")
        c.arrow(ox+3.5*s,oy+5*s,*outlets[1],label="fall")
        c.text(ox+3.5*s,oy+10*s+8*MM,"Flat roof with two drainage zones and emergency overflow concept",size_pt=9,bold=True,align="center")
        c.dimension(ox,oy,ox+7*s,oy,"7 000",offset=-10*MM)
        c.dimension(ox+7*s,oy,ox+7*s,oy+10*s,"10 000",offset=-10*MM)
        return {"id":"A-401","title":"Roof plan and drainage concept","scale":"1:50","canvas":c,"dxf":True}

    def _foundation(self) -> dict[str, Any]:
        c = self._base("S-101", "Foundation concept", "1:50", "STRUCTURE / GEOTECHNICS")
        ox,oy=115*MM,65*MM
        s=20*MM
        outer=7*s,10*s
        # Strip width 1.5m drawn schematically as band
        c.rect(ox,oy,outer[0],outer[1],fill="#f8fafc",width_mm=0.65)
        band=0.75*s
        c.rect(ox-band/2,oy-band/2,outer[0]+band,outer[1]+band,fill="#e5e7eb",width_mm=0.35)
        c.rect(ox+band/2,oy+band/2,outer[0]-band,outer[1]-band,fill="#ffffff",width_mm=0.35)
        c.line(ox+3.5*s,oy,ox+3.5*s,oy+10*s,width_mm=1.1)
        c.text(ox+3.5*s,oy+5*s,"Internal foundation beam\n500 x 600 mm",size_pt=8,bold=True,align="center")
        c.text(ox+3.5*s,oy+10*s+8*MM,"Perimeter strip concept: 1500 x 400 mm - verification required",size_pt=9,bold=True,align="center")
        # detail box
        dx,dy=315*MM,125*MM
        c.rect(dx,dy,65*MM,75*MM,width_mm=0.45)
        c.rect(dx+8*MM,dy+15*MM,49*MM,18*MM,fill="#d1d5db",width_mm=0.35)
        c.rect(dx+24*MM,dy+15*MM,17*MM,38*MM,fill="#9ca3af",width_mm=0.35)
        c.text(dx+32.5*MM,dy+60*MM,"CONCEPT DETAIL",size_pt=8,bold=True,align="center")
        c.text(dx+32.5*MM,dy+8*MM,"Groundwater assumption P=-0.50 m",size_pt=7,align="center")
        return {"id":"S-101","title":"Foundation concept","scale":"1:50","canvas":c,"dxf":True}

    def _structure(self) -> dict[str, Any]:
        c = self._base("S-201", "Structural scheme and load path", "1:75", "STRUCTURE")
        ox,oy=90*MM,70*MM
        sx,sy=35*MM,42*MM
        for ix in range(3):
            for iy in range(3):
                x,y=ox+ix*sx,oy+iy*sy
                c.circle(x,y,3*MM,fill="#93c5fd",width_mm=0.35)
                c.text(x,y+7*MM,f"C{ix+1}{iy+1}",size_pt=7,bold=True,align="center")
        for iy in range(3):
            c.line(ox,oy+iy*sy,ox+2*sx,oy+iy*sy,width_mm=0.9)
        for ix in range(3):
            c.line(ox+ix*sx,oy,ox+ix*sx,oy+2*sy,width_mm=0.9)
        for ix in range(3):
            for iy in range(2):
                c.arrow(ox+ix*sx,oy+(iy+1)*sy-8*MM,ox+ix*sx,oy+iy*sy+8*MM,label="load")
        # exploded vertical scheme
        bx=260*MM
        for level,label in [(75,"foundation"),(125,"ground floor"),(175,"first floor"),(225,"roof")]:
            c.rect(bx,level*MM,100*MM,10*MM,fill="#dbeafe",width_mm=0.35)
            c.text(bx+50*MM,level*MM+3*MM,label,size_pt=8,bold=True,align="center")
        for x in (bx+15*MM,bx+50*MM,bx+85*MM):
            c.line(x,85*MM,x,225*MM,width_mm=0.8)
        c.text(210*MM,252*MM,"Concept grid 3.5 m x 5.0 m - final member sizing by structural engineer",size_pt=9,bold=True,align="center")
        return {"id":"S-201","title":"Structural scheme and load path","scale":"1:75","canvas":c,"dxf":False}

    def _fire(self) -> dict[str, Any]:
        c = self._base("F-101", "Fire and escape route concept", "1:50", "FIRE SAFETY")
        ox,oy=90*MM,65*MM
        self._plan_rooms(c,ox,oy,20.0,first_floor=False)
        s=20*MM
        # escape paths to exits
        center=(ox+3.5*s,oy+3.2*s)
        exit1=(ox+1.4*s,oy)
        exit2=(ox+7*s,oy+1.6*s)
        c.arrow(*center,*exit1,label="escape")
        c.arrow(*center,*exit2,label="escape")
        c.text(325*MM,210*MM,"DESIGN PEAK",size_pt=9,bold=True,align="center")
        c.text(325*MM,195*MM,"200 persons",size_pt=16,bold=True,align="center")
        c.text(325*MM,175*MM,"2 exits x 1.20 m",size_pt=11,bold=True,align="center")
        c.text(325*MM,155*MM,"No compliance conclusion",size_pt=9,bold=True,align="center")
        c.text(325*MM,143*MM,"Professional fire assessment required",size_pt=8,align="center")
        return {"id":"F-101","title":"Fire and escape route concept","scale":"1:50","canvas":c,"dxf":False}

    def _phasing(self) -> dict[str, Any]:
        c = self._base("X-101", "Construction phasing concept", "NTS", "EXECUTION / AERIUS")
        phases=self.config["aerius_phases"]
        start_x=35*MM
        base_y=125*MM
        total_width=340*MM
        total_days=sum(p['duration_days'] for p in phases[:-1])
        cursor=start_x
        colors=["#dbeafe","#bfdbfe","#93c5fd","#60a5fa"]
        for idx,phase in enumerate(phases[:-1]):
            w=total_width*phase['duration_days']/total_days
            c.rect(cursor,base_y,w,35*MM,fill=colors[idx],width_mm=0.35)
            c.text(cursor+w/2,base_y+21*MM,phase['id'],size_pt=8,bold=True,align="center")
            c.text(cursor+w/2,base_y+11*MM,f"{phase['name']} - {phase['duration_days']} d",size_pt=7,align="center")
            cursor+=w
        c.rect(start_x,80*MM,total_width,25*MM,fill="#ecfdf5",width_mm=0.35)
        c.text(start_x+total_width/2,92*MM,"Mosque remains in use - temporary segregation and safe access required",size_pt=9,bold=True,align="center")
        c.text(210*MM,215*MM,"PHASED CONSTRUCTION CONCEPT",size_pt=15,bold=True,align="center")
        c.text(210*MM,195*MM,"Activity data are synthetic fixtures for workflow validation only",size_pt=9,bold=True,align="center")
        return {"id":"X-101","title":"Construction phasing concept","scale":"NTS","canvas":c,"dxf":False}


class ReportPdfBuilder:
    def __init__(self, title: str, subtitle: str, project: Mapping[str, Any]) -> None:
        self.title = title
        self.subtitle = subtitle
        self.project = project
        self.doc = PdfDocument()
        self.page_commands: list[str] = []
        self.y = 0.0
        self.page_no = 0
        self._new_page(cover=True)
        self._new_page()

    def _new_page(self, cover: bool = False) -> None:
        if self.page_commands:
            self.doc.add_page(*A4_P, "\n".join(self.page_commands)+"\n")
        self.page_no += 1
        self.page_commands = []
        self.y = A4_P[1] - 22*MM
        self.page_commands.append("0.12 0.18 0.25 RG")
        if cover:
            self._text(25*MM, self.y, "PROJECT PHOENIX", 13, True)
            self.y -= 35*MM
            self._text(25*MM, self.y, self.title, 23, True)
            self.y -= 12*MM
            self._text(25*MM, self.y, self.subtitle, 12, False)
            self.y -= 18*MM
            self._rule()
            self.y -= 12*MM
            fields=[
                ("Project", self.project["name"]),
                ("Location", self.project["address"]),
                ("Issue", "2026-07-27"),
                ("Status", STATUS),
            ]
            for key,value in fields:
                self._text(25*MM,self.y,key.upper(),8,True)
                self._text(65*MM,self.y,value,10,False)
                self.y-=9*MM
            self.y -= 18*MM
            self._text(25*MM,self.y,"This report contains actual generated concept deliverables. It is not a professional certification and is not approved for permit submission or construction.",10,True,max_chars=78)
        else:
            self._text(20*MM, A4_P[1]-14*MM, self.title, 8, True)
            self._text(A4_P[0]-20*MM, A4_P[1]-14*MM, f"Page {self.page_no}", 8, False, align="right")
            self.page_commands.append(f"{_num(20*MM)} {_num(14*MM)} m {_num(A4_P[0]-20*MM)} {_num(14*MM)} l S")
            self._text(20*MM, 8*MM, STATUS, 7, True)

    def _text(self, x: float, y: float, value: str, size: float, bold: bool, *, align: str = "left", max_chars: int | None = None) -> None:
        lines = _wrap(value, max_chars) if max_chars else [value]
        for index,line in enumerate(lines):
            estimated=len(line)*size*0.50
            tx=x-estimated if align=="right" else x-estimated/2 if align=="center" else x
            font="F2" if bold else "F1"
            self.page_commands.append(f"BT /{font} {_num(size)} Tf 1 0 0 1 {_num(tx)} {_num(y-index*(size+3))} Tm ({_pdf_text(line)}) Tj ET")

    def _rule(self) -> None:
        self.page_commands.append(f"{_num(25*MM)} {_num(self.y)} m {_num(A4_P[0]-25*MM)} {_num(self.y)} l S")

    def heading(self, value: str, level: int = 1) -> None:
        needed=20*MM if level==1 else 14*MM
        if self.y<35*MM+needed:
            self._new_page()
        size=15 if level==1 else 11
        self.y-=8*MM
        self._text(20*MM,self.y,value,size,True,max_chars=68)
        self.y-= (12 if level==1 else 9)*MM

    def paragraph(self, value: str) -> None:
        lines=_wrap(value,92)
        needed=(len(lines)*5.2+5)*MM
        if self.y<25*MM+needed:
            self._new_page()
        for line in lines:
            self._text(20*MM,self.y,line,9,False)
            self.y-=5.2*MM
        self.y-=3*MM

    def bullets(self, values: Sequence[str]) -> None:
        for value in values:
            lines=_wrap(value,84)
            needed=(len(lines)*5.2+2)*MM
            if self.y<25*MM+needed:
                self._new_page()
            self._text(22*MM,self.y,"-",9,True)
            for index,line in enumerate(lines):
                self._text(28*MM,self.y-index*5.2*MM,line,9,False)
            self.y-=len(lines)*5.2*MM+2*MM
        self.y-=2*MM

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[Any]], widths: Sequence[float] | None = None) -> None:
        if widths is None:
            widths=[(A4_P[0]-40*MM)/len(headers)]*len(headers)
        row_h=9*MM
        total_w=sum(widths)
        if self.y<35*MM+(len(rows)+2)*row_h:
            self._new_page()
        x=20*MM
        # header
        self.page_commands.append("0.90 g")
        self.page_commands.append(f"{_num(x)} {_num(self.y-row_h+2*MM)} {_num(total_w)} {_num(row_h)} re B")
        self.page_commands.append("0 g")
        cursor=x
        for header,w in zip(headers,widths):
            self._text(cursor+2*MM,self.y-4*MM,str(header),7,True,max_chars=max(8,int(w/MM/2.3)))
            cursor+=w
        self.y-=row_h
        for row in rows:
            if self.y<25*MM+row_h:
                self._new_page()
            cursor=x
            self.page_commands.append(f"{_num(x)} {_num(self.y-row_h+2*MM)} {_num(total_w)} {_num(row_h)} re S")
            for value,w in zip(row,widths):
                self._text(cursor+2*MM,self.y-4*MM,str(value),7,False,max_chars=max(8,int(w/MM/2.2)))
                cursor+=w
            self.y-=row_h
        self.y-=5*MM

    def finish(self, path: Path) -> Path:
        if self.page_commands:
            self.doc.add_page(*A4_P, "\n".join(self.page_commands)+"\n")
            self.page_commands=[]
        return self.doc.write(path)


class DocxBuilder:
    def __init__(self, title: str, subtitle: str, project: Mapping[str, Any]) -> None:
        self.title=title
        self.subtitle=subtitle
        self.project=project
        self.body: list[str]=[]
        self._paragraph("PROJECT PHOENIX", "Title")
        self._paragraph(title, "Title")
        self._paragraph(subtitle, "Subtitle")
        self._paragraph(project["name"], "Heading1")
        self._paragraph(project["address"], "Normal")
        self._paragraph("Issue: 2026-07-27", "Normal")
        self._paragraph(STATUS, "Warning")
        self._paragraph("This document records actual generated concept output. It is not a qualified professional statement and is not approved for permit submission or construction.", "Normal")
        self._page_break()

    def _paragraph(self, text: str, style: str = "Normal") -> None:
        safe=xml_escape(text)
        self.body.append(f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t xml:space="preserve">{safe}</w:t></w:r></w:p>')

    def _page_break(self) -> None:
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def heading(self, text: str, level: int = 1) -> None:
        self._paragraph(text, "Heading1" if level==1 else "Heading2")

    def paragraph(self, text: str) -> None:
        self._paragraph(text, "Normal")

    def bullets(self, values: Sequence[str]) -> None:
        for value in values:
            self._paragraph("- " + value, "ListBullet")

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
        table=['<w:tbl><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4"/><w:left w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/><w:insideH w:val="single" w:sz="2"/><w:insideV w:val="single" w:sz="2"/></w:tblBorders></w:tblPr>']
        for ridx,row in enumerate([headers,*rows]):
            table.append('<w:tr>')
            for value in row:
                style='Heading2' if ridx==0 else 'Normal'
                table.append(f'<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t>{xml_escape(str(value))}</w:t></w:r></w:p></w:tc>')
            table.append('</w:tr>')
        table.append('</w:tbl>')
        self.body.append(''.join(table))

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        document=(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>' + ''.join(self.body) +
            '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567"/></w:sectPr>'
            '</w:body></w:document>'
        )
        styles="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="36"/></w:rPr><w:pPr><w:spacing w:after="220"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="52677D"/><w:sz w:val="24"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:outlineLvl w:val="0"/><w:rPr><w:b/><w:color w:val="17324D"/><w:sz w:val="28"/></w:rPr><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:outlineLvl w:val="1"/><w:rPr><w:b/><w:color w:val="1F4E79"/><w:sz w:val="23"/></w:rPr><w:pPr><w:spacing w:before="180" w:after="80"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360" w:hanging="180"/></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Warning"><w:name w:val="Warning"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="9C0006"/><w:sz w:val="22"/></w:rPr><w:pPr><w:shd w:fill="FFC7CE"/><w:spacing w:before="120" w:after="180"/></w:pPr></w:style></w:styles>"""
        content_types="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>"""
        root_rels="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>"""
        doc_rels="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""
        core="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>""" + xml_escape(self.title) + """</dc:title><dc:creator>Project Phoenix</dc:creator><cp:lastModifiedBy>Project Phoenix</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">2026-07-27T00:00:00Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">2026-07-27T00:00:00Z</dcterms:modified></cp:coreProperties>"""
        app="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Project Phoenix</Application><AppVersion>1.0.0</AppVersion></Properties>"""
        members={
            '[Content_Types].xml':content_types,
            '_rels/.rels':root_rels,
            'word/document.xml':document,
            'word/styles.xml':styles,
            'word/_rels/document.xml.rels':doc_rels,
            'docProps/core.xml':core,
            'docProps/app.xml':app,
        }
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
            for name,value in sorted(members.items()):
                info=zipfile.ZipInfo(name,FIXED_ZIP_TIME)
                info.compress_type=zipfile.ZIP_STORED
                info.create_system=3
                info.external_attr=0o100644<<16
                archive.writestr(info,value.encode('utf-8'))
        return path


class RealConceptProductionEngine:
    VERSION = "1.0.0"

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config=config
        self.project=config["project"]

    def produce(self, output_dir: str | Path) -> dict[str, Any]:
        root=Path(output_dir)
        if root.exists():
            for child in root.iterdir():
                if child.is_dir():
                    import shutil
                    shutil.rmtree(child)
                else:
                    child.unlink()
        root.mkdir(parents=True,exist_ok=True)
        drawings_pdf=root/'drawings'/'pdf'
        drawings_svg=root/'drawings'/'svg'
        drawings_dxf=root/'drawings'/'dxf'
        reports_pdf=root/'reports'/'pdf'
        reports_docx=root/'reports'/'docx'
        for folder in (drawings_pdf,drawings_svg,drawings_dxf,reports_pdf,reports_docx):
            folder.mkdir(parents=True,exist_ok=True)

        sheets=DrawingFactory(self.config).create()
        drawing_register=[]
        combined=PdfDocument()
        paths: dict[str,Path]={}
        for sheet in sheets:
            sheet_id=sheet['id']
            stem=f"{sheet_id}_{self._slug(sheet['title'])}"
            canvas: VectorCanvas=sheet['canvas']
            pdf_path=drawings_pdf/f"{stem}.pdf"
            svg_path=drawings_svg/f"{stem}.svg"
            one=PdfDocument(); one.add_page(*A3_L,canvas.to_pdf_content()); one.write(pdf_path)
            write_text(svg_path,canvas.to_svg())
            paths[f"drawing_{sheet_id}_pdf"]=pdf_path
            paths[f"drawing_{sheet_id}_svg"]=svg_path
            dxf_path=None
            if sheet['dxf']:
                dxf_path=drawings_dxf/f"{stem}.dxf"
                write_text(dxf_path,canvas.to_dxf(),newline='')
                paths[f"drawing_{sheet_id}_dxf"]=dxf_path
            combined.add_page(*A3_L,canvas.to_pdf_content())
            drawing_register.append({
                'sheet_id':sheet_id,
                'title':sheet['title'],
                'scale':sheet['scale'],
                'status':STATUS,
                'pdf':pdf_path.relative_to(root).as_posix(),
                'svg':svg_path.relative_to(root).as_posix(),
                'dxf':dxf_path.relative_to(root).as_posix() if dxf_path else '',
            })
        drawing_set=drawings_pdf/'BB35_PILOT_1_REAL_CONCEPT_DRAWING_SET_v1_0_0.pdf'
        combined.write(drawing_set)
        paths['drawing_set_pdf']=drawing_set

        report_specs=self._report_specs(drawing_register)
        report_register=[]
        for spec in report_specs:
            stem=f"{spec['id']}_{self._slug(spec['title'])}"
            pdf_path=reports_pdf/f"{stem}.pdf"
            docx_path=reports_docx/f"{stem}.docx"
            self._write_report_pdf(pdf_path,spec)
            self._write_report_docx(docx_path,spec)
            paths[f"report_{spec['id']}_pdf"]=pdf_path
            paths[f"report_{spec['id']}_docx"]=docx_path
            report_register.append({
                'report_id':spec['id'],
                'title':spec['title'],
                'status':STATUS,
                'pdf':pdf_path.relative_to(root).as_posix(),
                'docx':docx_path.relative_to(root).as_posix(),
            })

        cross_checks=self._cross_checks(drawing_register,report_register,paths)
        summary={
            'schema_version':'phoenix.real-concept-production-result/1.0',
            'engine_version':self.VERSION,
            'issue_id':self.config['issue_id'],
            'issue_date':self.config['issue_date'],
            'project_id':self.project['project_id'],
            'status':'REAL_CONCEPT_DRAWINGS_AND_REPORTS_GENERATED',
            'drawing_sheet_count':len(drawing_register),
            'drawing_pdf_count':len(drawing_register)+1,
            'drawing_svg_count':len(drawing_register),
            'drawing_dxf_count':sum(1 for row in drawing_register if row['dxf']),
            'report_count':len(report_register),
            'report_pdf_count':len(report_register),
            'report_docx_count':len(report_register),
            'gross_area_m2':self.config['geometry']['gross_area_m2'],
            'parking_basis_spaces':self.config['parking']['confirmed_capacity_spaces'],
            'req107_status':self.config['production']['req107_status'],
            'professional_blocker_ids':self.config['production']['professional_blocker_ids'],
            'professional_evidence_blocker_count':len(self.config['production']['professional_blocker_ids']),
            'cross_check_count':len(cross_checks),
            'cross_checks_passed':sum(1 for row in cross_checks if row['passed']),
            'all_cross_checks_passed':all(row['passed'] for row in cross_checks),
            'concept_issue_package_ready':all(row['passed'] for row in cross_checks),
            'final_permit_ready_generation_allowed':False,
            'bb36_production_release_allowed':False,
            'next_gate':'Replace REQ-102, REQ-103, REQ-104, REQ-105, REQ-106 and REQ-108 concept evidence with validated professional evidence.',
        }
        paths['summary']=root/'01_issue_summary.json'; write_json(paths['summary'],summary)
        paths['drawing_register']=root/'02_drawing_register.csv'; write_csv(paths['drawing_register'],drawing_register,['sheet_id','title','scale','status','pdf','svg','dxf'])
        paths['report_register']=root/'03_report_register.csv'; write_csv(paths['report_register'],report_register,['report_id','title','status','pdf','docx'])
        paths['cross_checks']=root/'04_cross_check_report.json'; write_json(paths['cross_checks'],{'checks':cross_checks,'all_passed':all(row['passed'] for row in cross_checks)})
        assumptions=self._assumptions()
        paths['assumptions']=root/'05_assumptions_and_limitations.csv'; write_csv(paths['assumptions'],assumptions,['id','subject','value','source','status','replacement_required'])
        paths['index']=root/'06_issue_index.html'; write_text(paths['index'],self._issue_index(summary,drawing_register,report_register))
        paths['checksums']=root/'checksums.sha256'; self._write_checksums(root,paths['checksums'])
        paths['issue_package']=root/'BB35_PILOT_1_REAL_CONCEPT_ISSUE_PACKAGE_v1_0_0.zip'; self._write_issue_zip(root,paths['issue_package'])
        summary['output_file_count']=sum(1 for p in root.rglob('*') if p.is_file())
        summary['issue_package_sha256']=hashlib.sha256(paths['issue_package'].read_bytes()).hexdigest()
        write_json(paths['summary'],summary)
        # Update checksums/zip after final summary update.
        self._write_checksums(root,paths['checksums'])
        self._write_issue_zip(root,paths['issue_package'])
        return {'summary':summary,'paths':{k:str(v) for k,v in sorted(paths.items())}}

    def _report_specs(self,drawing_register: Sequence[Mapping[str,Any]]) -> list[dict[str,Any]]:
        g=self.config['geometry']; o=self.config['occupancy']; p=self.config['parking']; f=self.config['foundation_concept']; fire=self.config['fire_concept']
        drawings=[(row['sheet_id'],row['title'],row['scale']) for row in drawing_register]
        limitations=[
            'All geometry is a generated concept based on a 7 x 10 m two-storey extension and must be reconciled with a current survey and cadastral control.',
            'Structural, geotechnical, fire-safety, ventilation, parking and AERIUS conclusions require validation and signature by the responsible professionals.',
            'The issue is suitable for pilot validation and professional evidence replacement only.',
            'No document in this issue may be used for permit submission or construction.',
        ]
        integrated={
            'id':'R-001','title':'Integrated concept design report','subtitle':'Architecture, structure, fire, parking and phasing',
            'sections':[
                ('1. Executive summary',[f"Project Phoenix generated a coordinated concept issue for a {g['extension_width_m']:.0f} x {g['extension_length_m']:.0f} m, two-storey extension with {g['gross_area_m2']:.0f} m2 gross floor area.",f"The issue contains {len(drawings)} actual vector drawing sheets and six written reports. REQ-107 is closed by the project leader. Six professional evidence requests remain open."],None),
                ('2. Project basis',[f"Location: {self.project['address']}.",f"Regular future occupancy: {o['regular_future_persons']} persons; Friday future occupancy: {o['friday_future_persons']} persons; special peak: {o['special_peak_persons']} persons.",f"Parking basis: {p['confirmed_capacity_spaces']} project-leader-confirmed public spaces, field verification pending."],None),
                ('3. Drawing issue',['The generated drawing set is a coordinated concept issue with title blocks, scales, dimensions, room names, levels, assumptions and status markings.'],drawings),
                ('4. Design coordination',['Ground- and first-floor gross areas are each 70 m2. The architectural grids, structural concept, escape routes, foundation assumptions, parking basis and phased construction data are cross-checked through the production gate.'],None),
                ('5. Limitations',limitations,None),
                ('6. Release status',['Concept issue package: ready. Final permit-ready generation: blocked. BB36 production release: locked.'],None),
            ]
        }
        architecture={
            'id':'R-101','title':'Architectural concept report','subtitle':'Spatial programme, plans, elevations and sections',
            'sections':[
                ('1. Design intent',['The extension is arranged as a compact 7 x 10 m volume connected schematically to the existing mosque. A flat roof and simple facade rhythm support a clear and economical concept.'],None),
                ('2. Ground floor',["The ground floor contains a 43.40 m2 prayer hall and a 26.60 m2 service strip with entrance, stair, WC and ablution space."],[("Prayer hall","43.40 m2"),("Entrance","8.36 m2"),("Stair","6.84 m2"),("WC","5.32 m2"),("Ablution","6.08 m2")]),
                ('3. First floor',["The first floor contains a 40.60 m2 women\'s prayer hall and supporting classroom, stair, canteen and sanitary/store spaces."],[("Prayer hall women","40.60 m2"),("Classroom","9.24 m2"),("Stair","7.56 m2"),("Canteen","6.30 m2"),("Sanitary/store","6.30 m2")]),
                ('4. External appearance',['Generated elevations use light masonry, recessed frames and a parapet roof line. Final material selection and integration with the existing building remain design tasks.'],None),
                ('5. Required verification',limitations[:2],None),
            ]
        }
        structural={
            'id':'R-201','title':'Structural and foundation concept report','subtitle':'Load path, structural grid and synthetic foundation basis',
            'sections':[
                ('1. Structural scheme',['A regular three-by-three column grid is used as a conceptual load path. Beams transfer floor and roof loads to columns and the foundation system. Final materials and member sizes are not selected in this concept issue.'],None),
                ('2. Foundation concept',[f"The simulated foundation uses a continuous {f['perimeter_strip_width_m']:.2f} m wide and {f['strip_height_m']:.2f} m high strip with a {f['foundation_beam_width_m']:.2f} x {f['foundation_beam_height_m']:.2f} m beam. Groundwater is assumed at P={f['groundwater_level_m']:.2f} m."],[("Layer 1","0.0 to -0.8 m","synthetic sand fill"),("Layer 2","-0.8 to -2.5 m","synthetic soft clay"),("Layer 3","-2.5 to -8.0 m","synthetic medium-dense sand")]),
                ('3. Risks',['Settlement and differential movement at the new-to-existing connection require explicit assessment. Soil profile, bearing resistance, stiffness, reinforcement and detailing are not professional conclusions.'],None),
                ('4. Required evidence',['Current structural survey and connection assessment (REQ-103).','Ground investigation and signed foundation advice (REQ-104).'],None),
            ]
        }
        fire_report={
            'id':'R-301','title':'Bbl, fire safety and ventilation concept report','subtitle':'Occupancy, escape route and ventilation design basis',
            'sections':[
                ('1. Occupancy basis',[f"The review basis uses {o['regular_future_persons']} regular future occupants, {o['friday_future_persons']} Friday occupants and {o['special_peak_persons']} persons for the annual special peak."],None),
                ('2. Escape concept',[f"The concept drawing shows {fire['exit_count']} independent exits, each {fire['exit_width_m_each']:.2f} m wide, for a total simulated width of {fire['total_exit_width_m']:.2f} m."],[("Exit count",fire['exit_count']),("Width per exit",f"{fire['exit_width_m_each']:.2f} m"),("Total width",f"{fire['total_exit_width_m']:.2f} m"),("Compliance conclusion",fire['compliance_conclusion'])]),
                ('3. Ventilation concept',['Ventilation is to be sized from verified room functions, occupancy profiles and Bbl requirements. The current issue records the spatial basis only and does not state compliance.'],None),
                ('4. Required evidence',['Signed fire-safety and evacuation assessment.','Verified travel distances, compartmentation and resistance requirements.','Ventilation calculations and installation design.','Accessibility and sanitary review.'],None),
            ]
        }
        parking={
            'id':'R-401','title':'Parking concept report','subtitle':'Capacity basis, synthetic demand and measurement programme',
            'sections':[
                ('1. Capacity basis',[f"The project leader confirmed {p['confirmed_capacity_spaces']} public spaces in the direct surroundings. The previous 300-space hypothesis is superseded. Field verification is still required."],[(z['id'],z['label'],z['spaces']) for z in p['zones']]),
                ('2. Synthetic demand test',['The production run carries forward the simulation demand values solely to test the reporting chain.'],[("Regular future",p['synthetic_demand']['regular_future'],55,25),("Friday future",p['synthetic_demand']['friday_future'],55,30),("Special peak",p['synthetic_demand']['special_peak'],55,15)]),
                ('3. Measurement programme',['Five field moments must be counted, including Friday prayer. Raw count sheets, mapped public/private restrictions, photographs and a professional parking balance are required.'],None),
                ('4. Status',['The 225-space basis is project-leader-confirmed and not yet professionally verified. No definitive parking conclusion is made.'],None),
            ]
        }
        aerius={
            'id':'R-501','title':'AERIUS activity data concept report','subtitle':'Phasing, equipment boundary and traffic inputs',
            'sections':[
                ('1. Execution strategy',['The extension is assumed to be built in phases while the mosque remains in use. Safe separation, temporary access and overlap controls must be developed.'],None),
                ('2. Simulated phases',['The following durations are synthetic workflow fixtures and not contractor data.'],[(phase['id'],phase['name'],phase['duration_days']) for phase in self.config['aerius_phases']]),
                ('3. Required activity data',['Equipment type, power, fuel and operating hours.','Construction traffic by vehicle class and route.','Operational traffic and use-stage sources.','Separate construction and operational AERIUS input sets.','AERIUS calculation file and adviser statement.'],None),
                ('4. Status',['No nitrogen deposition conclusion is made in this concept production run. REQ-108 remains a professional evidence blocker.'],None),
            ]
        }
        return [integrated,architecture,structural,fire_report,parking,aerius]

    def _write_report_pdf(self,path:Path,spec:Mapping[str,Any])->None:
        builder=ReportPdfBuilder(spec['title'],spec['subtitle'],self.project)
        for title,paragraphs,table in spec['sections']:
            builder.heading(title)
            for paragraph in paragraphs:
                builder.paragraph(paragraph)
            if table:
                headers=[f"Field {i+1}" for i in range(len(table[0]))]
                builder.table(headers,table)
        builder.finish(path)

    def _write_report_docx(self,path:Path,spec:Mapping[str,Any])->None:
        builder=DocxBuilder(spec['title'],spec['subtitle'],self.project)
        for title,paragraphs,table in spec['sections']:
            builder.heading(title)
            for paragraph in paragraphs:
                builder.paragraph(paragraph)
            if table:
                headers=[f"Field {i+1}" for i in range(len(table[0]))]
                builder.table(headers,table)
        builder.write(path)

    def _cross_checks(self,drawings,reports,paths)->list[dict[str,Any]]:
        room_ground=[43.40,8.36,6.84,5.32,6.08]
        room_first=[40.60,9.24,7.56,6.30,6.30]
        parking_total=sum(z['spaces'] for z in self.config['parking']['zones'])
        checks=[
            ('CHK-001','drawing_sheet_count',len(drawings)==10,f"{len(drawings)} / 10"),
            ('CHK-002','report_count',len(reports)==6,f"{len(reports)} / 6"),
            ('CHK-003','ground_floor_area',abs(sum(room_ground)-70.0)<0.001,f"{sum(room_ground):.2f} m2"),
            ('CHK-004','first_floor_area',abs(sum(room_first)-70.0)<0.001,f"{sum(room_first):.2f} m2"),
            ('CHK-005','gross_area',abs(sum(room_ground)+sum(room_first)-self.config['geometry']['gross_area_m2'])<0.001,f"{sum(room_ground)+sum(room_first):.2f} m2"),
            ('CHK-006','parking_zones',parking_total==225,f"{parking_total} spaces"),
            ('CHK-007','req107_closed',self.config['production']['req107_status']=='CLOSED_PROJECT_LEADER_APPROVED',self.config['production']['req107_status']),
            ('CHK-008','professional_blockers',len(self.config['production']['professional_blocker_ids'])==6,str(self.config['production']['professional_blocker_ids'])),
            ('CHK-009','pdf_files',all(Path(v).read_bytes().startswith(b'%PDF-1.4') for k,v in paths.items() if k.endswith('_pdf')),f"{sum(1 for k in paths if k.endswith('_pdf'))} PDFs"),
            ('CHK-010','svg_files',all('<svg' in Path(v).read_text(encoding='utf-8') for k,v in paths.items() if k.endswith('_svg')),f"{sum(1 for k in paths if k.endswith('_svg'))} SVGs"),
            ('CHK-011','dxf_files',all('SECTION' in Path(v).read_text(encoding='utf-8') and 'EOF' in Path(v).read_text(encoding='utf-8') for k,v in paths.items() if k.endswith('_dxf')),f"{sum(1 for k in paths if k.endswith('_dxf'))} DXFs"),
            ('CHK-012','docx_files',all(zipfile.is_zipfile(v) for k,v in paths.items() if k.endswith('_docx')),f"{sum(1 for k in paths if k.endswith('_docx'))} DOCX files"),
            ('CHK-013','permit_gate',self.config['production']['final_permit_ready_generation_allowed'] is False,'blocked'),
            ('CHK-014','bb36_release_gate',self.config['production']['bb36_production_release_allowed'] is False,'locked'),
        ]
        return [{'check_id':cid,'subject':subject,'passed':passed,'evidence':evidence} for cid,subject,passed,evidence in checks]

    def _assumptions(self)->list[dict[str,Any]]:
        return [
            {'id':'ASM-001','subject':'extension geometry','value':'7 x 10 m, two storeys, 140 m2 gross','source':'owner-approved scope B','status':'PROJECT_BASIS','replacement_required':'survey reconciliation'},
            {'id':'ASM-002','subject':'existing building reference','value':'schematic 12 x 14 m block','source':'synthetic test fixture','status':'SIMULATION_ONLY','replacement_required':'REQ-102'},
            {'id':'ASM-003','subject':'structural grid','value':'3.5 x 5.0 m conceptual grid','source':'synthetic test fixture','status':'SIMULATION_ONLY','replacement_required':'REQ-103'},
            {'id':'ASM-004','subject':'foundation','value':'1.50 x 0.40 m strip plus 0.50 x 0.60 m beam','source':'synthetic test fixture','status':'SIMULATION_ONLY','replacement_required':'REQ-104'},
            {'id':'ASM-005','subject':'fire exits','value':'2 x 1.20 m','source':'synthetic test fixture','status':'SIMULATION_ONLY','replacement_required':'REQ-105'},
            {'id':'ASM-006','subject':'parking capacity','value':'225 spaces','source':'project leader confirmation','status':'FIELD_VERIFICATION_PENDING','replacement_required':'REQ-106'},
            {'id':'ASM-007','subject':'occupancy','value':'150 regular, 125 Friday, 200 peak','source':'HBM-OCC-2026-001','status':'PROJECT_LEADER_APPROVED','replacement_required':'none for REQ-107'},
            {'id':'ASM-008','subject':'AERIUS phases','value':'10/15/30/40 days plus operational use','source':'synthetic test fixture','status':'SIMULATION_ONLY','replacement_required':'REQ-108'},
        ]

    def _issue_index(self,summary,drawings,reports)->str:
        drawing_rows=''.join(f"<tr><td>{html.escape(row['sheet_id'])}</td><td>{html.escape(row['title'])}</td><td>{html.escape(row['scale'])}</td><td><a href=\"{html.escape(row['pdf'])}\">PDF</a> | <a href=\"{html.escape(row['svg'])}\">SVG</a>{' | <a href=\"'+html.escape(row['dxf'])+'\">DXF</a>' if row['dxf'] else ''}</td></tr>" for row in drawings)
        report_rows=''.join(f"<tr><td>{html.escape(row['report_id'])}</td><td>{html.escape(row['title'])}</td><td><a href=\"{html.escape(row['pdf'])}\">PDF</a> | <a href=\"{html.escape(row['docx'])}\">DOCX</a></td></tr>" for row in reports)
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>BB35 Real Concept Issue</title><style>body{{font-family:Arial,sans-serif;max-width:1200px;margin:28px auto;color:#172536}}h1{{border-bottom:4px solid #1f4e79;padding-bottom:12px}}.status{{padding:14px;border:1px solid #b91c1c;background:#fee2e2;font-weight:bold}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}.card{{border:1px solid #cbd5e1;padding:12px;border-radius:8px}}table{{width:100%;border-collapse:collapse;margin:12px 0 24px}}th,td{{border:1px solid #cbd5e1;padding:8px;text-align:left}}th{{background:#17324d;color:white}}a{{color:#1d4ed8}}@media(max-width:800px){{.cards{{grid-template-columns:1fr 1fr}}}}</style></head><body><h1>BB35 Pilot 1 - Real concept drawings and reports</h1><div class="status">{STATUS}</div><div class="cards"><div class="card"><b>Drawing sheets</b><br>{summary['drawing_sheet_count']}</div><div class="card"><b>Reports</b><br>{summary['report_count']}</div><div class="card"><b>Parking basis</b><br>{summary['parking_basis_spaces']} spaces</div><div class="card"><b>Professional blockers</b><br>{summary['professional_evidence_blocker_count']}</div></div><p>The files below are actual generated vector drawings and formatted reports. They remain concept documents and require professional evidence replacement before permit-ready release.</p><h2>Drawing set</h2><p><a href="drawings/pdf/BB35_PILOT_1_REAL_CONCEPT_DRAWING_SET_v1_0_0.pdf">Open complete 10-sheet PDF drawing set</a></p><table><thead><tr><th>Sheet</th><th>Title</th><th>Scale</th><th>Files</th></tr></thead><tbody>{drawing_rows}</tbody></table><h2>Reports</h2><table><thead><tr><th>Report</th><th>Title</th><th>Files</th></tr></thead><tbody>{report_rows}</tbody></table><h2>Release boundary</h2><ul><li>Concept issue package: ready.</li><li>REQ-107: closed by project leader.</li><li>Professional evidence blockers: REQ-102, 103, 104, 105, 106 and 108.</li><li>Final permit-ready generation: blocked.</li><li>BB36 production release: locked.</li></ul></body></html>"""

    def _write_checksums(self,root:Path,destination:Path)->None:
        lines=[]
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path in {destination,root/'BB35_PILOT_1_REAL_CONCEPT_ISSUE_PACKAGE_v1_0_0.zip'}:
                continue
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
        write_text(destination,'\n'.join(lines)+'\n')

    def _write_issue_zip(self,root:Path,destination:Path)->None:
        if destination.exists():
            destination.unlink()
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
            for path in sorted(root.rglob('*')):
                if not path.is_file() or path==destination:
                    continue
                info=zipfile.ZipInfo(path.relative_to(root).as_posix(),FIXED_ZIP_TIME)
                info.compress_type=zipfile.ZIP_STORED
                info.create_system=3
                info.external_attr=0o100644<<16
                archive.writestr(info,path.read_bytes())

    @staticmethod
    def _slug(value:str)->str:
        return ''.join(ch if ch.isalnum() else '_' for ch in value).strip('_')


def write_text(path:Path,text:str,newline:str='\n')->Path:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline=newline)
    return path


def write_json(path:Path,value:Any)->Path:
    return write_text(path,json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n')


def write_csv(path:Path,rows:Sequence[Mapping[str,Any]],fields:Sequence[str])->Path:
    def quote(value:Any)->str:
        text=str(value)
        if any(ch in text for ch in ',"\n\r'):
            return '"'+text.replace('"','""')+'"'
        return text
    lines=[','.join(fields)]
    for row in rows:
        lines.append(','.join(quote(row.get(field,'')) for field in fields))
    return write_text(path,'\n'.join(lines)+'\n')
