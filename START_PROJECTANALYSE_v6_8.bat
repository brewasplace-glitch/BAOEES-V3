@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.8
echo ============================================================
echo.

echo [1/13] Brewster kennis migreren...
python baoees\project_analyzer\brewster_knowledge_migration_engine.py
if errorlevel 1 goto error

echo [2/13] Deep Knowledge Harvest uitvoeren...
python baoees\project_analyzer\deep_knowledge_harvest_engine.py
if errorlevel 1 goto error

echo [3/13] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [4/13] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [5/13] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [6/13] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [7/13] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [8/13] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [9/13] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo [10/13] Health check uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo [11/13] Error diagnostics uitvoeren...
python baoees\project_analyzer\project_error_diagnostics_engine.py
if errorlevel 1 goto error

echo [12/13] Auto repair uitvoeren...
python baoees\project_analyzer\project_auto_repair_engine.py
if errorlevel 1 goto error

echo [13/13] Health check na reparatie uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.8 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\bib\dashboards\deep_knowledge_harvest_dashboard_v6_8.html" (
    start "" "outputs\bib\dashboards\deep_knowledge_harvest_dashboard_v6_8.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.8 is gestopt.
echo Controleer de foutmelding hierboven.
echo.
git status
pause
exit /b 1
