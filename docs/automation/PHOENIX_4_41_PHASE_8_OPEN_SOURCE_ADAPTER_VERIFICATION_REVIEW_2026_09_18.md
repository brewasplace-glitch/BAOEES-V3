# PROJECT PHOENIX 4.41 — PHASE 8 OPEN-SOURCE REVIEW

Review date: 2026-09-18

## RestrictedPython 8.5

Upstream describes RestrictedPython as a language-subset tool and explicitly
states that it is not a sandbox or secured environment. Version 8.5 is the
reviewed defense-in-depth candidate, but Phase 8 neither installs nor treats it
as an operating-system security boundary.

Source: https://pypi.org/project/RestrictedPython/

Decision: optional future defense-in-depth; not required or activated in v1.

## Microsoft eXecution Container (MXC)

MXC exposes cross-platform containment backends, including Windows backends,
but its upstream README identifies the repository as an early preview, notes
known overly permissive generated policies, and says no current profiles should
be treated as security boundaries.

Source: https://github.com/microsoft/mxc

Decision: disabled for candidate execution.

## Sandboxie Plus

Sandboxie Plus is an open-source Windows isolation project with filesystem,
registry, network and resource-control features. Phase 8 does not yet have a
package-bound provider with deterministic configuration validation and
independent attestation for it.

Source: https://github.com/sandboxie-plus/Sandboxie

Decision: reviewed but not integrated.

## gVisor

gVisor provides strong application isolation through a Linux-like userspace
kernel and OCI runtime. Its documented runtime requirements include Linux 5.6+
and therefore do not provide a Windows-native provider for this PHOENIX host.

Source: https://github.com/google/gvisor

Decision: not available as the active Windows-native provider.

## Phase-8 result

No candidate satisfies the required Windows-compatible, fail-closed,
security-boundary standard for this release. Phase 8 activates deterministic
synthesis, static contract validation, exact replay, signed attestations and
explicit SHA-bound review handoff only. Candidate execution, repository write
and automatic activation remain disabled.
