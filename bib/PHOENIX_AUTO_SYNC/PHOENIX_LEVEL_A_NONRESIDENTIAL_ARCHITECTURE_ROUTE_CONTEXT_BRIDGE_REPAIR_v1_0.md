# PHOENIX AUTO SYNC — Level-A Nonresidential Architecture Route Context Bridge v1.0

Root cause: the Level-A Generic Session architecture adapter ignored the selected project's
existing `NONRESIDENTIAL_REUSE_V1` contract and fell through to the residential-only text
bootstrap.

Repair: selected nonresidential project context is resolved before residential bootstrap.
Phoenix reuses a tracked project-scoped canonical architectural model and exposes a
lossless `levels -> storeys` Generic Session compatibility view.

No new architecture engine is created. Existing unsupported-use fail-closed behaviour is
preserved. Professional approval, production release and FOR CONSTRUCTION remain locked.
