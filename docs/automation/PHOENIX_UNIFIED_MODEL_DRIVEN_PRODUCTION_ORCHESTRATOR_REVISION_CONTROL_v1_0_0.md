# Project Phoenix Unified Model-Driven Production Orchestrator v1.0.0

This module coordinates the central geometric model, model-driven drawings and
reports, and the model-driven calculation workbook.

It provides source fingerprinting, dependency-based invalidation, selective
regeneration, fail-fast cross-discipline validation, revision numbering,
release manifests, checksums and a single complete concept issue package.

A central-model change invalidates both downstream product groups. A
production-only or calculation-only source change invalidates only the affected
discipline product and the unified release. A release is published only when
all 22 cross-discipline checks pass.
