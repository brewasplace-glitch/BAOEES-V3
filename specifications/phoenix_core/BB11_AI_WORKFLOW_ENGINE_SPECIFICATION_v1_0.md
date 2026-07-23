# BB11 AI Workflow Engine Specification v1.0

## Required capabilities

1. Workflow definitions with named steps
2. Dependency validation and topological ordering
3. Cycle detection
4. Conditional execution
5. Bounded retry handling
6. Fail-fast execution
7. Assumption recording with source and confidence
8. Decision records with rationale and error evidence
9. Deterministic JSON evidence
10. Knowledge Graph publication

## Acceptance criteria

- Python compile validation passes
- All BB11 unit tests pass
- BB11 self-test passes
- `git diff --check` passes
- Automatic staging includes only intended non-ignored changes
- Commit and push occur only after all checks succeed
- Final repository state is clean
