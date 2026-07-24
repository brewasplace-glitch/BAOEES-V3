# CalculiX Integration Architecture

BB14 provides an offline-safe finite-element adapter.

- Native mode discovers `ccx` from `CALCULIX_CCX` or PATH.
- Offline mode writes a CalculiX-compatible B31 input deck and verifies one linear cantilever.
- Results are persisted with SHA-256 evidence and can be published to the Digital Twin and Knowledge Graph.

Shell, solid, contact, buckling, modal and nonlinear analyses are future expansion scope.
