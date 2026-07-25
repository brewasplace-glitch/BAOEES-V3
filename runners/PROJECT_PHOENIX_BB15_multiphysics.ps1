param([string]$RepoRoot="C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
Set-Location $RepoRoot
$env:PYTHONPATH=$RepoRoot
@'
from pathlib import Path
from phoenix.multiphysics import *
registry=EngineRegistry(); register_default_adapters(registry)
gis=AnalysisTask("QGIS","prepare_geometry",{"metrics":{"span":3.0}})
os=AnalysisTask("OpenSees","structural_analysis",
 {"metrics":{"tip_displacement":-0.0535,"reaction":10000.0}},[gis.task_id])
cx=AnalysisTask("CalculiX","finite_element_analysis",
 {"metrics":{"tip_displacement":-0.0536,"reaction":10000.0}},[gis.task_id])
workflow=MultiPhysicsWorkflow("BB15 Demo","BB15-DEMO",[gis,os,cx])
engine=MultiPhysicsOrchestrator(registry)
result=engine.execute(workflow)
checksum=engine.save_evidence(Path("outputs/runtime/bb15/evidence.json"),result)
if not result["success"]: raise RuntimeError("BB15 workflow failed")
print("Phoenix Multi-Physics Coordination self-test: PASSED")
print("Tasks:",len(result["executions"]))
print("Engines:",result["fusion"]["source_engines"])
print("Checksum:",checksum)
'@ | python -
if($LASTEXITCODE-ne 0){throw "BB15 self-test failed"}
