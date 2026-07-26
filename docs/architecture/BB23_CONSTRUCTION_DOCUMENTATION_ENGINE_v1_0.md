# BB23 - Construction Documentation Engine v1.0.0

## Position

BB16 Building Model -> BB18.1 Architectural Drawings -> BB19 Structural Design
-> BB20 Quantity Take-Off -> BB21 Cost Estimation -> BB22 BIM Coordination
-> BB23 Construction Documentation.

## Purpose

BB23 turns Phoenix model, design, quantity, cost and coordination evidence into
one controlled multidisciplinary publication package.

## Assembly

The engine creates ten report sections:

1. project overview;
2. document control and source register;
3. building model summary;
4. drawing register;
5. structural design summary;
6. quantity take-off summary;
7. cost estimate summary;
8. BIM coordination status;
9. documentation issues and limitations;
10. source evidence fingerprints.

## Document control

Every package receives:

- deterministic package ID;
- Phoenix revision in `A00` format, such as `P01` or `C02`;
- project stage and release status;
- eight controlled output records;
- SHA-256 source fingerprints;
- explicit blocking issues;
- deterministic package fingerprint.

## Release gate

A package is blocked when:

- a required BB16, BB18.1, BB19, BB20, BB21 or BB22 source is absent;
- a source belongs to a different project;
- BB22 has not passed;
- BB22 contains an open `error` or `critical` issue.

A release request only produces `released` status after all blocking gates pass.

## Publications

BB23 v1.0.0 generates:

- JSON package manifest;
- CSV document register;
- Markdown technical report;
- HTML technical report;
- dependency-free DOCX technical report;
- dependency-free PDF technical report;
- SHA-256 publication checksum register;
- complete construction-documentation dossier ZIP.

## Safety boundary

The publication is non-certifying. It does not replace professional review,
discipline approval, statutory submission checks or signed engineering
documentation.

## Quality gates

1. Python compilation.
2. Seventeen BB23 unit tests.
3. BB23 self-test.
4. JSON, CSV, Markdown, HTML, DOCX, PDF and dossier ZIP validation.
5. DOCX render validation.
6. PDF render validation.
7. Git whitespace validation.
8. Exact payload staging.
9. Automatic commit and push after all gates pass.
10. Transactional rollback before push and no history rewrite after push.
