# PHOENIX 4.41 — Phase 7 Open-Source Activation / Sandbox Review — 2026-09-16

RestrictedPython 8.5 is retained only as a possible future defense-in-depth restricted-language evaluator. It is not treated as an operating-system security boundary.

Microsoft Execution Containers (MXC) is retained as a future cross-platform isolation candidate, but its upstream project currently describes itself as an early preview and says its profiles should not yet be treated as security boundaries. It is therefore not activated in Phase 7 v1.

Phase 7 v1 instead performs non-executing AST and adapter-contract validation, then requires explicit SHA-bound human approval before a governed repository installation.
