# Phoenix GIS Bootstrap Adapter — Wave 4 v1.0

Wave 4 adds the first file-producing discipline adapter to the autonomous
delivery pipeline.

The adapter accepts a project ID, location reference, optional user-supplied
geometry, coordinate reference system, sources and assumptions. It writes an
atomic, SHA-256-protected site-context artifact and returns that artifact to the
PXO runtime as output and evidence.

The adapter deliberately does not invent:

- coordinates;
- parcel boundaries;
- zoning rules;
- environmental constraints;
- utilities;
- access conditions;
- elevation or terrain data.

Without supplied geometry, the artifact is marked `reference_only`. With
supplied geometry and a coordinate reference system, it is marked
`supplied_geometry`. In both cases the output remains a bootstrap record rather
than an authoritative GIS analysis.

Later waves can enrich this artifact using verified external data connectors.
