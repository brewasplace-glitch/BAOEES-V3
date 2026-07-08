@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - AUTOMATED TASK BUILDER v7.8

python apps\brewster_engineering_wizard\project_analyzer\phoenix_automated_task_builder_engine.py || goto error

if exist "outputs\projects\phoenix_automated_task_builder_dashboard_v7_8.html" (
    start "" "outputs\projects\phoenix_automated_task_builder_dashboard_v7_8.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Automated Task Builder Engine v7.8 is gestopt.
git status
pause
exit /b 1
