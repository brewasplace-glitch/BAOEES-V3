# Project Phoenix — Package E C05 DOCX Review Bridge v1.0

## Purpose

Connect the installed C05 Generated Input Validation List to an operational,
reviewer-friendly DOCX round trip for Package E.

Flow:

existing R9.3/R9.5 evidence
→ Phoenix auto-generated Package-E candidate inputs
→ existing C05 validation list
→ reviewer-friendly DOCX
→ reviewer CONFIRM / MODIFY / NOT_APPLICABLE / DEFER
→ returned DOCX intake
→ canonical reviewed-input JSON
→ existing Package-E validation/requalification chain.

## Maximum automatic generation

Phoenix automatically contributes all values it can safely derive, including
project/package identity, current R9.5 state, R9.3 case count, and observed R9.3
proxy-ratio range.

The professional acceptance criterion remains empty. The observed R9.3 minimum is
shown as context only and is never promoted to a professional acceptance criterion
or independent engineering evidence.

## Open-source-first

Primary: `python-docx` (MIT), already present in the Phoenix project dependency
set and suitable for creating/updating Word DOCX documents.

Alternative reviewed: `docx2python`, useful for DOCX extraction. It is not added
because Phoenix already has `python-docx` and adding a second mandatory DOCX
dependency would provide no necessary capability for this bridge.

## Safety

The bridge never fabricates:
- professional review,
- reviewer identity,
- reviewer qualification,
- `REVIEWED` status,
- acceptance criteria,
- independent engineering evidence.

Production release remains `LOCKED`.
