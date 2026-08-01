# Project Phoenix Structural Foundation Design, Reinforcement & Detailing Engine v8.9.0

## Purpose
v8.9.0 consumes the verified foundation-interface / soil-support candidate from v8.8.0 and creates an auditable reinforced-foundation **design and detailing candidate**. It supports pad foundations, strip foundations, foundation beams and pile caps.

This layer is intentionally separated from statutory approval and construction release. It verifies explicit design evidence and produces model/schedule/detail data; it does not invent normative values.

## Core contracts
- Explicit foundation design basis with jurisdiction, standard set, edition, source reference and status.
- Explicit concrete and reinforcement material records with traceable strengths and sources.
- Foundation geometry contracts for pad, strip, foundation-beam and pile-cap candidates.
- Flexural, one-way shear, punching-shear and pile-cap strut-and-tie capacity checks from explicit demand/capacity evidence.
- Explicit reinforcement groups with bar marks, role, material, count, diameter, length, cover, spacing and shape-code data.
- Derived reinforcement area, total bar length and estimated reinforcement mass from explicit bar geometry and explicit material density.
- Reinforcement schedule generation and foundation quantity takeoff.
- Evidence contracts for minimum/maximum reinforcement, concrete cover, bar spacing, anchorage/development, dowels/starter bars, materials and drawing completeness.
- Foundation utilization envelopes and review-item generation for failed or incomplete mandatory checks.
- Central Digital Twin writeback for geometry, reinforcement, schedules, checks, quantities, drawing data, traceability and review items.

## Normative safety policy
Phoenix does **not** generate unreferenced values for:
- minimum or maximum reinforcement;
- concrete cover or bar spacing limits;
- anchorage/development lengths;
- flexural, shear or punching resistance;
- pile-cap strut-and-tie resistance;
- material design strengths;
- safety factors or code limits.

Those values must come from explicit project input, a verified calculation/standards engine, or competent engineering input with a traceable normative reference.

A `FOUNDATION_DESIGN_REINFORCEMENT_DETAILING_CANDIDATE_PASSED` state means only that the supplied explicit verification evidence passed the configured candidate checks and that required reinforcement/detail records are present. It does **not** mean code compliance, geotechnical approval, structural approval, foundation approval, detailing approval or construction release.

## Outputs
- Foundation geometry and concrete volumes.
- Reinforcement groups and reinforcement schedule.
- Estimated reinforcement mass from explicit density.
- Verification results and utilization envelopes.
- Drawing/detail data contract.
- Quantity takeoff.
- Normative/material traceability.
- Digital Twin writeback candidate.
- Review items for failed/incomplete evidence.

## Next release gate
Construction and structural model release remain locked pending integrated structural documentation, drawing QA/QC, calculation-package completeness, competent engineering review and explicit release authorization.
