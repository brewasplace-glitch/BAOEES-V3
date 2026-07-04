@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.6
echo ============================================================
echo.

echo [1/9] Brewster kennis migreren...
python baoees\project_analyzer\brewster_knowledge_migration_engine.py
if errorlevel 1 goto error

echo [2/9] Startanalyse uitvoeren...
python baoees\project_analyzer\project_start_analysis_engine.py
if errorlevel 1 goto error

echo [3/9] Workflow uitvoeren...
python baoees\project_analyzer\project_analyzer_workflow_engine.py
if errorlevel 1 goto error

echo [4/9] AAIE/BIB aannames uitvoeren...
python baoees\project_analyzer\aaie_bib_assumption_loader.py
if errorlevel 1 goto error

echo [5/9] Projectrapportagepackage uitvoeren...
python baoees\project_analyzer\project_report_bib_engine.py
if errorlevel 1 goto error

echo [6/9] DOCX/PDF export uitvoeren...
python baoees\project_analyzer\project_report_export_engine.py
if errorlevel 1 goto error

echo [7/9] Evidence en projectpakket uitvoeren...
python baoees\project_analyzer\project_package_evidence_engine.py
if errorlevel 1 goto error

echo [8/9] Launcher bridge en startdashboard uitvoeren...
python baoees\project_analyzer\project_analyzer_launcher_bridge.py
if errorlevel 1 goto error

echo [9/9] Health check uitvoeren...
python baoees\project_analyzer\project_analysis_health_check_engine.py
if errorlevel 1 goto error

echo.
echo PROJECT PHOENIX v6.6 START PROJECTANALYSE KLAAR
echo.

if exist "outputs\bib\dashboards\brewster_knowledge_migration_dashboard_v6_6.html" (
    start "" "outputs\bib\dashboards\brewster_knowledge_migration_dashboard_v6_6.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.6 is gestopt.
echo Controleer de foutmelding hierboven.
echo.
git status
pause
exit /b 1
