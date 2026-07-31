# Phoenix Professional Evidence Intake and Review Workflow v6.4.0

## Purpose

v6.4.0 turns the evidence contracts from v6.3.1 into an operational intake and
review workflow.

## Per-requirement structure

Each requirement receives four controlled folders:

- `sources`;
- `metadata`;
- `review`;
- `review_packets`.

Every accepted source must be non-empty, use an allowed file type, have a
SHA-256 hash and have a matching metadata record containing source title,
date, version, origin, discipline and file name.

## Review workflow

A requirement cannot progress to review without a valid reviewer assignment.
A professional review record must identify the reviewer, role and organization
and contain an explicit APPROVED, REJECTED or REVISION_REQUIRED decision.

Phoenix never creates professional approval automatically.

## REQ-108

REQ-108 may only close after REQ-102 through REQ-106 have been approved.
The permit-ready gate stays locked until all six requirements close.
