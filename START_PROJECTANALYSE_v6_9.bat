@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v6.9
echo ============================================================

python baoees\project_analyzer\brewster_knowledge_migration_engine.py || goto error
python baoees\project_analyzer\deep_knowledge_harvest_engine.py || goto error
python baoees\project_analyzer\module_registry_engine.py || goto error
python baoees\project_analyzer\project_start_analysis_engine.py || goto error
python baoees\project_analyzer\project_analyzer_workflow_engine.py || goto error
python baoees\project_analyzer\aaie_bib_assumption_loader.py || goto error
python baoees\project_analyzer\project_report_bib_engine.py || goto error
python baoees\project_analyzer\project_report_export_engine.py || goto error
python baoees\project_analyzer\project_package_evidence_engine.py || goto error
python baoees\project_analyzer\project_analyzer_launcher_bridge.py || goto error
python baoees\project_analyzer\project_analysis_health_check_engine.py || goto error
python baoees\project_analyzer\project_error_diagnostics_engine.py || goto error
python baoees\project_analyzer\project_auto_repair_engine.py || goto error
python baoees\project_analyzer\project_analysis_health_check_engine.py || goto error

echo.
echo PROJECT PHOENIX v6.9 START PROJECTANALYSE KLAAR

if exist "outputs\projects\module_registry_dashboard_v6_9.html" (
    start "" "outputs\projects\module_registry_dashboard_v6_9.html"
)

git status
pause
exit /b 0

:error
echo.
echo FOUT: START PROJECTANALYSE v6.9 is gestopt.
git status
pause
exit /b 1
