\
"""Small dependency-free deterministic PDF writer for concept evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


def _escape(value: str) -> str:
    return (
        value.replace('\\', '\\\\')
        .replace('(', '\\(')
        .replace(')', '\\)')
    )


def _ascii(value: object) -> str:
    text = str(value)
    replacements = {
        '\u00b2': '2',
        '\u00b3': '3',
        '\u00d7': 'x',
        '\u2013': '-',
        '\u2014': '-',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u00e9': 'e',
        '\u00eb': 'e',
        '\u00ef': 'i',
        '\u00fc': 'u',
        '\u00f6': 'o',
        '\u00e4': 'a',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.encode('ascii', 'replace').decode('ascii')


@dataclass
class PDFPage:
    width: float = 842.0
    height: float = 595.0
    commands: list[str] = field(default_factory=list)

    def text(self, x: float, y: float, value: object, size: float = 10.0) -> None:
        safe = _escape(_ascii(value))
        self.commands.append(
            f'BT /F1 {size:.2f} Tf {x:.2f} {y:.2f} Td ({safe}) Tj ET'
        )

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.8) -> None:
        self.commands.append(
            f'{width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S'
        )

    def rect(self, x: float, y: float, width: float, height: float, stroke: float = 0.8) -> None:
        self.commands.append(
            f'{stroke:.2f} w {x:.2f} {y:.2f} {width:.2f} {height:.2f} re S'
        )

    def fill_rect(self, x: float, y: float, width: float, height: float, gray: float = 0.92) -> None:
        self.commands.append(
            f'{gray:.3f} g {x:.2f} {y:.2f} {width:.2f} {height:.2f} re f 0 g'
        )

    def polyline(self, points: Iterable[tuple[float, float]], close: bool = False, width: float = 0.8) -> None:
        pts = list(points)
        if not pts:
            return
        command = f'{width:.2f} w {pts[0][0]:.2f} {pts[0][1]:.2f} m '
        command += ' '.join(f'{x:.2f} {y:.2f} l' for x, y in pts[1:])
        if close:
            command += ' h'
        command += ' S'
        self.commands.append(command)


class SimplePDF:
    def __init__(self) -> None:
        self.pages: list[PDFPage] = []

    def add_page(self, width: float = 842.0, height: float = 595.0) -> PDFPage:
        page = PDFPage(width=width, height=height)
        self.pages.append(page)
        return page

    def save(self, path: str | Path) -> Path:
        if not self.pages:
            raise ValueError('A PDF requires at least one page.')
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        objects: dict[int, bytes] = {}
        page_refs: list[str] = []
        next_obj = 4
        for page in self.pages:
            page_obj = next_obj
            content_obj = next_obj + 1
            next_obj += 2
            page_refs.append(f'{page_obj} 0 R')
            stream = ('\n'.join(page.commands) + '\n').encode('ascii')
            objects[content_obj] = (
                f'<< /Length {len(stream)} >>\nstream\n'.encode('ascii')
                + stream
                + b'endstream'
            )
            objects[page_obj] = (
                f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page.width:.2f} {page.height:.2f}] '
                f'/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj} 0 R >>'
            ).encode('ascii')

        objects[1] = b'<< /Type /Catalog /Pages 2 0 R >>'
        objects[2] = (
            f'<< /Type /Pages /Kids [{" ".join(page_refs)}] /Count {len(page_refs)} >>'
        ).encode('ascii')
        objects[3] = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'

        max_obj = max(objects)
        output = bytearray(b'%PDF-1.4\n%PHOENIX\n')
        offsets = [0] * (max_obj + 1)
        for number in range(1, max_obj + 1):
            offsets[number] = len(output)
            output.extend(f'{number} 0 obj\n'.encode('ascii'))
            output.extend(objects[number])
            output.extend(b'\nendobj\n')

        xref = len(output)
        output.extend(f'xref\n0 {max_obj + 1}\n'.encode('ascii'))
        output.extend(b'0000000000 65535 f \n')
        for number in range(1, max_obj + 1):
            output.extend(f'{offsets[number]:010d} 00000 n \n'.encode('ascii'))
        output.extend(
            f'trailer\n<< /Size {max_obj + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('ascii')
        )
        destination.write_bytes(output)
        return destination
