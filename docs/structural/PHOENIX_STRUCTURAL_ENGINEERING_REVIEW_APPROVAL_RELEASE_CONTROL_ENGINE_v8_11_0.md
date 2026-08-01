# PROJECT PHOENIX — Structural Engineering Review, Approval & Release Control Engine v8.11.0

## Purpose
v8.11.0 is the formal release-control layer after the v8.10.0 structural engineering package QA/QC stage. It does not perform a new structural calculation and it does not invent professional approval. It records and verifies explicit human review evidence and explicit release authorization before changing a release state.

## Controlled release sequence
1. v8.10.0 package state must be `ENGINEERING_PACKAGE_QAQC_CANDIDATE_PASSED`.
2. The current structural-model, calculation-package, drawing-package and engineering-evidence fingerprints are consolidated into one package SHA256 fingerprint.
3. A human engineering reviewer explicitly approves the exact fingerprinted revision and scope.
4. Reviewer identity/signature evidence must be referenced; if configured, external signature verification must be reported as verified.
5. A human release authority explicitly authorizes either structural-model release or construction release for the exact same package fingerprint.
6. All configured gates are re-evaluated at release time.
7. On success, v8.11.0 writes `RELEASED` to the allowed scope(s), creates a release record and a hash-chain-capable ledger event, and writes the state to the Digital Twin.

## Change invalidation
Any change to the structural model, calculations, drawings or evidence index changes the package fingerprint. If it no longer matches the approved/authorized fingerprint, approval is invalidated, both releases remain `LOCKED`, and a new review is required.

## Human responsibility
Phoenix may automate evidence collection, gate checking and state transitions, but it must not fabricate a reviewer or release decision. The project must define which persons/roles are competent and legally authorized under the applicable jurisdiction, contracts and professional rules.

## Release states
- `HUMAN_REVIEW_REQUIRED`
- `RELEASE_LOCKED`
- `APPROVAL_INVALIDATED_REVIEW_REQUIRED`
- `STRUCTURAL_MODEL_RELEASED`
- `CONSTRUCTION_RELEASED`

## Separation of duties
The default policy requires the engineering reviewer and release authority to be different persons. Projects may configure this only if their governance permits it.

## Audit evidence
Every release evaluation contains the package fingerprint, reviewer/release-authority identifiers, timestamps, scopes, blockers, deterministic release ID, release-record fingerprint and release-ledger event hash.

## Safety defaults
Automatic professional engineering approval is disabled. Release without explicit human authorization is disabled. Default structural-model and construction release states are locked.
