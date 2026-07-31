# EnergyPlus Silent License Acceptance Recovery v5.6.2

Uses Qt Installer Framework unattended CLI options:
`--accept-licenses --default-answer --accept-messages --confirm-command install`.

The installer has a 30-minute timeout, captures stdout/stderr, rejects any
remaining `Accept|Reject|Show` prompt, and requires a real design-day
simulation before repository mutation.
