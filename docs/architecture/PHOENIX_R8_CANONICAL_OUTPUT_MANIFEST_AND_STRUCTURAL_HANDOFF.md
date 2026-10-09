# PHOENIX R8 — Canonical Output Manifest + Structural Handoff Contract

R8 reuses the existing tropical residential output pipeline and the existing Phoenix structural session chain.

The manifest records exact A–E layout JSON, SVG plans and IFC files with hashes, the authoritative recommended geometry, tool handoff state and concept-only governance.

The structural handoff contract binds the recommended geometry to the existing `phoenix.autonomy.session_adapters.run_structural()` and `run_structural_chain()` v8.0–v8.12 flow.

It does not invent or replace the existing architecture-adapter inputs. The structural consumer still requires `architectural_model.json`, `detailed_elements.json` and `structural_project_profile.json`. Until those exist, handoff remains `CONTRACT_BOUND_INPUTS_REQUIRED` and solver execution is not started.

No professional approval, code-compliance claim, production release or construction approval is implied.
