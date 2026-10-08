# PHOENIX R5 FIX R1 — Distance-Sensitive Open-Source AEC Topology

R5 initial correctly failed because all new metrics saturated to identical values.

Fix R1 keeps the open-source-first architecture:
- TopologicPy TGraph is the required primary runtime engine.
- `TGraph.ByNetworkXGraph` creates the primary AEC graph from the proven geometric graph.
- `TGraph.Distance(..., type="topological")` is the required primary path-distance backend.
- NetworkX + Shapely remain fallback/validation only.
- OR-Tools CP-SAT remains the synthesis optimizer.

Metrics are now distance-sensitive:
- connectivity normalized per storey;
- mean room-to-circulation path;
- circulation accessibility;
- public/private mean transition path and privacy score;
- wet-core mean pair path and clustering score;
- route efficiency.

The real-project gate requires:
- five A-E variants;
- TopologicPy primary active for all five;
- TopologicPy Distance backend active for all five;
- zero isolated rooms;
- hard pass;
- at least two R5 metrics genuinely varying across A-E;
- five SVG + five IFC artifacts.

Release boundary: CONCEPT_AEC_TOPOLOGY_QA_NOT_FOR_CONSTRUCTION.
