@echo off
setlocal
cd /d "%~dp0"

echo PROJECT PHOENIX / BAOEES - START PROJECTANALYSE v7.0

python baoees\project_analyzer\project_intake_engine.py || goto error
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

echo PROJECT PHOENIX v7.0 START PROJECTANALYSE KLAAR

if exist "outputs\projects\project_intake_dashboard_v7_0.html" (
    start "" "outputs\projects\project_intake_dashboard_v7_0.html"
)

git status
pause
exit /b 0

:error
echo FOUT: START PROJECTANALYSE v7.0 is gestopt.
git status
pause
exit /b 1
