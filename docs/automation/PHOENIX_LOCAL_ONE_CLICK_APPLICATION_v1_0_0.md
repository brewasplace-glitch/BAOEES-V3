# Project Phoenix Local One-Click Application v1.0.0

## Purpose

Run Project Phoenix locally without ChatGPT through one desktop action.

## Dashboard reuse

At startup Phoenix scans the repository for the strongest existing HTML start dashboard. Candidate scoring uses Phoenix-specific filenames and content markers such as `START PROJECTANALYSE`, `Autonomous Project Mode`, `Bouw`, `Civiel` and `Infra`.

The selected dashboard is not overwritten. A local runtime panel is injected in memory when the page is served. If no suitable dashboard exists, Phoenix serves the bundled fallback dashboard.

## Start and stop

- `START_PHOENIX.cmd` starts the application in the background and opens the browser.
- `START_PHOENIX.ps1` provides PowerShell parameters.
- `STOP_PHOENIX.ps1` performs a token-protected local shutdown.

## Security boundary

- bind address is fixed to `127.0.0.1`;
- POST requests require a per-session token;
- only allow-listed Phoenix runners can execute;
- subprocess execution uses `shell=False`;
- no arbitrary command input is accepted;
- only repository-contained open targets are allowed.

## Current workflow availability

The BB35 simulation, integrated dossier and project-leader review are connected. The real drawings and reports workflow is shown but remains disabled until its production engine is installed.


## Production engine integration v1.1.0

The real concept drawings and reports workflow is enabled and the generated issue index and complete drawing set can be opened directly from the local dashboard.


## Central model integration v1.2.0

The dashboard can build and open the central geometric project model. The real drawings and reports workflow now derives its geometry and parking capacity from the canonical model fingerprint.
