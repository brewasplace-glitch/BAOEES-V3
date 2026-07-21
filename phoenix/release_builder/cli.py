"""Command-line interface for Phoenix Release Builder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import BuildRequest, PhoenixReleaseBuilder


def main() -> int:
    parser = argparse.ArgumentParser(description="Phoenix Release Builder")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    request = BuildRequest(
        repo_root=Path(args.repo_root).resolve(),
        release_id=str(manifest["release_id"]),
        version=str(manifest["version"]),
        output_dir=Path(args.output_dir).resolve(),
        include_files=tuple(str(item) for item in manifest["include_files"]),
        metadata=dict(manifest.get("metadata", {})),
    )
    result = PhoenixReleaseBuilder().build(request)
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
