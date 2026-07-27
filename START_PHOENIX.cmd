@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_PHOENIX.ps1"
if errorlevel 1 pause
