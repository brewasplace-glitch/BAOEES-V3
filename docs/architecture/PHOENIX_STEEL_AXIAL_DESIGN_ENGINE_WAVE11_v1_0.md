# Phoenix Steel Axial Design Engine â€” Wave 11 v1.0

Wave 11 consumes verified Wave 9 axial-force results and performs a transparent
structural-steel axial resistance check.

The engine reports:

- tension, compression and near-zero action modes;
- gross-section yield resistance;
- gross-section ultimate resistance;
- governing axial resistance;
- utilization;
- optional geometric slenderness screening;
- explicit pass/fail evidence.

The implementation is generic and policy-based. It does not claim compliance
with a named design standard.

The optional slenderness calculation is only a screening check. It is not a
buckling resistance model. Local buckling, global buckling, lateral-torsional
buckling, connection design, fatigue, fire resistance and fracture are outside
the verified scope and require separate engines and competent engineer review.
