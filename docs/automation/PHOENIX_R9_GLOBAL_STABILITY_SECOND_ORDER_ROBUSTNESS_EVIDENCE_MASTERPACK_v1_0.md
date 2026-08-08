# PROJECT PHOENIX R9 – Global Stability / Second-Order / Robustness Evidence Masterpack v1.0

## Purpose

R9 converts the fresh, repaired R8.2/R8.4/R8.5 structural state into a traceable global-stability evidence package before the existing v8.6 verifier. It does not weaken v8.6 and does not fabricate normative limits.

## Preconditions

- Current v8.5 state must be `MEMBER_VERIFICATION_CANDIDATE_PASSED`.
- The analytical model and current v8.4 CalculiX evidence must belong to the current structural chain.
- Production release remains locked.

## Autonomous evidence

R9 derives topological load paths, horizontal-shell diaphragm connectivity, first-order floor-response envelopes from the normalized CalculiX results, and (outside `PHOENIX_TEST_MODE`) attempts real CalculiX `NLGEOM` second-order reruns for lateral base load cases using the already executed v8.4 case decks. Those NLGEOM reruns remain evidence only unless the project input explicitly accepts that base-case scope for the v8.6 second-order candidate check.

R9 v1.0 deliberately does not approximate a global eigenvalue buckling factor, storey strength, or alternate-load-path capacity. Those remain explicit engineering evidence gaps unless supplied by a traceable project source.

## Normative limits

R9 contains no numeric global-stability acceptance limits. The generic v8.6 example file is explicitly forbidden as project evidence. Numeric limits and normative references must come from traceable project/standards/engineering input.

## Runtime integration

If no complete `global_stability_input` is already available, the structural chain invokes R9. If R9 can assemble all nine v8.6 checks it hands the resulting input to the unchanged v8.6 runner. Otherwise it writes a focused `global_stability_engineering_input_REQUIRED.json` template and blocks fail-closed with exact missing check types.

## Safety

Automatic code-compliance claim: disabled.
Automatic structural approval: disabled.
Automatic robustness approval: disabled.
Professional structural review: required.
For-construction / production release: locked.
