@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - TASK AUTOPILOT v8.0

python apps\brewster_engineering_wizard\project_analyzer\phoenix_task_autopilot_engine.py || goto error

if exist "outputs\projects\phoenix_task_autopilot_dashboard_v8_0.html" (
    start "" "outputs\projects\phoenix_task_autopilot_dashboard_v8_0.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Task Autopilot Engine v8.0 is gestopt.
git status
pause
exit /b 1
