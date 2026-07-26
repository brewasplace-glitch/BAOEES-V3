# BB17 — Building Code Engine v1.0.0

## Position

BB16 Building Model Engine → Phoenix Toolchain & Dependency Manager → BB17 Building Code Engine.

## Purpose

BB17 is the central, source-controlled rule and compliance-evidence layer above the canonical BB16 model.

## Capabilities

- JSON code-profile registry.
- Restricted rule-expression runtime without arbitrary Python execution.
- Applicability, severity, pass, fail, not-applicable and error states.
- Model-evidence extraction and rule-level source references.
- Deterministic evaluation identifiers and SHA-256 fingerprints.
- JSON compliance reports.
- Direct integration with BB16 objects through `to_dict()`.

## Bundled profile

`PHX-BASELINE-BUILDING-MODEL-1.0` checks Phoenix model integrity only. It does not establish Bbl, NEN, Eurocode, municipal, permit or other legal compliance.

## Official codepacks

Official jurisdiction packs must be separate, versioned, source-locked and reviewable. They must register publication identifiers, editions, amendments, applicability dates, rule-level references and validation evidence.

## Security boundary

Imports, attribute access, comprehensions, lambdas and arbitrary Python execution are rejected. Rule expressions can call only registered model-query helpers.

## Quality gates

Python compile, seven unit tests, self-test with eleven passing baseline rules, `git diff --check`, exact payload staging, automatic commit/push and transactional rollback.
