# BB17.3 — Jurisdiction Source Acquisition & Rule Mapping Engine v1.0.0

## Position

BB17 Building Code Engine → BB17.1 Governance → BB17.2 Multi-Jurisdiction
Foundation → BB17.3 Source Acquisition & Rule Mapping.

## Purpose

BB17.3 provides the controlled bridge between official regulatory sources and
Phoenix building-code rules for European Netherlands, Suriname, Caribbean
Netherlands, Aruba, Curaçao and Sint Maarten.

## Capabilities

- Versioned source catalogs per jurisdiction.
- Safe HTTP/HTTPS source-reference validation.
- Source status, edition, effective-date and checksum metadata.
- Rights-aware storage policy: metadata-only, public text or restricted.
- Non-executing acquisition and change-detection plans.
- Rule-to-source mappings with article/section locators.
- Draft, mapped, reviewed, approved and rejected mapping workflow.
- Source and mapping coverage reports.
- Activation gate requiring verified sources and approved mappings.
- Deterministic fingerprints for catalogs, mappings and assessments.
- Explicit rejection of cross-jurisdiction mapping.

## Safety boundary

v1.0.0 performs no automatic network download and stores no regulatory source
text. Foundation catalogs contain metadata and review queues only. A legal
codepack remains inactive until required sources are independently verified and
all required Phoenix rules have approved source mappings.

## Next content waves

The engine supports controlled content waves in the order NL-EU, SR, BES, AW,
CW and SX. Each wave can add verified source metadata, rule identifiers,
article locators, interpretations and review evidence without changing the core
BB17.3 runtime.
