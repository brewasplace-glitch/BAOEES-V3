# PROJECT PHOENIX 4.41 — Phase 19 FIX R1

Phase 19 FIX R1 repairs the Official Start Screen binding for integrated
project orchestration.

## Corrected contract

- A visible `locationReference` field supplies `location_reference`.
- The saved Official Start upload batch is transmitted to the project session
  and bound to the integrated orchestration contract.
- Upload manifests are path-safe and SHA-256 bound. Upload presence and
  integrity do not constitute professional or technical verification.
- A prior `HOLD_MISSING_PROJECT_INPUTS` run can be resumed by its exact run ID.
- Resume locates the exact originating session by deterministic contract hash,
  accepts only location and upload-batch completion, and records the predecessor
  run ID. A non-held run cannot be resumed through this route.

## Safety boundaries

- No design result is fabricated.
- No engine is activated automatically.
- No professional release is performed automatically.
- Missing location or uploads stop the browser flow before a new session is
  created.
- Invalid, absent or empty upload manifests fail closed.
