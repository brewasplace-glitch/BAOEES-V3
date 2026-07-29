# QGIS Registry Class Reference Recovery v5.3.9

## Confirmed failure
Phoenix `create_adapter()` executes:

`return ADAPTERS[engine_id]()`.

Therefore `ADAPTERS["qgis"]` must contain the adapter class, not an already
constructed adapter instance.

Incorrect:

`"qgis": QGISWindowsAdapter()`

Correct:

`"qgis": QGISWindowsAdapter`

## Recovery
v5.3.9:
1. removes every QGIS adapter constructor call from the active registry;
2. registers `QGISWindowsAdapter` as a class reference;
3. verifies no `QGISWindowsAdapter()` remains;
4. verifies `create_adapter()` can construct the adapter;
5. reruns the real QGIS acceptance and Phoenix detection;
6. requires `qgis: AVAILABLE`;
7. commits and pushes only after all controls pass.

No QGIS installation or download occurs.
