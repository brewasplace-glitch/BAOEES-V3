# PHOENIX 4.41 — Phase 5 Open-Source Executor Adapter Registry Review — 2026-09-16

## pluggy — primary future provider

Repository: https://github.com/pytest-dev/pluggy
License: MIT
Role: future external adapter hook/registration provider.
Fit: PluginManager registry, hook specifications, validated hook
implementations, and controlled hook dispatch.

## stevedore — fallback provider

Repository: https://github.com/openstack/stevedore
License: Apache-2.0
Role: future entry-point based adapter/driver discovery.
Fit: dynamic plugin discovery through entry points, driver managers, extension
managers and named dispatch.

## Phase 5 v1 decision

Use a deterministic Phoenix-owned machine-readable adapter registry as the
authority-bearing v1 backend. Keep pluggy and stevedore as optional future
discovery providers behind the Phoenix adapter contract; neither becomes a hard
runtime dependency.
