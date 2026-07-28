# Professional evidence intake instructions

Current accepted evidence: **0 of 6**.

## Intake location

`inputs/pilots/moskee_bunschoten/professional_evidence_intake_v2_3_0`

Each requirement has its own controlled folder. Copy the templates, add signed evidence files under `evidence/`, calculate SHA-256 hashes and run the closure gate.

## Mandatory sequence

1. Professional adviser submits project-specific signed evidence.
2. Phoenix validates schema, scope fields, document types, file existence, file hashes, registration data and forbidden simulation markers.
3. Critical findings are corrected.
4. Project leader reviews the exact manifest and records an `ACCEPTED` decision referencing its SHA-256.
5. Phoenix closes only that requirement.
6. When all six requirements are closed, Phoenix emits an accepted-evidence snapshot and change-impact register.
7. The unified production orchestrator must then regenerate model, drawings, reports and calculations before any final issue can be released.

REQ-107 remains closed under programme `HBM-OCC-2026-001` and is not reopened by this gate.
