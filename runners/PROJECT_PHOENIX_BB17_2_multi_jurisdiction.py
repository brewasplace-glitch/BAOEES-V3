"""BB17.2 self-test runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phoenix.building_code import CodeProfileRegistry
from phoenix.codepack_governance import CodepackRegistry
from phoenix.multi_jurisdiction import (
    JurisdictionRegistry,
    JurisdictionResolver,
    LocationContext,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    jurisdiction_registry = JurisdictionRegistry()
    definitions = jurisdiction_registry.load_directory(
        ROOT / "configs/phoenix/jurisdictions"
    )
    resolver = JurisdictionResolver(definitions)

    cases = [
        ("Bunschoten", LocationContext(country_code="NL"), "NL-EU"),
        ("Paramaribo", LocationContext(country_code="SR", district="Paramaribo"), "SR"),
        ("Bonaire", LocationContext(country_code="NL", island="Bonaire"), "BES"),
        ("Aruba", LocationContext(country_code="AW"), "AW"),
        ("Curacao", LocationContext(country_name="Curaçao"), "CW"),
        ("Sint Maarten", LocationContext(country_code="SX"), "SX"),
    ]
    selections = []
    for name, context, expected in cases:
        selection = resolver.resolve(context)
        if selection.jurisdiction_id != expected:
            raise RuntimeError(f"{name}: expected {expected}, got {selection.jurisdiction_id}")
        selections.append({"case": name, **selection.to_dict()})

    manifests = CodepackRegistry().load_directory(
        ROOT / "configs/phoenix/codepacks/foundations"
    )
    profile_registry = CodeProfileRegistry()
    profiles = [
        profile_registry.load_file(path)
        for path in sorted(
            (ROOT / "configs/phoenix/building_code_profiles/foundations").glob("*.json")
        )
    ]
    overlays = jurisdiction_registry.load_overlays(
        ROOT / "configs/phoenix/jurisdictions/engineering_overlays_v1_0.json"
    )

    result = {
        "status": "PASSED",
        "build_block": "BB17.2",
        "version": "1.0.0",
        "jurisdiction_count": len(definitions),
        "foundation_manifest_count": len(manifests),
        "foundation_profile_count": len(profiles),
        "engineering_overlay_count": len(overlays),
        "registry_fingerprint_sha256": jurisdiction_registry.fingerprint(definitions),
        "legal_mixing_policy": "exclusive_primary",
        "foundation_profiles_are_non_regulatory": True,
        "selections": selections,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
