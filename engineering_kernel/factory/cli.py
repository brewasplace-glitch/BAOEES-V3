from __future__ import annotations
import argparse
import json
from pathlib import Path
from .generator import generate_domain_scaffolding

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PEK scaffolding from EKMS.")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--output-root", default="engineering_kernel/generated")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = generate_domain_scaffolding(
        Path(args.repository_root), args.domain, Path(args.output_root),
        args.limit, args.overwrite, args.dry_run
    )
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
