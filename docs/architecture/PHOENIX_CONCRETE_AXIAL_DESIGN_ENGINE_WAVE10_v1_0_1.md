# Phoenix Concrete Axial Design Engine â€” Wave 10 v1.0.1

Wave 10 consumes verified Wave 9 axial-force results and performs a
transparent reinforced-concrete axial sizing check.

The engine supports:

- tension, compression and near-zero axial actions;
- user-controlled concrete and reinforcement strengths;
- user-controlled resistance and action factors;
- minimum and maximum reinforcement ratios;
- bar diameter and minimum bar count;
- required and provided reinforcement area;
- axial capacity and utilization;
- explicit pass/fail evidence.

This version is intentionally generic and policy-based. It does not claim
compliance with a named design standard.

It does not verify bending, shear, slenderness, buckling, second-order
effects, crack control, detailing, durability, anchorage, fire resistance
or constructability. Those capabilities require separate verified engines
and competent structural-engineer review.

## v1.0.1 corrective patch

The integration fixture now uses the Wave 7-supported `dead` load type instead of the unsupported `design` value. The installer also recognizes and safely removes only the exact partial Wave 10 v1.0 footprint left by the failed run before beginning a clean installation.
