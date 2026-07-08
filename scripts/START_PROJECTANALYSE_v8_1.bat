@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - RUNNER VALIDATION v8.1

python apps\brewster_engineering_wizard\project_analyzer\runner_validation.py || goto error

if exist "outputs\projects\runner_validation_dashboard_v8_1.html" (
    start "" "outputs\projects\runner_validation_dashboard_v8_1.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Runner Validation Engine v8.1 is gestopt.
git status
pause
exit /b 1
