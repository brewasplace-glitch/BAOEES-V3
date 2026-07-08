@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - RUNNER REPAIR ADVISOR v8.2

python apps\brewster_engineering_wizard\project_analyzer\runner_repair_advisor.py || goto error

if exist "outputs\projects\runner_repair_advisor_dashboard_v8_2.html" (
    start "" "outputs\projects\runner_repair_advisor_dashboard_v8_2.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Runner Repair Advisor Engine v8.2 is gestopt.
git status
pause
exit /b 1
