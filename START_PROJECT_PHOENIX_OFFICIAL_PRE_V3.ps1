param([string]$Repository = "C:\PROJECT-PHOENIX")
$ErrorActionPreference="Stop"
$Html=Join-Path $Repository "phoenix\local_app\static\official_start_v3_0\index.html"
if(-not(Test-Path -LiteralPath $Html -PathType Leaf)){throw "Official Phoenix start screen not found: $Html"}
$Candidates=@("START_PROJECT_PHOENIX_LOCAL_APP.ps1","START_PHOENIX_LOCAL_APP.ps1","START_PROJECT_PHOENIX.ps1","START_PHOENIX.ps1")
foreach($Candidate in $Candidates){$Path=Join-Path $Repository $Candidate;if(Test-Path -LiteralPath $Path -PathType Leaf){try{Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$Path`"")|Out-Null}catch{};break}}
Start-Process $Html
