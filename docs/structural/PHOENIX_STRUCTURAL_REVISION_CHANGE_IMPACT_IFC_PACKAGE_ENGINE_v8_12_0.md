# PROJECT PHOENIX — Structural Revision, Change Impact & IFC Package Engine v8.12.0

## Function
v8.12.0 manages the structural engineering lifecycle after v8.11.0 release.

It installs:
- immutable released-baseline control;
- DRAFT / FOR_REVIEW / APPROVED / IFC / SUPERSEDED / AS_BUILT revision states;
- SHA256 component change detection;
- transitive affected-item graph;
- re-analysis and re-verification requirement generation;
- mandatory fresh v8.10 QA/QC after engineering change;
- mandatory fresh v8.11 human review/release after engineering change;
- superseded-document control;
- IFC transmittal/package index;
- immutable IFC manifest fingerprint;
- Digital Twin revision/IFC writeback.

## IFC rule
A revision can be issued as IFC only when the exact current revision fingerprint
has a v8.11.0 release record with `construction_release = RELEASED` and all
required IFC documents are approved/IFC.

An earlier release never transfers automatically to changed engineering.

## Safety defaults
- automatic professional engineering approval: DISABLED
- automatic human review fabrication: DISABLED
- automatic IFC without v8.11 authorization: DISABLED
- changed revision automatic IFC promotion: DISABLED
