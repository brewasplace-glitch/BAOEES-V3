# PROJECT PHOENIX — Structural Code, Limit-State & Member Verification Engine v8.5.0

## Purpose
v8.5.0 consumes the validated analysis-result contract from v8.4.0 and evaluates explicit ULS/SLS verification rules for structural members. It is the first Phoenix layer that creates member-level demand/capacity verification evidence.

## Normative architecture
The engine deliberately does **not** invent design resistances, partial factors, buckling values, serviceability limits, interaction equations or code editions. Those inputs must be explicit and traceable to a project structural design basis, verified standards engine, licensed normative dataset or competent engineer input.

A result marked `PASS` therefore means: *the supplied rule has been evaluated and is within the supplied limit*. It does not by itself constitute statutory code compliance or signed structural approval.

## Supported verification rules
- `FORCE_CAPACITY_RATIO` — axial, shear, bending or torsion demand divided by an explicit resistance.
- `LINEAR_INTERACTION` — evaluates an explicitly selected linear interaction rule and preserves its normative reference.
- `BUCKLING_RESISTANCE_RATIO` — compression demand divided by an explicit buckling resistance.
- `NODE_DISPLACEMENT_LIMIT` — SLS displacement against an explicit project limit.
- `SLENDERNESS_LIMIT` — explicit slenderness ratio against an explicit limit.

## Hard gates
- source must identify the v8.4.0 validation contract;
- analysis validation state must be explicitly accepted by project policy;
- code basis requires jurisdiction, standard set, edition and source reference;
- every configured rule requires a normative reference when policy enables it;
- missing mandatory ULS/SLS coverage creates an incomplete verification state;
- failed mandatory rules create engineering review items;
- automatic code-compliance claim remains disabled;
- automatic structural approval remains disabled;
- structural model release remains locked.

## Digital Twin
The verification candidate is written conceptually to:

`CENTRAL_DIGITAL_TWIN.structural.code_limit_state_member_verification`

Normative references and rule results are preserved for later audit/review.

## Next release-gate capabilities
v8.5.0 intentionally leaves these gates closed for subsequent Phoenix build blocks:
1. global stability and second-order verification;
2. connection and support verification;
3. foundation-interface verification;
4. competent engineering review and release gate.
