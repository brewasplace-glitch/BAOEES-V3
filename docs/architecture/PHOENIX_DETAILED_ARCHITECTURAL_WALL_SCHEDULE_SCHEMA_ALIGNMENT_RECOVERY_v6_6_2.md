# Phoenix Detailed Architectural Wall Schedule Schema Alignment Recovery v6.6.2

The wall model stores nested start/end coordinates. v6.6.1 passed the raw wall
dictionaries directly to a CSV schema that did not include those fields.

v6.6.2 projects each wall to explicit scalar columns:

- start_x_m;
- start_y_m;
- end_x_m;
- end_y_m;
- length_m;
- height_m;
- thickness_m;
- host_space_ids.

Host-space IDs are sorted and joined with `|`. Strict CSV schema validation
remains active with `extrasaction="raise"`.

The PowerShell error handler is restored to `throw "Python failed:
$LASTEXITCODE"`.
