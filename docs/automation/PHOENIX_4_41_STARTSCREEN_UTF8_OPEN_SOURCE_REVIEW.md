# PHOENIX 4.41 — UTF-8 / mojibake open-source review

## Primary — ftfy 6.3.1

- Purpose: repair mojibake and other Unicode text damage after the fact.
- Selected function: `fix_encoding`, specifically to avoid unrelated HTML-entity
  normalization.
- License: Apache-2.0.
- Role: primary source-level mojibake repair.

## Fallback / detector — charset-normalizer 3.5.1

- Purpose: detect/decode unknown text encodings.
- License: MIT.
- Role: decode fallback only when a source file is not valid UTF-8.

## Phoenix runtime fallback

The browser bridge also includes a small CP1252-to-UTF-8 repair path for
dynamically generated DOM text. This is not used as the authoritative source
repair; it only prevents runtime-generated labels from showing known mojibake.
