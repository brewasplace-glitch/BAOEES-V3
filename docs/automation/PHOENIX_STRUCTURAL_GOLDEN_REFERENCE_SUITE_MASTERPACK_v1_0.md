# PROJECT PHOENIX — Structural Golden Reference Suite v1.0

Required baseline: `373913ee780f9670b3af5133ee88b5597dcd2146`

Suite `PHX-STRUCT-GOLDEN-SUITE-001` contains:

1. `PHX-GOLDEN-SCIA-BEAM-001`: simply supported beam, L=5 m, q=1 kN/m, R=2.5 kN each, Mmax=3.125 kNm. Existing CalculiX validation is reusable; SCIA live validation remains pending.
2. `PHX-GOLDEN-CANTILEVER-002`: cantilever L=2 m with 1 kN end load, E=210 GPa, 0.1 x 0.1 m rectangular section. Analytical reaction, moment and tip deflection are known. A deterministic B31 CalculiX deck is prepared.
3. `PHX-GOLDEN-AXIAL-BAR-003`: L=2 m, P=100 kN, E=200 GPa, A=0.01 m2. Analytical stress is 10 MPa and elongation 0.1 mm. A deterministic T3D2 CalculiX deck is prepared.

The two new benchmarks deliberately do not receive invented numerical PASS tolerances. Such tolerances must be explicit and benchmark-specific before numerical validation.

No live SCIA or CalculiX is run during installation. Production and FOR-CONSTRUCTION remain LOCKED.
