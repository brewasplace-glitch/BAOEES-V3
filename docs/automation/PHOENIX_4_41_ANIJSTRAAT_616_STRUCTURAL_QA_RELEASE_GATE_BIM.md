# PHOENIX 4.41 — Anijstraat #616 Structural QA Release Gate + BIM Integration

Expected source SHA256: `1a39f7a94e8f32c755ed7300a63c8a76c6be5902932b8ca34036343ccebf33d0`.

This stage audits the complete preliminary structural evidence chain and creates a standards-based BIM handoff.

## QA behavior

A successful execution means the **QA process itself** passed. It does **not** mean construction release is allowed.

Expected decision with current evidence:

`QA_GATE_EXECUTION = PASS`

`RELEASE_DECISION = HOLD`

`FOR_CONSTRUCTION_RELEASE = LOCKED`

## BIM output

Primary open-source BIM engine: IfcOpenShell 0.8.5.

- IFC4 structural QA handoff;
- read-back validation with IfcOpenShell;
- Phoenix QA metadata on every structural proxy;
- IDS requirements + IfcTester 0.8.5 validation;
- Digital Twin structural handoff JSON;
- QA dashboard and release-hold matrix.

The prior GLB/OBJ/STL remains the visual 3D coordination evidence. The IFC file is intentionally a preliminary QA/BIM metadata handoff and does not pretend unproven geometry is final.


## FIX R1 — Cross-stage runtime bridge

The first Windows run installed IfcOpenShell and IfcTester successfully and verified the design and solver evidence.
The run then stopped while verifying the previous 3D/report stage because that verifier imports `trimesh`, `python-docx`, and `pypdf`, while the QA/BIM runner exposed only its own isolated BIM runtime.

FIX R1 creates an isolated compatibility runtime with `trimesh==5.1.0`, `python-docx==1.2.0`, and `pypdf==5.9.0`, adds it to the cross-stage `PYTHONPATH`, and probes all required imports before evidence verification.

This is a runtime-wiring repair only. Structural results and the release decision are unchanged.


## FIX R2 — IfcTester JSON reporter serialization

The Windows FIX R1 run passed:
- cross-stage Python imports;
- design evidence verification;
- solver evidence verification;
- 3D/report evidence verification;
- IFC creation and IDS validation up to report generation.

The run failed only while Phoenix attempted to serialize `reporter.Json(...).report()` with Python `json.dumps`.
IfcTester result structures may contain `ifcopenshell.entity_instance` values, which are intentionally handled by IfcTester's reporter encoder.

FIX R2 uses the official IfcTester sequence:

1. `report = reporter.Json(spec_file)`
2. `report.report()`
3. `report.to_file(report_path)`
4. Phoenix re-opens the written JSON and requires `status == true`.

No structural calculation, IFC requirement, IDS rule, or release decision is changed.
