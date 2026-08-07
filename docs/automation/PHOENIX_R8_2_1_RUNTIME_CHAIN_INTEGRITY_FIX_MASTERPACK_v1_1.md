# Project Phoenix R8.2.1 Runtime Chain Integrity Fix

Version: 1.1
Expected baseline: `7fed41720bc4f92007e8c4016b518ea1d370c4e7`

## Confirmed runtime failure

The live PAT run reached current v8.1 and v8.2 output generation and then failed in
`phoenix/autonomy/structural_session_chain.py` before the R8.1/R8.2 topology path:

`UnboundLocalError: action_load_for_solver`.

The variable was consumed by the autonomous v8.3 solver-basis builder before the R8.2
integration block initialized it.

## Fixes

1. Initialize `action_load_for_solver` immediately after successful v8.2 action-load generation.
2. Preserve R8.2 remapping as the authoritative downstream action-load state.
3. Feed the same remapped action-load model into v8.4 autonomous CalculiX result processing.
4. Remove the mutable previous `adapter_result.json` before every adapter execution.
5. Require any newly produced adapter result to match the exact current session ID before
   adapter state is persisted.
6. Add a mocked runtime regression that executes the v8.1 -> v8.2 -> autonomous solver basis
   -> R8.1 -> R8.2 path and proves the remapped load model reaches v8.3.

## Stale-result policy

Only the mutable `adapter_result.json` summary is cleared before a new adapter run. Detailed
historical project evidence is not deleted. A stale adapter result may never be promoted into a
new session's blocker register.

## Safety

- Automatic code-compliance claim: DISABLED
- Automatic structural approval: DISABLED
- Professional structural review: REQUIRED
- Automatic new supports/columns/rigid links/MPC/solver constraints: DISABLED
- For-construction / production release: LOCKED
- No optional-engine full-regression claim is made.
