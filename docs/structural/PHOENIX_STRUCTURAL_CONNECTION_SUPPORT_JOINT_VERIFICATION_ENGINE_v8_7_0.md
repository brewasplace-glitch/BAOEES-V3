# PROJECT PHOENIX — Structural Connection, Support & Joint Verification Engine v8.7.0

## Purpose
v8.7.0 consumes the accepted global-stability/robustness candidate from v8.6.0 and creates auditable verification evidence for structural connections, supports and joints.

## Engineering boundary
The engine does **not** invent bolt, weld, anchor, bearing or connection resistances and does not assign a joint stiffness class without explicit evidence. Demand/capacity values and classifications must come from the project structural design basis, verified standards engine, calculation engine, licensed normative dataset or competent engineer input and must carry traceable references.

A `PASS` means only that the configured demand does not exceed the configured capacity, or that explicitly required classification evidence is present. It is not a statutory code-compliance declaration or signed structural approval.

## Supported checks
- `BEAM_COLUMN_CONNECTION`
- `BEAM_BEAM_CONNECTION`
- `COLUMN_BASE_CONNECTION`
- `SUPPORT_REACTION_CAPACITY`
- `BOLT_GROUP_CAPACITY`
- `WELD_CAPACITY`
- `ANCHOR_GROUP_CAPACITY`
- `BEARING_CAPACITY`
- `JOINT_STIFFNESS_CLASSIFICATION_EVIDENCE`

## Hard gates
- v8.6.0 source engine and accepted global-stability state are mandatory;
- jurisdiction, standard set, edition and source reference are mandatory;
- normative references are mandatory by default;
- every mandatory verification type must be represented;
- unknown connection/support/joint references are rejected;
- failed or incomplete mandatory checks create review items;
- automatic code-compliance and structural/connection approval remain disabled;
- structural model release remains locked.

## Digital Twin
Candidate evidence writes conceptually to:

`CENTRAL_DIGITAL_TWIN.structural.connection_support_joint_verification`

The writeback preserves check results, utilizations, classifications and normative references for audit and competent-engineer review.

## Remaining release gates
v8.7.0 intentionally leaves the following gates closed:
1. foundation-interface verification;
2. competent engineering review and release authorization.
