# Phoenix Construction Coordination, Clash Detection, QA/QC and Field Release Engine v7.1.0

v7.1.0 adds the controlled transition from construction release to field release.

Core capabilities:
- discipline model register;
- clash register with severity and status;
- release-blocking issue tracking;
- QA/QC register;
- work package control;
- field inspection register;
- field release matrix;
- Digital Twin field-release writeback;
- SHA-256 artifact manifest.

Automatic field release is disabled. Field-ready unlock requires the upstream
execution-release gate, no open critical clashes, all mandatory QA/QC and field
inspection items passing with evidence, all release-blocking issues closed,
current approved work packages, coordinated current discipline models and
professional site release.
