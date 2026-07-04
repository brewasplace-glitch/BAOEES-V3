@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.7
echo ============================================================
echo.

echo [1/12] Brewster kennis migreren...
python baoees\project_analyzer\brewster_knowledge_migration_engine.py
if errorlevel 1 goto error

echo [2/12] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [3/12] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [4/12] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [5/12] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [6/12] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [7/12] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [8/12] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo [9/12] Health check uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo [10/12] Error diagnostics uitvoeren...
python baoees\project_analyzer\project_error_diagnostics_engine.py
if errorlevel 1 goto error

echo [11/12] Auto repair uitvoeren...
python baoees\project_analyzer\project_auto_repair_engine.py
if errorlevel 1 goto error

echo [12/12] Health check na reparatie uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.7 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\projects\project_error_diagnostics_dashboard.html" (
    start "" "outputs\projects\project_error_diagnostics_dashboard.html"
)

if exist "outputs\projects\project_auto_repair_dashboard.html" (
    start "" "outputs\projects\project_auto_repair_dashboard.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.7 is gestopt.
echo Controleer de foutmelding hierboven.
echo.
git status
pause
exit /b 1
