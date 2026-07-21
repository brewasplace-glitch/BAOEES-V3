# Phoenix Autonomous Delivery Pipeline — Wave 3 v1.0

Wave 3 connects the previously separate Phoenix layers into one controlled
pipeline:

1. receive a project brief;
2. generate exactly ten PPG concept variants;
3. rank and present the variants;
4. select a variant automatically or by explicit variant ID;
5. create the PXO dependency plan;
6. execute registered runtime adapters;
7. persist integrity-protected checkpoints;
8. resume only after SHA-256 verification.

The pipeline produces a bootstrap manifest containing the ten-variant
presentation queue, selected variant, PXO plan and traceability fingerprints.

This wave does not provide real GIS, geotechnical, structural or permit
adapters. It provides the safe integration and resume framework into which
those adapters will be added.
