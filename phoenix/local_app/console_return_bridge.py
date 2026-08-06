from __future__ import annotations

import ctypes
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = PROJECT_ROOT / "outputs" / "runtime" / "phoenix_console_bridge_v1_0" / "active_console.json"


def _read_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _open_fallback_console() -> dict[str, Any]:
    command = (
        "$host.UI.RawUI.WindowTitle='PROJECT PHOENIX - ACTIVE CONSOLE'; "
        "Set-Location -LiteralPath '" + str(PROJECT_ROOT).replace("'", "''") + "'; "
        "$env:PHOENIX_BRAVE_SEARCH_API_KEY=[Environment]::GetEnvironmentVariable('PHOENIX_BRAVE_SEARCH_API_KEY','User'); "
        "Write-Host 'PROJECT PHOENIX - ACTIVE CONSOLE' -ForegroundColor Cyan; "
        "Write-Host ('Repository: ' + (Get-Location));"
    )
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen(["powershell.exe", "-NoExit", "-NoProfile", "-Command", command], cwd=str(PROJECT_ROOT), creationflags=creationflags)
    return {
        "ok": True,
        "status": "FALLBACK_CONSOLE_OPENED",
        "message": "De oorspronkelijke Phoenix-console was niet meer beschikbaar; een nieuwe Phoenix PowerShell is geopend.",
    }


def activate_registered_console() -> dict[str, Any]:
    if os.name != "nt":
        return {"ok": False, "status": "WINDOWS_ONLY", "message": "PowerShell window activation is only available on Windows."}
    state = _read_state()
    hwnd_value = state.get("console_hwnd")
    try:
        hwnd = int(hwnd_value or 0)
    except Exception:
        hwnd = 0
    user32 = ctypes.windll.user32
    if hwnd and user32.IsWindow(hwnd):
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        try:
            user32.BringWindowToTop(hwnd)
        except Exception:
            pass
        activated = bool(user32.SetForegroundWindow(hwnd))
        try:
            user32.SwitchToThisWindow(hwnd, True)
            activated = True
        except Exception:
            pass
        return {
            "ok": True,
            "status": "ACTIVE_CONSOLE_ACTIVATED" if activated else "ACTIVE_CONSOLE_RESTORED",
            "message": "Phoenix PowerShell naar de voorgrond gebracht.",
            "registered_utc": state.get("registered_utc"),
        }
    return _open_fallback_console()
