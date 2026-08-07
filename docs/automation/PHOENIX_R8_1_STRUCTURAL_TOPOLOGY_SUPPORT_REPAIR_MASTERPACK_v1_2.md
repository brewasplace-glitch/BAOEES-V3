# Project Phoenix R8.1 — Structural Topology & Support Repair

## Purpose

R8.1 prevents a solver run from being accepted when the analytical structural
graph has floating members, unanchored components or provisional fixed-base
supports above the true lowest provisional base plane.

The pack also corrects the architectural-to-structural beam candidate derivation:
for rectangular spaces, preliminary support beams are derived on the two space
edges parallel to the slab's long direction, rather than as an isolated centre
line through the room. Shared identical edge segments are de-duplicated.

## Safety boundary

R8.1 does not invent new columns, supports, rigid links, shell ties or solver
constraints. A beam endpoint that only geometrically touches a shell edge or
another member without a shared analytical node is reported as unresolved and
blocks v8.3. No structural approval is granted.

## Chain location

v8.0 structural candidates
→ v8.1 analytical model
→ v8.2 loads
→ **R8.1 topology/support repair gate**
→ v8.3 solver input
→ v8.4 real CalculiX
→ R8 RC design candidate
→ v8.5 member verification

## Fail-closed reasons

- `STRUCTURAL_FOUNDATION_SUPPORT_PLANE_REQUIRED`
- `STRUCTURAL_LOAD_PATH_UNRESOLVED`
- `STRUCTURAL_UNANCHORED_COMPONENTS`

## Release policy

- automatic code-compliance claim: disabled
- automatic structural approval: disabled
- engineering review: required
- for-construction release: locked
- production release: locked


## v1.1 installer correction

The previous v1.0 installer correctly applied the R8.1 topology/support patch and passed
the dedicated R8.1 tests and v8.1 self-test, but its impact-scoped regression list exposed
a stale R7 static assertion. R8 had already replaced the direct R7 chain hook with
`autonomous_rc_design_candidate_v8_5_r8`, so the old assertion no longer described the
current chain architecture.

v1.1 keeps all R7 behavioral tests and updates only that static integration assertion to
accept either the original R7 hook or the R8 successor hook. This does not weaken any
engineering gate, does not change the R8 design-candidate behavior, and does not unlock
release.


## v1.2 regression-contract correction

v1.1 fixed the first stale R7 static assertion but the same test method contained a
second direct-chain assertion for `derive_member_verification_prerequisite`. R8 no longer
calls that function directly; its successor path calls `derive_rc_design_candidate`.

v1.2 updates the complete static R7 integration method in one atomic rewrite:

- original R7 module hook OR R8 successor module hook is accepted;
- `member_verification_input_requirement.json` remains mandatory;
- original R7 derivation call OR R8 successor derivation call is accepted.

All functional R7 prerequisite tests remain unchanged. This is test-contract maintenance,
not an engineering-gate bypass. Structural approval remains disabled and production
release remains locked.
