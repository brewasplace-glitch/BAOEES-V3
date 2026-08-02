# PROJECT PHOENIX — Official Start Screen v3.0.2

## What this hotfix changes
This update builds on v3.0.1 and addresses the observed usability gaps:

- restores a richer visual Phoenix UI
- removes the heavy full-screen redraw refresh pattern that caused flicker
- adds a dedicated RESULTATEN button and results panel
- adds a visible progress bar and status strip
- adds a GEWENSTE OUTPUT selector with real checkbox groups
- routes left navigation and Phoenix modules through integrated routing logic
- opens runtime screens when appropriate
- otherwise opens the best available repository-backed Phoenix target
- preserves the proven project-analysis and workflow-launch chain

## Key runtime behavior
Polling now follows three tiers:
- `/api/summary` every 3 seconds
- `/api/progress` every 2 seconds
- `/api/status` every 30 seconds

This sharply reduces unnecessary DOM rebuilds.

## Main interaction zones
1. Project type selection
2. Upload / intake
3. Speech input
4. Project mode
5. Desired output
6. Start Projectanalyse
7. Resultaten
8. Phoenix modules
9. Workflow list
10. Project list

## Module routing
Modules now expose view metadata and richer routing logic. Screen-like modules
can stay inside the Phoenix runtime; other modules open the best available real
file or folder target. Placeholder empty-folder behavior is no longer the main
user path.
