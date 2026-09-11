[CmdletBinding()]
param([string]$RepoRoot="C:\PROJECT-PHOENIX",[string]$SourcePdf="",[string]$OutputRoot="")
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
function Fail([string]$m){throw $m}
function Py {
 param([Parameter(Mandatory=$true)][string[]]$PyArgs)
 if(Get-Command py.exe -ErrorAction SilentlyContinue){$exe="py.exe";$prefix=@("-3")}
 elseif(Get-Command python.exe -ErrorAction SilentlyContinue){$exe="python.exe";$prefix=@()}
 else{Fail "Python 3 not found"}
 $old=$ErrorActionPreference;$ErrorActionPreference="Continue"
 try{$o=@(& $exe @prefix @PyArgs 2>&1);$c=$LASTEXITCODE}finally{$ErrorActionPreference=$old}
 $o|ForEach-Object{Write-Host $_};if($c-ne 0){Fail "Python failed with exit code ${c}"}
}
if(-not $SourcePdf){Fail "SourcePdf required"}
if(-not(Test-Path -LiteralPath $SourcePdf -PathType Leaf)){Fail "SourcePdf missing"}
if(-not $OutputRoot){$stamp=Get-Date -Format "yyyyMMddTHHmmss";$OutputRoot=Join-Path $env:USERPROFILE "Downloads\PHOENIX_ANIJSTRAAT_616_STRUCTURAL_DERIVATION_LOAD_$stamp"}
New-Item -ItemType Directory -Force -Path $OutputRoot|Out-Null
$deps=Join-Path $env:LOCALAPPDATA "PROJECT-PHOENIX\runtime_deps\pdf_gap_v1";$env:PYTHONPATH="$RepoRoot;$deps"
$ga=Join-Path $RepoRoot "phoenix\structural_input_gap\analyzer.py"
$gc=Join-Path $RepoRoot "configs\phoenix\anijstraat_616_structural_input_gap_v1.json"
$go=Join-Path $OutputRoot "_prerequisite_gap"
$en=Join-Path $RepoRoot "phoenix\structural_derivation_load\engine.py"
$cf=Join-Path $RepoRoot "configs\phoenix\anijstraat_616_structural_derivation_load_v1.json"
foreach($f in @($ga,$gc,$en,$cf)){if(-not(Test-Path -LiteralPath $f -PathType Leaf)){Fail "Required file missing: $f"}}
Py -PyArgs @($ga,"--pdf",$SourcePdf,"--config",$gc,"--output",$go)
$gj=Join-Path $go "structural_input_gap_analysis.json"
Py -PyArgs @($en,"--pdf",$SourcePdf,"--gap-json",$gj,"--config",$cf,"--output",$OutputRoot)
Py -PyArgs @($en,"--verify-output",(Join-Path $OutputRoot "structural_derivation_load_model.json"))
Write-Host "PHOENIX_4_41_ANIJSTRAAT_616_STRUCTURAL_DERIVATION_LOAD=PASS" -ForegroundColor Green
Write-Host "NEXT_STAGE=PHOENIX_4.41_REAL_PROJECT_SOLVER_EXECUTION_AND_ELEMENT_VERIFICATION"
Write-Host "OUTPUT=$OutputRoot"
