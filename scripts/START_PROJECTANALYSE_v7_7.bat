@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - TASK EXECUTOR v7.7

python apps\brewster_engineering_wizard\project_analyzer\phoenix_task_executor_engine.py || goto error

if exist "outputs\projects\phoenix_task_executor_dashboard_v7_7.html" (
    start "" "outputs\projects\phoenix_task_executor_dashboard_v7_7.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Task Executor Engine v7.7 is gestopt.
git status
pause
exit /b 1
