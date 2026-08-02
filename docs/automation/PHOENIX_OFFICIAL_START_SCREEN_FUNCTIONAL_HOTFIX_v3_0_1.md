# PROJECT PHOENIX — Official Start Screen Functional Hotfix v3.0.1

## Problem fixed
The prior official screen was visually based on a background image and only a
small number of transparent hotspots had handlers.

v3.0.1 converts the official start screen into a same-origin local-runtime
application. Visible controls are real HTML controls connected to Phoenix APIs.

## Functional controls
- BOUW / CIVIEL / INFRA project-type selection
- real file upload into `inputs/runtime/official_start_v3_uploads`
- browser speech recognition into the project brief
- START PROJECTANALYSE creates a persisted intake session and lists actual
  registered Phoenix workflows
- PROJECTEN
- DIGITAL TWIN
- BOUWKUNDIG
- CONSTRUCTIEF
- CIVIEL
- INFRA
- VERGUNNINGEN
- KOSTEN & PLANNING
- QA/QC
- RELEASE CONTROL
- BIB / KNOWLEDGE
- SYSTEM STATUS
- registered workflow START buttons
- project selection

## Architecture
The official launcher starts/reuses a dedicated local Phoenix runtime and opens
`/start-v3/`. The start page and API therefore share the same origin. POST
actions use the existing local session-token security model.

Existing runtime routes remain available:
- `/`
- `/api/health`
- `/api/status`
- `/api/jobs/<id>`
- `/api/workflows/<id>/run`
- `/api/open`
- `/api/shutdown`

New v3.0.1 routes:
- `/start-v3/`
- `/start-v3/<asset>`
- `/api/uploads`
- `/api/modules/<id>/open`
- `/api/project-analysis/start`
