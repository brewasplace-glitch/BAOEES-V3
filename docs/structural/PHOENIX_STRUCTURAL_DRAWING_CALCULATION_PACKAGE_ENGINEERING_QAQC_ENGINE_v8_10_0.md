# Project Phoenix Structural Drawing, Calculation Package & Engineering QA/QC Engine v8.10.0

## Purpose

v8.10.0 consolidates the structural evidence chain from v8.0.0 through v8.9.0 into a controlled engineering-package candidate. It does not replace engineering judgement and it does not release a structure for construction.

The engine creates and validates a structured dossier containing drawing, calculation, verification, assumption, QA/QC and evidence registers. It also creates a deterministic SHA-256 fingerprint over the canonical package metadata so later pipeline stages can detect unexpected package-content changes.

## Inputs

The engine requires:

- an accepted v8.9.0 foundation design / reinforcement / detailing candidate;
- explicit evidence references for v8.0.0 through v8.9.0;
- a controlled engineering-package basis and revision;
- drawing and calculation registers;
- member, global-stability, connection, foundation-interface and foundation-design verification registers;
- an explicit engineering-assumption register;
- mandatory QA/QC evidence;
- a mandatory human engineering review gate.

## QA/QC scope

The implemented QA/QC contract covers:

1. source-layer completeness;
2. drawing/calculation cross-reference resolution;
3. drawing and calculation revision coherence;
4. verification-register completeness;
5. normative-reference completeness;
6. assumption-register completeness;
7. open-review-item reconciliation;
8. Digital Twin cross-reference evidence;
9. quantity/schedule coherence evidence;
10. package identifier coherence.

Missing or failed mandatory evidence creates a blocker. Missing mandatory source layers or registers produces an `INCOMPLETE` state. Other blockers produce a `REVIEW_REQUIRED` state.

## Generated package metadata

The report contains:

- source-layer evidence matrix;
- drawing register;
- calculation register;
- structural verification registers;
- engineering assumption register;
- QA/QC checks and findings;
- evidence index with record fingerprints;
- package manifest with deterministic package fingerprint;
- maximum reported utilization from the verification chain;
- technical release-readiness matrix;
- Digital Twin writeback contract.

## Safety and release semantics

`ENGINEERING_DRAWING_CALCULATION_PACKAGE_QAQC_CANDIDATE_PASSED` means only that the configured technical evidence package passed this engine's explicit consistency and completeness rules.

It does **not** mean:

- code compliance has been professionally certified;
- calculations or drawings have been professionally approved;
- a competent structural engineer has signed the design;
- construction release has been issued;
- the structural model is released.

A competent structural engineer remains mandatory. Even if the human-review status in the input is `APPROVED`, v8.10.0 does not automatically unlock either construction release or structural-model release. A separate controlled release process is required.

## Digital Twin writeback

The writeback namespace is:

`structural.engineering_package_qaqc.v8_10_0`

It includes the verification state, package manifest, drawing/calculation/verification registers, assumptions, QA/QC findings, evidence index and release-readiness metadata.

## Validation

The package includes an embedded self-test and 32 unit tests covering source gates, evidence completeness, revision coherence, cross-references, verification states, assumptions, QA/QC blockers, evidence fingerprints, Digital Twin writeback and release-lock behavior.
