# PEK-08 Structural Engine — Wave 1 v1.0

The first Structural Engine wave adds 30 generic structural-mechanics
functions in SI units.

Implemented areas:

- rectangular and circular section properties;
- parallel-axis theorem;
- axial, bending, combined and average shear stress;
- strain and axial deformation;
- simply supported beam reactions, moments and deflections;
- cantilever deflection and rotation;
- effective length, slenderness and Euler buckling;
- second-order moment amplification;
- utilization and factor of safety;
- 2D force resultants;
- local/global 2D vector transformations.

The module deliberately avoids hard-coded national-code factors. Those belong
in later steel, concrete, timber and masonry code layers.
