# Phoenix Cost Price Runtime Continuation — FIXED R4

This fix implements the nonblocking price-evidence policy in the actual Cost & Planning runtime rather than only in tests.

- Missing, stale, or currency-mismatched local market price evidence is recorded as `PRICE_EVIDENCE_UNRESOLVED`.
- It does not block Cost & Planning generation.
- No price, FX, tax, duty, freight, or material value is fabricated.
- Quantity items with no matching price remain unresolved while priced items may still form a partial estimate.
- Invalid quantities and other non-price faults remain blocking.
- The cost input register records `price_evidence_status` and the unresolved evidence list.
- The cost plan records `PRICE_EVIDENCE_UNRESOLVED_ESTIMATE_CONTINUES` or `PARTIAL_UNRESOLVED_PRICES` as applicable.
- R4 also rebinds `RUNNERS` after the material-mode wrappers because the original dictionary was created before those wrappers were defined.
- Professional / for-construction release remains locked.
