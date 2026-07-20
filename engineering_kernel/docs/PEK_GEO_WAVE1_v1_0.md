# PEK-07 Geo Engine — Wave 1 v1.0

This release adds the first geotechnical domain extension to the Phoenix
Engineering Kernel.

It contains 30 generic SI-based functions for:

- soil layers and profile continuity;
- dry, saturated and submerged unit weights;
- pore pressure and total/effective vertical stress;
- effective stress profiles with groundwater;
- Rankine active, passive and at-rest coefficients;
- lateral pressure and triangular resultants;
- strip-footing bearing-capacity factors and capacity;
- allowable bearing pressure;
- one-dimensional and elastic settlement;
- consolidation degree approximation;
- hydraulic gradient, Darcy velocity and seepage discharge;
- critical hydraulic gradient;
- liquefaction safety ratio;
- slope ratios and angles;
- groundwater elevation.

The fixed 750-function core registry is deliberately not altered. GEO is
registered as a domain extension under `specification/domains`.
