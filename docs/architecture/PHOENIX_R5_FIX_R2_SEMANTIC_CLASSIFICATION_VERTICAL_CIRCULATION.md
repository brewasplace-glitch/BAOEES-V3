# PHOENIX R5 FIX R2 — Semantic Classification + Vertical Circulation

Evidence proved that `zone` values (`social`, `service`) were masking the specific
room semantics stored in `name`. This caused PUBLIC=0 and WET=0.

Fix:
- classify from zone + name + room_name + room_id;
- keep TopologicPy TGraph as primary AEC graph engine;
- keep OR-Tools CP-SAT as optimizer;
- keep NetworkX + Shapely as fallback/validation;
- add conceptual vertical circulation graph links between stair/circulation nodes
  on adjacent storeys;
- allow PUBLIC↔PRIVATE and WET↔WET topology paths across storeys;
- do not weaken any QA gate.

Expected Plutostraat counts per variant:
PUBLIC=3, PRIVATE=4, WET=3, CIRCULATION=2.

Release boundary: CONCEPT_AEC_TOPOLOGY_QA_NOT_FOR_CONSTRUCTION.
