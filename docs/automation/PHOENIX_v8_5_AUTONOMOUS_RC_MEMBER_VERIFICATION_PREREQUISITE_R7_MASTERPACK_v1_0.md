# Project Phoenix v8.5 â€” Autonomous RC Member Verification Prerequisite R7

## Evidence basis

The PHOENIX-PAT-001 real-project run reached v8.5 after six successful real
CalculiX analyses.

Runtime inspection proved:

- 48 line members;
- all 48 reference C20/25 reinforced-concrete members;
- 34 reference 250x250 RC columns;
- 14 RC beams across several preliminary reference sections;
- solver material data is analysis-only;
- `capacity_strength_properties_used = false`;
- no verified reinforcement layout or member design resistance is available;
- architecture/material registers explicitly state that specific reinforcement
  or prestress design is still required.

Therefore the old generic blocker was too coarse.

## R7 behavior

When `member_verification_input` is absent:

1. Phoenix inspects the analytical members.
2. If RC members are detected, Phoenix writes
   `v8_5/member_verification_input_requirement.json`.
3. The artifact records member/material/section counts.
4. It explicitly identifies the missing RC engineering evidence.
5. The structural chain blocks with:
   `RC_MEMBER_DESIGN_RESISTANCE_EVIDENCE_REQUIRED`.
6. No normative value, reinforcement, member capacity or code-compliance result
   is invented.

Existing explicitly supplied valid `member_verification_input` remains
untouched and continues through the existing v8.5 engine.

## Next capability

The next autonomous capability after R7 is an RC Design Candidate Engine that
can only run after an explicit project RC design policy / normative basis is
approved and traceable.

## Release safety

- automatic code compliance claim: disabled
- automatic structural approval: disabled
- production release: locked
- professional engineering review: required