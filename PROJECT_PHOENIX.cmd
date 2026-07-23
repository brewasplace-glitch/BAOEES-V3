@echo off
setlocal
set "REPO_ROOT=C:\PROJECT-PHOENIX"
powershell.exe -NoExit -ExecutionPolicy Bypass -File "%REPO_ROOT%\runners\PROJECT_PHOENIX_CONSOLE.ps1" -RepoRoot "%REPO_ROOT%"
endlocal
