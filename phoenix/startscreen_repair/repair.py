#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List

SUSPICIOUS = (
    "Ã", "Â", "ðŸ", "â€", "âœ", "â˜", "âš", "â†", "â‡",
    "âŒ", "â”", "â–", "â—", "â˜", "ï¸", "�"
)
TEXT_EXTS = {".html", ".htm", ".js", ".json", ".css", ".txt", ".md"}
HOST_REL = "phoenix/local_app/static/official_start_v3_0/index.html"
HOST_DIR_REL = "phoenix/local_app/static/official_start_v3_0"

def git_ls_files(repo: Path) -> List[str]:
    p = subprocess.run(
        ["git", "-C", str(repo), "ls-files"],
        capture_output=True, text=True
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr or "git ls-files failed")
    return [x.strip().replace("\\", "/") for x in p.stdout.splitlines() if x.strip()]

def suspicious_count(text: str) -> int:
    return sum(text.count(x) for x in SUSPICIOUS)

def decode_bytes(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        try:
            from charset_normalizer import from_bytes
            best = from_bytes(data).best()
            if best is None:
                raise RuntimeError("charset-normalizer found no usable encoding")
            return str(best), str(best.encoding or "detected")
        except Exception as exc:
            raise RuntimeError(f"Unable to decode text file: {exc}") from exc

def fix_mojibake(text: str) -> str:
    try:
        from ftfy import fix_encoding
        return fix_encoding(text)
    except Exception as exc:
        raise RuntimeError(f"ftfy unavailable or failed: {exc}") from exc

def canonicalize_labels(text: str) -> str:
    replacements = [
        ("PROJECT PHOENIX 3.0.2", "PROJECT PHOENIX 4.41"),
        ("PROJECT PHOENIX 3.0", "PROJECT PHOENIX 4.41"),
        ("Official Start v3.0.2", "Official Start v4.41"),
        ("Official Start v3.0", "Official Start v4.41"),
        ("START v3.0.2", "START v4.41"),
        ("START v3.0", "START v4.41"),
        ("Official Start v3", "Official Start v4.41"),
    ]
    out = text
    for old, new in replacements:
        out = out.replace(old, new)

    # Browser tab title variants.
    out = re.sub(
        r'(<title[^>]*>)(.*?PROJECT\s+PHOENIX).*?(</title>)',
        r'\1PROJECT PHOENIX 4.41 · Official Start\3',
        out,
        flags=re.I | re.S,
    )
    return out

def ensure_utf8_meta(text: str) -> str:
    if not re.search(r'<meta\s+[^>]*charset\s*=', text, flags=re.I):
        m = re.search(r'<head[^>]*>', text, flags=re.I)
        if m:
            return text[:m.end()] + '\n<meta charset="utf-8">' + text[m.end():]
        return '<meta charset="utf-8">\n' + text
    return re.sub(
        r'<meta\s+[^>]*charset\s*=\s*["\']?[^"\'>\s]+["\']?[^>]*>',
        '<meta charset="utf-8">',
        text,
        count=1,
        flags=re.I,
    )

def local_refs(index_text: str) -> List[str]:
    refs = []
    for attr in ("src", "href"):
        for value in re.findall(
            rf'{attr}\s*=\s*["\']([^"\']+)["\']',
            index_text, flags=re.I
        ):
            if value.startswith(("http://", "https://", "//", "data:", "#")):
                continue
            clean = value.split("?", 1)[0].split("#", 1)[0]
            if clean:
                refs.append(clean)
    return refs

def target_files(repo: Path) -> List[Path]:
    host = repo / HOST_REL
    if not host.exists():
        raise RuntimeError(f"Canonical served start host missing: {HOST_REL}")

    files = []
    host_dir = repo / HOST_DIR_REL
    for p in host_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            files.append(p)

    index_text, _ = decode_bytes(host.read_bytes())
    for ref in local_refs(index_text):
        p = (host.parent / ref).resolve()
        try:
            p.relative_to(repo.resolve())
        except ValueError:
            continue
        if p.is_file() and p.suffix.lower() in TEXT_EXTS and p not in files:
            files.append(p)

    return sorted(files)

def audit(repo: Path) -> Dict:
    tracked = set(git_ls_files(repo))
    host = repo / HOST_REL
    text, enc = decode_bytes(host.read_bytes())
    candidates = []
    for rel in tracked:
        low = rel.lower()
        if "official_start" not in low or not low.endswith((".html", ".htm")):
            continue
        p = repo / rel
        try:
            t, e = decode_bytes(p.read_bytes())
        except Exception:
            continue
        candidates.append({
            "path": rel,
            "encoding": e,
            "suspicious_count": suspicious_count(t),
            "has_4_41": "4.41" in t,
            "has_3_0": "3.0" in t,
        })
    return {
        "canonical_served_host": HOST_REL,
        "host_exists": host.exists(),
        "host_encoding": enc,
        "host_suspicious_count": suspicious_count(text),
        "host_has_project_phoenix_3": "PROJECT PHOENIX 3" in text,
        "host_has_project_phoenix_4_41": "PROJECT PHOENIX 4.41" in text,
        "start_candidates": candidates,
    }

def repair(repo: Path, report_path: Path) -> Dict:
    before_audit = audit(repo)
    changed = []
    file_reports = []

    files = target_files(repo)
    for path in files:
        rel = path.relative_to(repo).as_posix()
        original_bytes = path.read_bytes()
        text, enc = decode_bytes(original_bytes)
        before = suspicious_count(text)

        fixed = fix_mojibake(text)
        if rel == HOST_REL:
            fixed = canonicalize_labels(fixed)
            fixed = ensure_utf8_meta(fixed)

        after = suspicious_count(fixed)
        if fixed != text or enc.lower() != "utf-8":
            path.write_text(fixed, encoding="utf-8", newline="\n")
            changed.append(rel)

        file_reports.append({
            "path": rel,
            "source_encoding": enc,
            "suspicious_before": before,
            "suspicious_after": after,
            "changed": rel in changed,
        })

    host_text = (repo / HOST_REL).read_text(encoding="utf-8")
    # Cache-bust the bridge so the browser cannot keep the old floating toolbar JS.
    host_text = re.sub(
        r'(<script\s+src=["\']\./phoenix_detv_cad_bridge\.js)(?:\?[^"\']*)?(["\'])',
        r'\1?v=4.41-utf8-native-r1\2',
        host_text,
        flags=re.I,
    )
    (repo / HOST_REL).write_text(host_text, encoding="utf-8", newline="\n")
    if HOST_REL not in changed:
        changed.append(HOST_REL)

    after_audit = audit(repo)
    result = {
        "status": "PASS",
        "before": before_audit,
        "after": after_audit,
        "files": file_reports,
        "changed_files": sorted(set(changed)),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

def verify(repo: Path, report_path: Path) -> Dict:
    host = repo / HOST_REL
    text = host.read_text(encoding="utf-8")
    errors = []

    if "PROJECT PHOENIX 4.41" not in text:
        errors.append("visible PHOENIX 4.41 branding not found in canonical host")
    if re.search(r'PROJECT PHOENIX 3(?:\.0(?:\.2)?)?', text, flags=re.I):
        errors.append("stale PROJECT PHOENIX 3.x branding remains")
    if "charset=\"utf-8\"" not in text.lower():
        errors.append("UTF-8 meta declaration missing")
    if suspicious_count(text) > 0:
        errors.append(
            f"canonical host still contains {suspicious_count(text)} known mojibake markers"
        )
    if "phoenix_detv_cad_bridge.js?v=4.41-utf8-native-r1" not in text:
        errors.append("CAD bridge cache-busting source reference missing")

    bridge = repo / HOST_DIR_REL / "phoenix_detv_cad_bridge.js"
    if not bridge.exists():
        errors.append("native DE TV CAD bridge missing")
    else:
        js = bridge.read_text(encoding="utf-8")
        for needle in (
            "Project CAD", "Open CAD bestand", "DETV_NATIVE_CAD_CONTROLS",
            "repairDocumentText", "127.0.0.1:8765"
        ):
            if needle not in js:
                errors.append(f"bridge requirement missing: {needle}")
        toolbar_match = re.search(
            r"#phoenix-cad-toolbar\s*\{([^}]*)\}",
            js,
            flags=re.I | re.S,
        )
        if not toolbar_match:
            errors.append("native DE TV CAD toolbar CSS block missing")
        else:
            toolbar_css = re.sub(r"\s+", "", toolbar_match.group(1).lower())
            if "position:fixed" in toolbar_css:
                errors.append("old floating fixed CAD toolbar styling remains")
            if "position:static!important" not in toolbar_css:
                errors.append("native DE TV CAD toolbar is not explicitly static")

    if errors:
        raise RuntimeError("; ".join(errors))

    data = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "status": "PASS",
        "canonical_host": HOST_REL,
        "host_suspicious_count": suspicious_count(text),
        "changed_files": data.get("changed_files", []),
    }

def self_test():
    sample = "ðŸŽ¤ Spraak âœ”"
    fixed = fix_mojibake(sample)
    assert "🎤" in fixed
    assert "✔" in fixed
    html = '<html><head><title>PROJECT PHOENIX 3.0.2</title></head><body>PROJECT PHOENIX 3.0.2 START v3.0.2</body></html>'
    out = ensure_utf8_meta(canonicalize_labels(html))
    assert "PROJECT PHOENIX 4.41" in out
    assert 'charset="utf-8"' in out
    print("PHOENIX_4_41_STARTSCREEN_REPAIR_SELF_TEST=PASS")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--repair", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.repo_root:
        ap.error("--repo-root required")
    repo = args.repo_root.resolve()

    if args.audit:
        print(json.dumps(audit(repo), indent=2))
        return 0
    if args.repair:
        if not args.report:
            ap.error("--report required")
        print(json.dumps(repair(repo, args.report), indent=2))
        print("STARTSCREEN_UTF8_REPAIR=PASS")
        return 0
    if args.verify:
        if not args.report:
            ap.error("--report required")
        print(json.dumps(verify(repo, args.report), indent=2))
        print("STARTSCREEN_CANONICAL_VERIFY=PASS")
        return 0

    ap.error("choose --audit, --repair, --verify, or --self-test")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
