# PHOENIX 4.41 — CORS open-source review

Before implementation, Flask-CORS and aiohttp-cors were reviewed as available
open-source CORS solutions.

Neither is adopted in this step because Phoenix already has a small loopback
`BaseHTTPRequestHandler` CAD sidecar. Moving to Flask or aiohttp solely for one
allowlisted browser-origin check would add a second web framework without adding
CAD capability.

The selected implementation keeps the current server and adds narrow,
allowlisted CORS response headers directly to it.
