# PHOENIX 4.41 — Phase 6 Open-Source Engine Discovery / Onboarding Review — 2026-09-16

## pluggy — primary future live hook provider

Repository: https://github.com/pytest-dev/pluggy
License: MIT
The PluginManager supports plugin registration, hook specifications,
implementation validation and hook dispatch/introspection.

## stevedore — fallback entry-point provider

Repository: https://github.com/openstack/stevedore
License: Apache-2.0
The 2026.1 / 5.6.0 series adds explicit entry-point conflict resolution and
requires Python 3.10 or later. Stevedore provides extension and driver managers
around Python entry-point discovery.

## v1 decision

Phase 6 discovery itself stays dependency-light and non-executing:
machine-readable repository manifests plus `importlib.metadata` enumeration.
pluggy and stevedore remain optional future providers behind the Phoenix
onboarding contract.
