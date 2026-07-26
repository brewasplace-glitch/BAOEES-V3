"""BB17.4 self-test and foundation assessment runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from phoenix.rulepack_compiler import JurisdictionRulepackCompiler, RuleDefinitionRegistry
from phoenix.source_mapping import SourceMappingRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    registry = SourceMappingRegistry()
    catalogs = registry.load_source_catalog_directory(
        _ROOT / "configs" / "phoenix" / "source_catalogs" / "foundations"
    )
    mappings = registry.load_mapping_directory(
        _ROOT / "configs" / "phoenix" / "rule_mappings" / "foundations"
    )
    catalogs_by_jurisdiction = {item.jurisdiction_id: item for item in catalogs}
    mappings_by_jurisdiction = {item.jurisdiction_id: item for item in mappings}

    definition_registry = RuleDefinitionRegistry()
    compiler = JurisdictionRulepackCompiler()
    assessments = []
    for jurisdiction in sorted(catalogs_by_jurisdiction):
        mapping_set = mappings_by_jurisdiction[jurisdiction]
        definitions = definition_registry.load_dict({
            "id": f"PHX-RULE-DEFINITIONS-{jurisdiction}-FOUNDATION-1.0",
            "jurisdiction_id": jurisdiction,
            "version": "1.0.0",
            "status": "draft-foundation",
            "rules": [],
            "metadata": {"foundation_only": True},
        })
        result = compiler.compile(
            catalogs_by_jurisdiction[jurisdiction],
            mapping_set,
            definitions,
        )
        assessments.append({
            "jurisdiction_id": jurisdiction,
            "status": result.status.value,
            "issue_count": len(result.issues),
            "fingerprint_sha256": result.metadata["fingerprint_sha256"],
        })

    expected = {"NL-EU", "SR", "BES", "AW", "CW", "SX"}
    found = {item["jurisdiction_id"] for item in assessments}
    passed = found == expected and all(item["status"] == "blocked" for item in assessments)
    report = {
        "status": "PASSED" if passed else "FAILED",
        "build_block": "BB17.4",
        "version": "1.0.0",
        "jurisdiction_count": len(assessments),
        "expected_foundations_blocked": True,
        "assessments": assessments,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
