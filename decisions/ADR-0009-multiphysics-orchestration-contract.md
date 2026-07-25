# ADR-0009 — Multi-physics orchestration contract

Status: Accepted.

Engine adapters implement:
`handler(operation, input_data, context) -> dictionary`.

This keeps BB15 independent from solver-specific APIs.
