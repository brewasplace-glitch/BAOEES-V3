# PROJECT PHOENIX v8.0 UPDATE
# Phoenix Task Autopilot Engine
# Geen handmatig Python knip- en plakwerk nodig.

$ErrorActionPreference = "Stop"

Write-Host "PROJECT PHOENIX v8.0 UPDATE START" -ForegroundColor Cyan

$ProjectRoot = Get-Location

if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {
    throw "Dit script moet vanuit de root van de PROJECT-PHOENIX repository worden uitgevoerd."
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$EnginePath = Join-Path $ProjectRoot "apps\brewster_engineering_wizard\project_analyzer\phoenix_task_autopilot_engine.py"
$ScriptDir = Join-Path $ProjectRoot "scripts"
$RunnerPs1 = Join-Path $ScriptDir "START_PROJECTANALYSE_v8_0.ps1"
$RunnerBat = Join-Path $ScriptDir "START_PROJECTANALYSE_v8_0.bat"
$LogPath = Join-Path $ProjectRoot "outputs\projects\start_projectanalyse_v8_0_update_log.json"

New-Item -ItemType Directory -Path (Split-Path $EnginePath) -Force | Out-Null
New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path $LogPath) -Force | Out-Null

foreach ($Path in @($EnginePath, $RunnerPs1, $RunnerBat)) {
    if (Test-Path $Path) {
        Copy-Item $Path "$Path.backup_v8_0_$Timestamp" -Force
    }
}

$EngineContent = @'
from __future__ import annotations

import html
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / '.git').exists():
            return parent
    return here.parents[3]


PROJECT_ROOT = find_project_root()


class PhoenixTaskAutopilotEngine:
    ENGINE_NAME = 'Project Phoenix Task Autopilot Engine'
    ENGINE_VERSION = 'v8.0'

    def __init__(self) -> None:
        self.outputs = PROJECT_ROOT / 'outputs' / 'projects'
        self.docs = PROJECT_ROOT / 'DOCS' / 'project_phoenix' / 'task_autopilot'
        self.roadmap_status_path = self.outputs / 'phoenix_task_roadmap_status_v7_9.json'
        self.roadmap_fallback_path = self.outputs / 'phoenix_task_roadmap_v7_6.json'
        self.next_go_path = self.outputs / 'phoenix_next_go_step_v7_9.json'
        self.rules_path = self.outputs / 'phoenix_build_rules_v7_6.json'
        self.plan_path = self.outputs / 'phoenix_task_autopilot_plan_v8_0.json'
        self.selected_task_path = self.outputs / 'phoenix_task_autopilot_selected_task_v8_0.json'
        self.execution_result_path = self.outputs / 'phoenix_task_autopilot_execution_result_v8_0.json'
        self.dashboard_path = self.outputs / 'phoenix_task_autopilot_dashboard_v8_0.html'
        self.log_path = self.outputs / 'phoenix_task_autopilot_log_v8_0.json'
        self.doc_path = self.docs / 'phoenix_task_autopilot_v8_0.md'

    def run(self) -> Dict[str, Any]:
        self.outputs.mkdir(parents=True, exist_ok=True)
        self.docs.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now().isoformat(timespec='seconds')
        roadmap = self.read_json(self.roadmap_status_path) or self.read_json(self.roadmap_fallback_path)
        next_go = self.read_json(self.next_go_path)
        rules = self.read_json(self.rules_path)
        git_before = self.git_state()
        selected_task = self.select_next_task(roadmap, next_go)
        go_gate = self.evaluate_go_gate(selected_task, rules)
        execution = self.execute_safe_scaffold(selected_task, go_gate)
        git_after = self.git_state()
        plan = self.build_plan(selected_task, go_gate, execution, git_before, git_after)
        self.write_json(self.plan_path, plan)
        self.write_json(self.selected_task_path, selected_task)
        self.write_json(self.execution_result_path, execution)
        self.write_text(self.dashboard_path, self.build_dashboard(plan))
        self.write_text(self.doc_path, self.build_documentation(plan))
        result = {
            'status': 'OPGESLAGEN',
            'engine': self.ENGINE_NAME,
            'engine_version': self.ENGINE_VERSION,
            'started_at': started_at,
            'finished_at': datetime.now().isoformat(timespec='seconds'),
            'project_root': str(PROJECT_ROOT),
            'selected_task_id': selected_task.get('task_id', ''),
            'selected_task_title': selected_task.get('title', ''),
            'go_required': go_gate.get('go_required', True),
            'autopilot_action': execution.get('action', ''),
            'autopilot_status': execution.get('status', ''),
            'plan_path': str(self.plan_path),
            'selected_task_path': str(self.selected_task_path),
            'execution_result_path': str(self.execution_result_path),
            'dashboard_path': str(self.dashboard_path),
            'documentation_path': str(self.doc_path),
            'git_clean_after': git_after.get('is_clean', False),
            'next_instruction': execution.get('next_instruction', 'Controleer dashboard en git status.'),
        }
        self.write_json(self.log_path, result)
        return result

    def select_next_task(self, roadmap: Dict[str, Any], next_go: Dict[str, Any]) -> Dict[str, Any]:
        next_task = next_go.get('next_safe_step', {}) if isinstance(next_go, dict) else {}
        if isinstance(next_task, dict) and next_task.get('task_id') and next_task.get('task_id') != 'ROADMAP-COMPLETE':
            return next_task
        tasks = roadmap.get('tasks', []) if isinstance(roadmap, dict) else []
        open_tasks = [t for t in tasks if isinstance(t, dict) and t.get('status', 'open') == 'open']
        if open_tasks:
            return sorted(open_tasks, key=lambda item: item.get('priority', 999999))[0]
        return {
            'task_id': 'S01-002',
            'track': 'Stabilisatie & automatisering',
            'track_id': 'S01',
            'priority': 102,
            'title': 'Automated cleanup helper',
            'objective': 'Bouw een gecontroleerde Phoenix cleanup helper.',
            'files_to_create_or_modify': [
                'apps/brewster_engineering_wizard/project_analyzer/automated_cleanup_helper.py',
                'DOCS/project_phoenix/s01/automated_cleanup_helper.md',
                'outputs/projects/automated_cleanup_helper_log.json',
                'outputs/projects/automated_cleanup_helper_dashboard.html',
            ],
            'test_command': 'python -m py_compile apps/brewster_engineering_wizard/project_analyzer/automated_cleanup_helper.py',
            'commit_message': 'feat: add automated cleanup helper (S01-002)',
            'risk_level': 'laag',
            'requires_go': False,
            'status': 'open',
        }

    def evaluate_go_gate(self, task: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
        risk = str(task.get('risk_level', 'middel')).lower()
        requires_go = bool(task.get('requires_go', True))
        safe_to_scaffold = (risk == 'laag' and not requires_go)
        return {
            'status': 'OPEN' if requires_go else 'PASS_FOR_SCAFFOLD',
            'go_required': requires_go,
            'risk_level': risk,
            'safe_to_scaffold_now': safe_to_scaffold,
            'reason': self.go_reason(risk, requires_go),
            'safe_scope': ['create_new_files_only', 'no_overwrite', 'no_auto_commit', 'no_auto_push', 'show_git_status'],
        }

    def go_reason(self, risk: str, requires_go: bool) -> str:
        if requires_go:
            return 'Roadmaptaak vereist expliciete GO voordat inhoudelijke uitvoering start.'
        if risk != 'laag':
            return 'Risico is niet laag; Autopilot beperkt zich tot voorbereiding.'
        return 'Laag risico en geen expliciete GO vereist; Autopilot mag veilige scaffoldbestanden aanmaken.'

    def execute_safe_scaffold(self, task: Dict[str, Any], go_gate: Dict[str, Any]) -> Dict[str, Any]:
        if not go_gate.get('safe_to_scaffold_now'):
            return {'status': 'WAITING_FOR_GO', 'action': 'prepared_only', 'created_files': [], 'skipped_files': [], 'errors': [], 'next_instruction': 'Geef GO als deze roadmaptaak inhoudelijk uitgevoerd mag worden.'}
        files = task.get('files_to_create_or_modify', [])
        if not isinstance(files, list):
            files = []
        created, skipped, errors = [], [], []
        for rel in files:
            relative = str(rel).replace('\\', '/').strip()
            if not relative:
                continue
            target = PROJECT_ROOT / relative
            try:
                if target.exists():
                    skipped.append({'path': str(target), 'reason': 'Bestand bestaat al; Autopilot overschrijft niet.'})
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(self.content_for(target, task), encoding='utf-8')
                created.append({'path': str(target), 'reason': 'Veilig scaffoldbestand aangemaakt.'})
            except Exception as exc:
                errors.append({'path': str(target), 'error': str(exc)})
        test_result = self.run_task_test(task)
        return {
            'status': 'SCAFFOLD_EXECUTED' if not errors else 'SCAFFOLD_WITH_ERRORS',
            'action': 'safe_scaffold_created',
            'created_files': created,
            'skipped_files': skipped,
            'errors': errors,
            'test_result': test_result,
            'next_instruction': 'Controleer bestanden, commit en push pas na review.',
        }

    def content_for(self, target: Path, task: Dict[str, Any]) -> str:
        suffix = target.suffix.lower()
        if suffix == '.py':
            return self.python_scaffold(task)
        if suffix == '.md':
            return self.markdown_scaffold(task)
        if suffix == '.html':
            return self.html_scaffold(task)
        if suffix == '.json':
            return self.json_scaffold(task)
        return 'Project Phoenix Autopilot scaffoldbestand.\n'

    def python_scaffold(self, task: Dict[str, Any]) -> str:
        title = str(task.get('title', 'Phoenix Autopilot Task'))
        task_id = str(task.get('task_id', 'TASK'))
        class_name = self.class_name(title)
        slug = self.safe_slug(title)
        lines = [
            'from __future__ import annotations',
            '',
            'import json',
            'from datetime import datetime',
            'from pathlib import Path',
            'from typing import Any, Dict',
            '',
            'def find_project_root() -> Path:',
            '    here = Path(__file__).resolve()',
            '    for parent in here.parents:',
            "        if (parent / '.git').exists():",
            '            return parent',
            '    return here.parents[3]',
            '',
            'PROJECT_ROOT = find_project_root()',
            '',
            f'class {class_name}:',
            f'    ENGINE_NAME = {title!r}',
            f'    TASK_ID = {task_id!r}',
            "    ENGINE_VERSION = 'autopilot_scaffold_v8_0'",
            '',
            '    def __init__(self) -> None:',
            "        self.outputs = PROJECT_ROOT / 'outputs' / 'projects'",
            f"        self.log_path = self.outputs / '{slug}_log.json'",
            f"        self.dashboard_path = self.outputs / '{slug}_dashboard.html'",
            '',
            '    def run(self) -> Dict[str, Any]:',
            '        self.outputs.mkdir(parents=True, exist_ok=True)',
            '        result = {',
            "            'status': 'AUTOPILOT_SCAFFOLD_READY',",
            "            'task_id': self.TASK_ID,",
            "            'engine': self.ENGINE_NAME,",
            "            'engine_version': self.ENGINE_VERSION,",
            "            'generated_at': datetime.now().isoformat(timespec='seconds'),",
            "            'project_root': str(PROJECT_ROOT),",
            "            'next_step': 'Vul deze scaffold met echte taaklogica in een volgende GO-stap.',",
            '        }',
            "        self.log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8-sig')",
            "        self.dashboard_path.write_text('<!doctype html><html><body><h1>' + self.ENGINE_NAME + '</h1><p>AUTOPILOT_SCAFFOLD_READY</p></body></html>', encoding='utf-8')",
            '        return result',
            '',
            'def main() -> None:',
            f'    engine = {class_name}()',
            '    result = engine.run()',
            '    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))',
            '',
            "if __name__ == '__main__':",
            '    main()',
            '',
        ]
        return '\n'.join(lines)

    def markdown_scaffold(self, task: Dict[str, Any]) -> str:
        return '# ' + str(task.get('title', 'Phoenix Autopilot Task')) + '\n\n' + \
            'Taak: `' + str(task.get('task_id', '')) + '`  \n' + \
            'Spoor: ' + str(task.get('track', '')) + '  \n' + \
            'Risico: ' + str(task.get('risk_level', '')) + '\n\n' + \
            '## Doel\n\n' + str(task.get('objective', '')) + '\n\n' + \
            '## Test\n\n```powershell\n' + str(task.get('test_command', 'git status')) + '\n```\n\n' + \
            '## Commitvoorstel\n\n```powershell\ngit commit -m "' + str(task.get('commit_message', 'chore: autopilot scaffold')) + '"\n```\n\n' + \
            '## Status\n\nAangemaakt door Project Phoenix Task Autopilot Engine v8.0.\n'

    def html_scaffold(self, task: Dict[str, Any]) -> str:
        title = html.escape(str(task.get('title', '')))
        task_id = html.escape(str(task.get('task_id', '')))
        return '<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>' + title + '</title></head><body><h1>' + title + '</h1><p>Taak: <code>' + task_id + '</code></p><p>Status: AUTOPILOT_SCAFFOLD_READY</p></body></html>\n'

    def json_scaffold(self, task: Dict[str, Any]) -> str:
        return json.dumps({'status': 'AUTOPILOT_SCAFFOLD_READY', 'task_id': task.get('task_id', ''), 'title': task.get('title', ''), 'track': task.get('track', ''), 'generated_by': self.ENGINE_NAME, 'generated_at': datetime.now().isoformat(timespec='seconds')}, ensure_ascii=False, indent=2)

    def run_task_test(self, task: Dict[str, Any]) -> Dict[str, Any]:
        command = str(task.get('test_command', 'git status')).strip() or 'git status'
        if 'py_compile' not in command:
            return {'status': 'SKIPPED', 'command': command, 'reason': 'Autopilot v8.0 draait alleen veilige py_compile tests automatisch.'}
        try:
            completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, shell=True, check=False)
            return {'status': 'PASS' if completed.returncode == 0 else 'FAIL', 'command': command, 'returncode': completed.returncode, 'stdout': completed.stdout[-2000:], 'stderr': completed.stderr[-2000:]}
        except Exception as exc:
            return {'status': 'ERROR', 'command': command, 'error': str(exc)}

    def build_plan(self, task: Dict[str, Any], go_gate: Dict[str, Any], execution: Dict[str, Any], git_before: Dict[str, Any], git_after: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'status': 'OPGESLAGEN',
            'engine': self.ENGINE_NAME,
            'engine_version': self.ENGINE_VERSION,
            'generated_at': datetime.now().isoformat(timespec='seconds'),
            'project_root': str(PROJECT_ROOT),
            'selected_task': task,
            'go_gate': go_gate,
            'execution_result': execution,
            'git_before': git_before,
            'git_after': git_after,
            'safety_policy': {'auto_commit': False, 'auto_push': False, 'overwrite_existing_files': False, 'delete_files': False, 'run_only_safe_tests': True},
            'next_steps': ['Controleer dashboard en git status.', 'Commit/push alleen na review.', 'Run v7.9 of volgende statusengine om roadmapstatus bij te werken.'],
        }

    def git_state(self) -> Dict[str, Any]:
        status = self.run_git(['status', '--porcelain'])
        return {'branch': self.run_git(['branch', '--show-current']).strip(), 'is_clean': status.strip() == '', 'porcelain_status': status, 'latest_commit': self.run_git(['rev-parse', '--short', 'HEAD']).strip(), 'latest_commit_message': self.run_git(['log', '-1', '--pretty=%s']).strip()}

    def run_git(self, args: List[str]) -> str:
        try:
            completed = subprocess.run(['git'] + args, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
            return (completed.stdout or completed.stderr or '').strip()
        except Exception as exc:
            return f'git_error: {exc}'

    def build_dashboard(self, plan: Dict[str, Any]) -> str:
        task = plan['selected_task']
        go_gate = plan['go_gate']
        execution = plan['execution_result']
        created_rows = ''.join('<tr><td><code>' + self.esc(i.get('path', '')) + '</code></td><td>' + self.esc(i.get('reason', '')) + '</td></tr>' for i in execution.get('created_files', [])) or "<tr><td colspan='2'>Geen bestanden aangemaakt.</td></tr>"
        skipped_rows = ''.join('<tr><td><code>' + self.esc(i.get('path', '')) + '</code></td><td>' + self.esc(i.get('reason', '')) + '</td></tr>' for i in execution.get('skipped_files', [])) or "<tr><td colspan='2'>Geen bestanden overgeslagen.</td></tr>"
        test_result = execution.get('test_result', {})
        return f'''<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<title>Project Phoenix Task Autopilot v8.0</title>
<style>
body {{ margin:0; font-family:Arial,sans-serif; background:#0f172a; color:#e5e7eb; }}
main {{ max-width:1280px; margin:0 auto; padding:32px; }}
section {{ background:#111827; border:1px solid #334155; border-radius:14px; padding:20px; margin-bottom:18px; }}
h1,h2 {{ color:#f8fafc; }}
table {{ width:100%; border-collapse:collapse; }}
td,th {{ border:1px solid #334155; padding:10px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
code {{ color:#bfdbfe; }}
.badge {{ display:inline-block; padding:6px 10px; background:#1e293b; border-radius:999px; }}
</style>
</head>
<body>
<main>
<section><h1>Project Phoenix Task Autopilot Engine v8.0</h1><p>Status: <strong>{self.esc(plan.get('status', ''))}</strong></p><p>Actie: <span class="badge">{self.esc(execution.get('action', ''))}</span></p><p>Resultaat: <strong>{self.esc(execution.get('status', ''))}</strong></p></section>
<section><h2>Geselecteerde taak</h2><p><strong>{self.esc(task.get('task_id', ''))}</strong> — {self.esc(task.get('title', ''))}</p><p>{self.esc(task.get('objective', ''))}</p><p>Spoor: {self.esc(task.get('track', ''))}</p><p>Risico: <strong>{self.esc(task.get('risk_level', ''))}</strong></p></section>
<section><h2>GO-gate</h2><p>GO vereist: <strong>{self.esc(go_gate.get('go_required', ''))}</strong></p><p>Safe scaffold nu: <strong>{self.esc(go_gate.get('safe_to_scaffold_now', ''))}</strong></p><p>Reden: {self.esc(go_gate.get('reason', ''))}</p></section>
<section><h2>Aangemaakte bestanden</h2><table><tr><th>Bestand</th><th>Toelichting</th></tr>{created_rows}</table></section>
<section><h2>Overgeslagen bestanden</h2><table><tr><th>Bestand</th><th>Toelichting</th></tr>{skipped_rows}</table></section>
<section><h2>Testresultaat</h2><p>Status: <strong>{self.esc(test_result.get('status', 'niet uitgevoerd'))}</strong></p><p>Command: <code>{self.esc(test_result.get('command', ''))}</code></p></section>
</main>
</body>
</html>'''

    def build_documentation(self, plan: Dict[str, Any]) -> str:
        task = plan['selected_task']
        execution = plan['execution_result']
        return '\n'.join(['# Project Phoenix Task Autopilot v8.0', '', 'Deze engine bereidt de volgende roadmaptaak gecontroleerd voor en voert alleen veilige scaffoldacties uit.', '', f'- Taak: {task.get("task_id", "")}', f'- Titel: {task.get("title", "")}', f'- Actie: {execution.get("action", "")}', f'- Status: {execution.get("status", "")}', '', '## Veiligheidsregels', '', '- Geen automatische commit.', '- Geen automatische push.', '- Geen overschrijven van bestaande bestanden.', '- Geen verwijderen van bestanden.', '- Alleen veilige tests automatisch.', ''])

    def class_name(self, value: Any) -> str:
        words = re.findall(r'[A-Za-z0-9]+', str(value))
        name = ''.join(word.capitalize() for word in words) or 'PhoenixTask'
        if name[0].isdigit():
            name = 'Task' + name
        return name + 'Engine'

    def safe_slug(self, value: Any) -> str:
        text = str(value).strip().lower()
        text = re.sub(r'[^a-z0-9]+', '_', text)
        text = re.sub(r'_+', '_', text).strip('_')
        return text or 'task'

    def read_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8-sig'))
        except Exception:
            try:
                return json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                return {}

    def write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8-sig')

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def esc(self, value: Any) -> str:
        return html.escape(str(value), quote=True)


TaskAutopilotEngine = PhoenixTaskAutopilotEngine
PhoenixAutopilotEngine = PhoenixTaskAutopilotEngine


def main() -> None:
    engine = PhoenixTaskAutopilotEngine()
    result = engine.run()
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))


if __name__ == '__main__':
    main()
'@

$RunnerPs1Content = @'
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "PROJECT PHOENIX - TASK AUTOPILOT v8.0" -ForegroundColor Cyan

python .\apps\brewster_engineering_wizard\project_analyzer\phoenix_task_autopilot_engine.py

if ($LASTEXITCODE -ne 0) {
    throw "Phoenix Task Autopilot Engine v8.0 mislukt."
}

$Dashboard = Join-Path $ProjectRoot "outputs\projects\phoenix_task_autopilot_dashboard_v8_0.html"

if (Test-Path $Dashboard) {
    Start-Process $Dashboard
}

git status
'@

$RunnerBatContent = @'
@echo off
setlocal
cd /d "%~dp0\.."

echo PROJECT PHOENIX - TASK AUTOPILOT v8.0

python apps\brewster_engineering_wizard\project_analyzer\phoenix_task_autopilot_engine.py || goto error

if exist "outputs\projects\phoenix_task_autopilot_dashboard_v8_0.html" (
    start "" "outputs\projects\phoenix_task_autopilot_dashboard_v8_0.html"
)

git status
pause
exit /b 0

:error
echo FOUT: Phoenix Task Autopilot Engine v8.0 is gestopt.
git status
pause
exit /b 1
'@

Set-Content -Path $EnginePath -Value $EngineContent -Encoding UTF8
Set-Content -Path $RunnerPs1 -Value $RunnerPs1Content -Encoding UTF8
Set-Content -Path $RunnerBat -Value $RunnerBatContent -Encoding ASCII

$UpdateLog = [ordered]@{
    status = "OPGESLAGEN"
    engine = "Project Phoenix Task Autopilot Connector"
    engine_version = "v8.0"
    generated_at = (Get-Date).ToString("s")
    project_root = "$ProjectRoot"
    engine_path = "$EnginePath"
    runner_ps1 = "$RunnerPs1"
    runner_bat = "$RunnerBat"
    repository_policy = "Alleen PROJECT-PHOENIX repository"
}

$UpdateLog | ConvertTo-Json -Depth 5 | Set-Content -Path $LogPath -Encoding UTF8

Write-Host "Bestanden geschreven." -ForegroundColor Green

Write-Host "Syntaxcontrole Phoenix Task Autopilot Engine..." -ForegroundColor Cyan
python -m py_compile .\apps\brewster_engineering_wizard\project_analyzer\phoenix_task_autopilot_engine.py

Write-Host "Run v8.0..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\scripts\START_PROJECTANALYSE_v8_0.ps1

Write-Host "Git status..." -ForegroundColor Cyan
git status

Write-Host "PROJECT PHOENIX v8.0 UPDATE KLAAR" -ForegroundColor Green
