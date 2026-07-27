param([string]$Repository = "C:\PROJECT-PHOENIX")
$ErrorActionPreference = "Stop"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Project Phoenix.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $Repository "START_PHOENIX.ps1") + '"'
$Shortcut.WorkingDirectory = $Repository
$Shortcut.Description = "Start Project Phoenix Local"
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,21"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
