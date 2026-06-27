@echo off
setlocal

title PROJECT PHOENIX - START PROJECTANALYSE v5.0

echo.
echo ============================================================
echo  PROJECT PHOENIX / BAOEES
echo  START PROJECTANALYSE v5.0
echo ============================================================
echo.

cd /d "%~dp0"

if not exist "%~dp0START_PROJECTANALYSE.ps1" (
    echo FOUT: START_PROJECTANALYSE.ps1 niet gevonden.
    echo Verwacht pad:
    echo %~dp0START_PROJECTANALYSE.ps1
    echo.
    pause
    exit /b 1
)

echo PowerShell startscript wordt uitgevoerd...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_PROJECTANALYSE.ps1"

set EXITCODE=%ERRORLEVEL%

echo.
echo ============================================================
echo  START PROJECTANALYSE BAT AFRONDING
echo ============================================================
echo.

if not "%EXITCODE%"=="0" (
    echo START PROJECTANALYSE is gestopt met foutcode: %EXITCODE%
    echo.
    pause
    exit /b %EXITCODE%
)

echo START PROJECTANALYSE succesvol afgerond.
echo.
exit /b 0