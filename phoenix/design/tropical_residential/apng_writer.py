from __future__ import annotations

import binascii
import struct
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunks(data: bytes) -> List[Tuple[bytes, bytes]]:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Not a PNG file")
    out: List[Tuple[bytes, bytes]] = []
    pos = len(PNG_SIGNATURE)
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos+4])[0]
        ctype = data[pos+4:pos+8]
        cdata = data[pos+8:pos+8+length]
        crc = data[pos+8+length:pos+12+length]
        if len(cdata) != length or len(crc) != 4:
            raise ValueError("Truncated PNG chunk")
        out.append((ctype, cdata))
        pos += 12 + length
        if ctype == b"IEND":
            break
    return out


def _pack_chunk(ctype: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(ctype)
    crc = binascii.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def inspect_apng(path: Path) -> dict:
    data = Path(path).read_bytes()
    chunks = _chunks(data)
    frame_controls = [x for x in chunks if x[0] == b"fcTL"]
    acts = [x for x in chunks if x[0] == b"acTL"]
    frame_count = None
    loops = None
    if acts:
        frame_count, loops = struct.unpack(">II", acts[0][1])
    return {
        "is_png": data.startswith(PNG_SIGNATURE),
        "is_apng": bool(acts and frame_controls),
        "frame_count": frame_count,
        "frame_control_count": len(frame_controls),
        "loops": loops,
        "bytes": len(data),
    }


def write_apng(
    frame_paths: Sequence[Path],
    output_path: Path,
    delay_ms: int = 1800,
    loops: int = 0,
) -> dict:
    if len(frame_paths) < 2:
        raise ValueError("APNG requires at least two frames")
    if delay_ms <= 0:
        raise ValueError("delay_ms must be positive")

    parsed = []
    for p in frame_paths:
        data = Path(p).read_bytes()
        chunks = _chunks(data)
        ihdr = next((d for t, d in chunks if t == b"IHDR"), None)
        idats = [d for t, d in chunks if t == b"IDAT"]
        if ihdr is None or not idats:
            raise ValueError(f"PNG is missing IHDR/IDAT: {p}")
        parsed.append((Path(p), chunks, ihdr, idats))

    reference_ihdr = parsed[0][2]
    width, height = struct.unpack(">II", reference_ihdr[:8])
    for p, _, ihdr, _ in parsed[1:]:
        if ihdr != reference_ihdr:
            raise ValueError(f"All APNG frames must have identical IHDR: {p}")

    # Keep the first frame's safe pre-IDAT ancillary chunks.
    first_chunks = parsed[0][1]
    ancillary = []
    for ctype, cdata in first_chunks:
        if ctype == b"IHDR":
            continue
        if ctype == b"IDAT":
            break
        if ctype not in {b"acTL", b"fcTL", b"fdAT"}:
            ancillary.append((ctype, cdata))

    out = bytearray(PNG_SIGNATURE)
    out += _pack_chunk(b"IHDR", reference_ihdr)
    for ctype, cdata in ancillary:
        out += _pack_chunk(ctype, cdata)

    out += _pack_chunk(b"acTL", struct.pack(">II", len(parsed), int(loops)))

    seq = 0
    delay_num = int(delay_ms)
    delay_den = 1000

    for index, (_, _, _, idats) in enumerate(parsed):
        fctl = struct.pack(
            ">IIIIIHHBB",
            seq,
            width,
            height,
            0,
            0,
            delay_num,
            delay_den,
            0,  # APNG_DISPOSE_OP_NONE
            0,  # APNG_BLEND_OP_SOURCE
        )
        out += _pack_chunk(b"fcTL", fctl)
        seq += 1

        if index == 0:
            for data in idats:
                out += _pack_chunk(b"IDAT", data)
        else:
            for data in idats:
                out += _pack_chunk(b"fdAT", struct.pack(">I", seq) + data)
                seq += 1

    out += _pack_chunk(b"IEND", b"")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(out))
    return inspect_apng(output_path)
