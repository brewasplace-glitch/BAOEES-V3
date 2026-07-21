# Phoenix Geotechnical Bootstrap Adapter — Wave 5 v1.0

Wave 5 adds the second real discipline adapter to the Phoenix autonomous
delivery chain.

The adapter consumes and verifies the SHA-256 integrity of the GIS site-context
artifact. It then creates a geotechnical site model using only explicitly
supplied soil layers, groundwater information, investigation references and
identified assumptions.

The project-wide groundwater assumption of P = -0.50 m is supported, but it is
disabled by default and can only be used when the caller explicitly enables
`allow_assumed_groundwater`. The resulting artifact marks it as an assumption
that must be replaced by project-specific evidence.

The adapter does not calculate or invent:

- bearing resistance;
- settlement;
- soil parameters;
- design groundwater;
- foundation dimensions;
- foundation suitability.

Those tasks belong to later verified geotechnical and foundation design waves.
