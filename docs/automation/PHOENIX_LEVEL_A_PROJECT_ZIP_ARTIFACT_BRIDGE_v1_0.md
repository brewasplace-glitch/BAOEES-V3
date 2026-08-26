# Project Phoenix Level-A Project ZIP Artifact Bridge v1.0

## Proven root cause

Moskee Bunschoten R6 runtime forensics proved that `project_zip` was blocked because no
non-empty ZIP existed in the project workspace. The desired-output resolver already
recognizes any non-empty project-workspace ZIP, so the missing component was the
producer, not the resolver.

## Reuse-first implementation

Phoenix already contains multiple deterministic ZIP exporters and uses Python's standard
`zipfile` module. This bridge reuses that established package pattern and adds no new
dependency or parallel export engine.

## Runtime behavior

The closure adapter writes `qaqc_release_gate.json` first, then emits:

- `project_level_a_candidate_package.zip`
- `project_level_a_candidate_package_manifest.json`

The ZIP contains current project-workspace evidence plus an internal
`PROJECT_ZIP_MANIFEST.json`.

Existing ZIP files are excluded to prevent recursive package nesting.

## Safety

The artifact is explicitly a `LEVEL_A_CANDIDATE_PROJECT_EVIDENCE` package. It may be
created even when QA/QC is blocked because packaging is independent from professional
approval.

It always carries:

- `formal_release=false`
- `professional_review_required=true`
- `automatic_professional_approval=false`
- `production_release=LOCKED`
- `for_construction=LOCKED`

This change does not repair or bypass structural source evidence, material supply,
technical product evidence, QA/QC approval, or formal release gates.
