@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - BUILD GOVERNANCE v7.6

python apps\brewster_engineering_wizard\project_analyzer\phoenix_build_governance_engine.py || goto error

if exist "outputs\projects\phoenix_daily_start_dashboard_v7_6.html" (
    start "" "outputs\projects\phoenix_daily_start_dashboard_v7_6.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Build Governance Engine v7.6 is gestopt.
git status
pause
exit /b 1
