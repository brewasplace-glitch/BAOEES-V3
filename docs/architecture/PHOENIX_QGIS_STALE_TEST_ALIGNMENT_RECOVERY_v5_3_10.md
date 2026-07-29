# QGIS Stale Test Alignment Recovery v5.3.10

## Confirmed state
The QGIS registry class-reference correction succeeded:

- registry mode: `CLASS_REFERENCE`;
- adapter construction deferred to `create_adapter()`;
- dedicated registry class-reference verifier passed.

The remaining failure was a stale unit test that searched for an old human-readable
phrase (`active registry reference`) that no longer exists in the updated tool.

## Recovery
v5.3.10 replaces the stale phrase check with semantic tests that verify:

1. the v5.3.9 activator exists;
2. it explicitly enforces `CLASS_REFERENCE`;
3. it rejects `QGISWindowsAdapter()` instances;
4. it defers construction to `create_adapter()`;
5. the dedicated registry verifier exists;
6. the verifier rejects adapter instances and confirms the class reference.

No QGIS installation or download occurs.
