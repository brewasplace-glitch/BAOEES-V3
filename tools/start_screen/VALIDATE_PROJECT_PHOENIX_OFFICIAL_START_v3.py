#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

SKIP_PREFIXES = ("http://", "https://", "data:", "mailto:", "javascript:", "#")

def extract_local_refs(html: str):
    refs = re.findall(r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']", html, flags=re.I)
    out = []
    for ref in refs:
        ref = ref.strip()
        if not ref or ref.startswith(SKIP_PREFIXES):
            continue
        out.append(ref.split("?", 1)[0].split("#", 1)[0])
    return out

def validate(repo: Path):
    rec_path = repo / "configs" / "phoenix" / "official_start_screen_v3_migration_record.json"
    if not rec_path.is_file():
        raise SystemExit("Migration record missing")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    source = repo / rec["source_screen_directory"]
    target = repo / "phoenix" / "local_app" / "static" / "official_start_v3_0"
    if not source.is_dir() or not target.is_dir():
        raise SystemExit("Source or target official screen missing")
    old_index = source / "index.html"
    new_index = target / "index.html"
    if not old_index.is_file() or not new_index.is_file():
        raise SystemExit("Source or target index.html missing")
    old_html = old_index.read_text(encoding="utf-8", errors="replace")
    new_html = new_index.read_text(encoding="utf-8", errors="replace")
    if "PROJECT_PHOENIX_official_start_v3_client.js" not in new_html:
        raise SystemExit("Phoenix v3 client script reference missing")
    old_has_start = bool(re.search(r"START\s+PROJECTANALYSE", old_html, flags=re.I))
    new_has_start = bool(re.search(r"START\s+PROJECTANALYSE", new_html, flags=re.I))
    if old_has_start and not new_has_start:
        raise SystemExit("START PROJECTANALYSE was lost during migration")
    missing = []
    for ref in extract_local_refs(new_html):
        candidate = (target / ref).resolve()
        try:
            candidate.relative_to(target.resolve())
        except Exception:
            continue
        if not candidate.exists():
            missing.append(ref)
    if missing:
        raise SystemExit("Missing local assets: " + ", ".join(sorted(set(missing))))
    if not (target / "PROJECT_PHOENIX_official_start_v3_client.js").is_file():
        raise SystemExit("Phoenix v3 client JS missing")
    print("OFFICIAL START v3 STATIC REGRESSION VALIDATION: PASSED")
    print("START PROJECTANALYSE PRESERVATION:", "PASSED" if (not old_has_start or new_has_start) else "FAILED")
    print("LOCAL ASSET REFERENCES CHECKED:", len(extract_local_refs(new_html)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()
    validate(Path(args.repo).resolve())

if __name__ == "__main__":
    main()
