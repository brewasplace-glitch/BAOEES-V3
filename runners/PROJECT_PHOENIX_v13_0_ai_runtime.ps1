param(
 [ValidateSet("self-test","health","plan","execute","resume")][string]$Mode="plan",
 [string]$RuntimeId="phoenix-core-v13",
 [string[]]$Capability=@("workflow.orchestration","workflow.autonomous","engine.discovery"),
 [string]$ApprovalToken=""
)
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$E=".\apps\brewster_engineering_wizard\project_analyzer\phoenix_ai_runtime_v13_0.py"
switch($Mode){
 "self-test"{python $E self-test}
 "health"{python $E health}
 "plan"{$a=@($E,"plan","--runtime-id",$RuntimeId);foreach($c in $Capability){$a+=@("--capability",$c)};python @a}
 "execute"{python $E execute --runtime-id $RuntimeId --approval-token $ApprovalToken}
 "resume"{python $E resume --runtime-id $RuntimeId --approval-token $ApprovalToken}
}
if($LASTEXITCODE -ne 0){throw "Phoenix AI Runtime v13.0 geblokkeerd of mislukt."}
git status
