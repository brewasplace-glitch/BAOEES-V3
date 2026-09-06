# PROJECT PHOENIX — R10.2 BUILD CONTRACT

**Title:** PHOENIX R10.2 — Architectural Quality Optimizer + Site/Climate/Façade Refinement + Camera/Composition Quality Gate
**Date:** 2026-09-06
**Project:** Plutostraat, Paramaribo, Suriname — Parcel 314 / MI-GLIS-ID BG-6316-5762
**Status Label:** PRELIMINARY / NOT FOR CONSTRUCTION

## 1. Baseline and authority
- R10 generated five unique, constraint-driven plan topologies and was accepted.
- R10.1 machine and evidence integrity gates passed.
- R10.1 visual/architectural quality gate did **not** pass.
- R10.2 is therefore the authorized next step.

## 2. Objective
Improve the five existing variants A–E without collapsing them into one generic solution, and produce architecturally stronger, climate-responsive, site-aware variants with reliable presentation renders.

## 3. Hard scope
R10.2 SHALL:
1. Preserve five distinct variants A–E as separate design identities.
2. Refine architecture, massing articulation, façades, entrance hierarchy and indoor-outdoor logic.
3. Strengthen response to tropical climate in Paramaribo: rain, solar control, shading, ventilation, covered transitions, privacy.
4. Improve parcel integration: access, arrival, veranda/patio/courtyard relations, open space, planting, boundary treatment.
5. Make non-orthogonal gestures architecturally legible where applicable.
6. Enforce camera/collision/composition quality gates before a render is accepted.
7. Generate machine-verifiable evidence and human-review outputs.

## 4. Out of scope
R10.2 SHALL NOT:
1. Unlock design selection.
2. Unlock structural analysis/solver.
3. Unlock permit workflow.
4. Unlock construction release.
5. Claim code compliance or professional approval.
6. Replace architectural judgment with a file-count-only PASS.

## 5. Hard locks to remain active
- DESIGN_SELECTION = LOCKED
- STRUCTURAL_SOLVER = LOCKED
- PERMIT = LOCKED
- CONSTRUCTION = LOCKED
- PROFESSIONAL_ARCHITECT_REVIEW = REQUIRED

## 6. Inputs
Mandatory inputs:
- The five approved R10 design JSONs / contracts.
- The R10.1 evidence basis and conversion outputs.
- Site identity: Plutostraat, Paramaribo, Suriname — parcel 314 / MI-GLIS-ID BG-6316-5762.
- Phoenix rules: open-source-first, stop on first gate failure, no false PASS.

## 7. Required outputs
Per variant A–E, R10.2 SHALL produce:
1. Refined design JSON / contract.
2. Evaluation JSON.
3. Ground-floor plan artifact.
4. Upper-floor plan artifact (if applicable).
5. 3D model artifacts suitable for downstream conversion.
6. IFC / FCStd / STEP / BLEND / GLB outputs, where pipeline supports them.
7. At least 5 validated presentation renders:
   - street_corner
   - rear
   - side
   - courtyard_or_patio
   - aerial
8. Variant summary sheet.
9. Gate result entry.
10. Traceable source/evidence manifest.

Project-level outputs:
- R10_2_RESULT.txt
- R10_2_QA_SUMMARY.json
- DE_TV-ready gallery/index artifact
- Aggregated review sheet comparing variants A–E
- Local evidence collector compatibility

## 8. Architectural refinement requirements
For all five variants:
1. Entrance hierarchy must become more legible.
2. Façades must show clearer hierarchy of solid/void/shade.
3. Openings must relate more plausibly to room use, privacy and orientation.
4. Roof edges, overhangs, pergolas and verandas must read as climate devices, not arbitrary slabs.
5. Outdoor living spaces must be readable and accessible.
6. Site edge, front approach, parking/arrival and garden logic must become visible.
7. Material logic at concept level must become more believable.
8. Each variant must retain its concept identity.

## 9. Camera / composition quality gate (mandatory)
A render SHALL FAIL if any of the following is true:
1. Camera is inside geometry or behind a solid face.
2. View is materially blocked by walls/screens/terrain/objects.
3. The intended façade or spatial idea is not visible.
4. Useful visible-building ratio is below threshold.
5. Useful context ratio is below threshold.
6. Image is over-zoomed so that the whole intended composition is unreadable.
7. Courtyard camera does not visibly communicate an actual courtyard/patio/veranda space.

Mandatory gate behavior:
- Detect failure automatically.
- Reposition and/or retarget camera automatically.
- Re-render until pass or max-attempt ceiling.
- Log all failed attempts in QA evidence.
- No silent fallback to a bad image.

## 10. Minimum QA metrics
Suggested default thresholds:
- visible_building_ratio >= 0.35
- useful_context_ratio >= 0.10
- occlusion_ratio <= 0.40
- camera_collision = false
- target_landmark_visible = true
- view_purpose_pass = true

## 11. Acceptance criteria
R10.2 is PASS only if all of the following are true:
1. Five refined variants A–E are produced.
2. Variant identities remain distinct.
3. Required artifacts exist and are traceable.
4. Camera/composition QA passes for all required views for all variants.
5. Visual outputs show measurable improvement over R10.1.
6. No hard lock is bypassed.
7. No false compliance or approval claim is made.
8. Final status explicitly remains PRELIMINARY / NOT FOR CONSTRUCTION.
