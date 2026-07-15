param(
 [ValidateSet("self-test","build","validate","reason","query")][string]$Mode="reason",
 [ValidateSet("module","config","documentation","engine")][string]$NodeType="engine"
)
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$Engine=".\apps\brewster_engineering_wizard\project_analyzer\phoenix_knowledge_reasoning_v18_0.py"
switch($Mode){
 "self-test"{python $Engine self-test}
 "build"{python $Engine build}
 "validate"{python $Engine validate}
 "reason"{python $Engine reason}
 "query"{python $Engine query --node-type $NodeType}
}
if($LASTEXITCODE -ne 0){throw "Phoenix Core v18.0 Knowledge Graph & Reasoning is mislukt."}
git status
