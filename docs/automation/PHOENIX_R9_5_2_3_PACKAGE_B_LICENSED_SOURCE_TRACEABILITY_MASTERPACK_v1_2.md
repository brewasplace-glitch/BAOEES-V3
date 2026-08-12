# PROJECT PHOENIX R9.5.2.3 - Package B Licensed Source Traceability Masterpack v1.2

Baseline: `e4d8651b227764a2b75b3fa0b21239a5476a985d`

## User confirmation
`IK BEVESTIG LICENSED USE - GO PACKAGE B TRACEABILITY`

Recorded as project-user confirmation for the supplied NEN Connect screenshots on 2026-08-12.

## Source bundle
A compact repository-local evidence PDF plus four raw screenshots are registered with SHA-256 validation.

Clauses/context:
- NEN-EN 1992-1-1 5.8.2(6)
- NEN-EN 1992-1-1 5.8.7.3
- Dutch National Annex A2:2025 context for 5.8.3.3, 5.8.5, 5.8.6 and 5.8.7.2

## Package B criteria
- SECOND_ORDER_AMPLIFICATION max 1.10
- GLOBAL_BUCKLING_FACTOR min 11.0
- STOREY_STABILITY_INDEX max 0.10

The latter two remain project-engineering-policy proxies. No literal Eurocode limit claim is made.

## Runtime behavior
R9.5.2.3 validates the evidence-bundle file and all raw source-image hashes before promoting the three
approved Package B criteria into the actual R9.5 input fields. Any mismatch fails closed.

R9.5.2 evidence intake is also annotated as traceability complete, but R9.5/R9.4/v8.6 remain the actual
qualification gates.

## Safety
- licensed use confirmed by the project user;
- extraction review limited to source-to-clause traceability;
- professional structural review is NOT claimed;
- automatic code-compliance claim remains disabled;
- legal adoption of Eurocode 2 in Suriname is not claimed;
- production release remains LOCKED.

## v1.1 regression-test transition repair

The v1.0 installer correctly passed all 24 new R9.5.2.3 dedicated tests, but then stopped because two
older R9.5.2.2 tests still asserted the pre-traceability state.

v1.1 updates only these two intentionally obsolete expectations:
- Package B traceability now must be complete;
- licensed source fields now must be populated and reviewed.

All other R9.5.2.2 tests remain unchanged. The R9.5.2.3 engine behavior and evidence bundle are unchanged.

## v1.2 binary evidence Git-safety repair

The v1.1 installer passed the complete Python and impact regression suite, but `git diff --cached --check`
then inspected the generated PDF as text and reported internal PDF syntax/xref lines as trailing whitespace.
Windows Git also warned that LF would be replaced by CRLF for the PDF, which is unacceptable for
checksum-controlled evidence.

v1.2 therefore adds repository-local Git attributes ONLY for this Package B evidence directory:

- the evidence PDF is `-text -diff`;
- raw JPG evidence is `-text -diff`.

This prevents CRLF normalization and text whitespace inspection of the binary evidence. Text source files
remain subject to the full `git diff --check` / `git diff --cached --check` gate.

The installer also disables the Git pager for its own checks so a failed diff can never strand the user at
an `(END)` pager screen.

All Package B SHA-256 validation, A+B logic, R9.5/R9.4/v8.6 gates and professional-review locks remain unchanged.
