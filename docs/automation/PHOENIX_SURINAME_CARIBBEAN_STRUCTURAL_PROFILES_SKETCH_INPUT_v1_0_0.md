# Project Phoenix Suriname and Caribbean structural profiles with sketch input recognition v1.0.0

## Scope

This module adds seven controlled jurisdiction profiles: Suriname, Bonaire, Sint Eustatius, Saba, Aruba, Curaçao and Sint Maarten. Profiles record official legal/permit context and mandatory confirmation gates. They intentionally do not claim that a single design standard is automatically accepted in every jurisdiction.

## Sketch workflow

1. Upload PNG, JPG, JPEG, BMP, TIFF or PDF.
2. Acquire text from explicit transcription, sidecar text, Tesseract, Windows OCR or a PDF text layer.
3. Recognize span, section, concrete/steel class, cover, distributed loads, point loads, positions and support text.
4. Show candidate values and confidence evidence.
5. Require explicit user confirmation/correction.
6. Require selected-jurisdiction engineer-basis confirmation.
7. Generate normalized input for the reinforced-concrete beam engine.
8. Run preliminary calculation and keep final release blocked.

## Safety gates

- No silent calculation from unconfirmed OCR.
- No point load without a confirmed position.
- No final structural release without local engineer approval.
- No profile is presented as a legal opinion.


## v1.0.1 cross-platform recovery
- All deterministic JSON, Markdown, SVG, HTML and checksum text output uses explicit LF line endings.
- Installation establishes the canonical artifact baseline on the target platform.
- A second independent regeneration must byte-match that local baseline before Git staging.
