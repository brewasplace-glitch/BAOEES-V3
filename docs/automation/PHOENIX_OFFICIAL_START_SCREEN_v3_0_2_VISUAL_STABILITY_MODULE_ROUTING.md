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


## R1 visual stability / fit-to-screen correction
Practical browser validation showed two UI issues:
1. the page used a fixed viewport layout that prevented normal vertical scrolling;
2. periodic DOM rebuilds were still capable of producing visible redraw/flicker.

R1 changes:
- normal vertical page scrolling;
- smaller desktop spacing and card heights;
- sticky, independently scrollable left navigation on desktop;
- no periodic heavy project/workflow/module DOM rebuild;
- summary/status text is only mutated when values change;
- progress UI is only mutated when progress actually changes;
- heavy lists refresh after real actions instead of on a fixed timer.


## R3 zero-idle-polling correction
Practical validation showed that the browser still exhibited visible flicker after
periodic heavy redraws were removed. R3 therefore removes all periodic idle
polling from the start screen.

Behavior:
- no setInterval loops while Phoenix is idle;
- one initial status read at startup;
- a manual STATUS refresh button is available;
- only an actually running workflow is polled, by job id, every 2.5 seconds;
- only the progress strip changes during workflow execution;
- project/workflow/module lists are refreshed once after a real workflow state transition.

This eliminates background UI mutation while the user is reading or configuring a project.


## R4 test-contract correction
R3's runtime implementation correctly removed all idle `setInterval(...)` polling,
but one older R1 static test still required `setInterval(refreshProgress, ...)`.
That legacy assertion contradicted the new R3 zero-idle-polling design and caused
the installer to fail even though the runtime code matched the intended behavior.

R4 changes only the test contract:
- removes the obsolete requirement for periodic progress polling;
- asserts that no idle `setInterval(...)` loop remains;
- preserves the R3 active-job-only `setTimeout(...)` monitor.
