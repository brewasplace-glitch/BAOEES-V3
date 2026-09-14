# PHOENIX 4.41 UTF-8 + Runtime Label FIX R9

Baseline: `781be57f7d148e700172e8c9dd4a8b2a24136343`.

R8 reduced the visible UTF-8 regression to one exact residual sequence:

`U+00F0 U+00C5 U+00B8 U+008F U+00A2`

This is a nested Windows-1252/UTF-8 corruption. Collapsing the nested encoding
recovers UTF-8 bytes `F0 9F 8F A2`, which is Unicode `U+1F3E2` (office building).

R9 therefore performs one exact pre-normalization:
`U+00F0 U+00C5 U+00B8 U+008F U+00A2` -> `&#x1F3E2;`

No broader cross-tag regex is introduced. The R7 tag-bounded navicon repair,
exact phoenixTvPrev repair, ASCII-safe console JSON, bounded START v4.41 guard,
and protected CAD/observer bridge remain unchanged.
