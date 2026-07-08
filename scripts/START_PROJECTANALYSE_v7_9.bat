@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - TASK STATUS / ROADMAP UPDATE v7.9

python apps\brewster_engineering_wizard\project_analyzer\phoenix_task_status_roadmap_update_engine.py || goto error

if exist "outputs\projects\phoenix_roadmap_status_dashboard_v7_9.html" (
    start "" "outputs\projects\phoenix_roadmap_status_dashboard_v7_9.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Task Status Roadmap Update Engine v7.9 is gestopt.
git status
pause
exit /b 1
