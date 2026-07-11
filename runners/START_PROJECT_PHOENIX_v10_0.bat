@echo off
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File ".\runners\START_PROJECT_PHOENIX_v10_0.ps1" -Mode plan -Workflow platform_foundation
pause
