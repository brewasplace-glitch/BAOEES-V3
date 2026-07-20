# PEK Geometry Wave 1 v1.0

Implements PEK-GEOM-0001 through PEK-GEOM-0025.

Capabilities:

- immutable 2D and 3D points;
- distances and midpoints;
- 2D and 3D vectors;
- dot and cross products;
- vector lengths and normalization;
- angles between 2D vectors;
- polygon area, signed area, perimeter and centroid;
- 2D bounding boxes;
- translation and rotation;
- infinite-line intersection.

Geometry is unit-agnostic. Every operation requires coordinates expressed in one
consistent linear unit. Unit conversion belongs to the PEK Units Engine.
