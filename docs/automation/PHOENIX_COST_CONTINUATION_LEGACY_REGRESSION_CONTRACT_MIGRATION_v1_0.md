# Phoenix Cost Continuation Legacy Regression Contract Migration v1.0

This migration aligns the older project-context regression contract with the approved Phoenix material continuation policy.

- Missing current local material price evidence is not an adapter execution blocker.
- The cost workflow continues and records the affected price as unresolved.
- Phoenix must not fabricate a current price.
- Confirmed current local prices remain included in the estimate.
- Procurement and construction release controls remain separate from design/cost continuation.

The old regression expected `run_adapter("cost_planning", ...) == 10` when current local price evidence was incomplete. That expectation conflicts with the approved continuation policy and is migrated to a successful adapter return code while unresolved price evidence remains explicit.


## FIXED R3 method-scoped migration
The live legacy test contains more than one cost-planning blocking assertion. R3 scopes migration to the named test_09 method and changes every legacy return-code 10 assertion in that method to the nonblocking return-code 0 contract. Identical assertions in other test methods are deliberately left untouched. Missing/current-price values remain unresolved rather than fabricated.
