from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from phoenix.rulepack_compiler import (
    CompilationStatus,
    JurisdictionRulepackCompiler,
    RuleDefinitionRegistry,
)
from phoenix.rulepack_compiler.safety import UnsafeRuleDefinition


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def source(status="verified", jurisdiction="SR"):
    return Obj(
        id="SRC-SR-001",
        jurisdiction_id=jurisdiction,
        title="Official source",
        authority="Authority",
        canonical_uri="https://example.invalid/source",
        publication_id="PUB-001",
        edition="1",
        required=True,
        status=Obj(value=status),
    )


def catalog(status="validated", jurisdiction="SR"):
    return Obj(
        id="CAT-SR-1.0",
        jurisdiction_id=jurisdiction,
        version="1.0.0",
        status=status,
        sources=(source(jurisdiction=jurisdiction),),
    )


def mapping(status="approved", jurisdiction="SR"):
    return Obj(
        id="MAP-SR-001",
        jurisdiction_id=jurisdiction,
        phoenix_rule_id="SR-BLD-001",
        source_id="SRC-SR-001",
        locator="article 1",
        status=Obj(value=status),
        confidence="high",
        reviewer="Reviewer",
        reviewed_at="2026-07-26T00:00:00Z",
        interpretation_note="Test mapping",
        evidence_sha256="a" * 64,
    )


def mapping_set(status="validated", jurisdiction="SR"):
    return Obj(
        id="MAPSET-SR-1.0",
        jurisdiction_id=jurisdiction,
        version="1.0.0",
        status=status,
        required_rule_ids=("SR-BLD-001",),
        mappings=(mapping(jurisdiction=jurisdiction),),
    )


def definitions(status="validated", jurisdiction="SR"):
    return RuleDefinitionRegistry().load_dict({
        "id": "DEFSET-SR-1.0",
        "jurisdiction_id": jurisdiction,
        "version": "1.0.0",
        "status": status,
        "rules": [{
            "id": "SR-BLD-001",
            "title": "Project id",
            "description": "Project id is required.",
            "discipline": "administrative",
            "severity": "error",
            "expression": 'not_empty("project_id")',
            "failure_message": "Project id missing.",
            "evidence_paths": ["project_id"]
        }]
    })


class RulepackCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = JurisdictionRulepackCompiler()

    def test_approved_inputs_compile_bb17_profile(self) -> None:
        result = self.compiler.compile(catalog(), mapping_set(), definitions())
        self.assertEqual(CompilationStatus.COMPILED, result.status)
        self.assertEqual(1, len(result.profile["rules"]))
        self.assertFalse(result.profile["metadata"]["regulatory_activation_allowed"])

    def test_draft_mapping_set_is_blocked(self) -> None:
        result = self.compiler.compile(catalog(), mapping_set(status="draft-foundation"), definitions())
        self.assertEqual(CompilationStatus.BLOCKED, result.status)

    def test_unverified_source_is_blocked(self) -> None:
        cat = catalog()
        cat.sources = (source(status="discovered"),)
        result = self.compiler.compile(cat, mapping_set(), definitions())
        self.assertEqual(CompilationStatus.BLOCKED, result.status)

    def test_cross_jurisdiction_inputs_are_blocked(self) -> None:
        result = self.compiler.compile(catalog(), mapping_set(jurisdiction="NL-EU"), definitions())
        self.assertEqual(CompilationStatus.BLOCKED, result.status)

    def test_unsafe_definition_is_rejected(self) -> None:
        with self.assertRaises(UnsafeRuleDefinition):
            RuleDefinitionRegistry().load_dict({
                "id": "DEFSET-SR-UNSAFE",
                "jurisdiction_id": "SR",
                "version": "1.0.0",
                "status": "validated",
                "rules": [{
                    "id": "SR-BLD-001",
                    "title": "Unsafe",
                    "description": "Unsafe.",
                    "discipline": "test",
                    "severity": "error",
                    "expression": '__import__("os")',
                    "failure_message": "Unsafe."
                }]
            })

    def test_result_fingerprint_is_deterministic(self) -> None:
        first = self.compiler.compile(catalog(), mapping_set(), definitions())
        second = self.compiler.compile(catalog(), mapping_set(), definitions())
        self.assertEqual(
            first.metadata["fingerprint_sha256"],
            second.metadata["fingerprint_sha256"],
        )

    def test_blocked_profile_export_is_rejected(self) -> None:
        result = self.compiler.compile(catalog(status="draft"), mapping_set(), definitions())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                self.compiler.export_profile(result, Path(tmp) / "profile.json")

    def test_compiled_profile_export(self) -> None:
        result = self.compiler.compile(catalog(), mapping_set(), definitions())
        with tempfile.TemporaryDirectory() as tmp:
            path = self.compiler.export_profile(result, Path(tmp) / "profile.json")
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("SR", data["jurisdiction"])


if __name__ == "__main__":
    unittest.main()
