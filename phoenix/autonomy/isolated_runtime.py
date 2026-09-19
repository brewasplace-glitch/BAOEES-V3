from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from xml.sax.saxutils import escape as xml_escape


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class RuntimeProviderProbe:
    provider_id: str
    provider_version: str
    available: bool
    security_boundary: bool
    execution_enabled: bool
    reasons: tuple[str, ...]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "available": self.available,
            "security_boundary": self.security_boundary,
            "execution_enabled": self.execution_enabled,
            "reasons": list(self.reasons),
            "evidence": self.evidence,
        }


class IsolatedRuntimeProvider(Protocol):
    provider_id: str
    provider_version: str

    def probe(self) -> RuntimeProviderProbe: ...

    def execute(self, source: str, request: dict[str, Any]) -> dict[str, Any]: ...


class DisabledRuntimeProvider:
    provider_id = "disabled.no_accepted_runtime"
    provider_version = "1.0.0"

    def __init__(self, reasons: tuple[str, ...] | list[str] | str):
        if isinstance(reasons, str):
            reasons = (reasons,)
        self.reasons = tuple(str(x) for x in reasons)

    def probe(self) -> RuntimeProviderProbe:
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            False,
            False,
            False,
            self.reasons or ("NO_ACCEPTED_RUNTIME_PROVIDER",),
            {},
        )

    def execute(self, source: str, request: dict[str, Any]) -> dict[str, Any]:
        raise PermissionError("CANDIDATE_EXECUTION_DENY:NO_ACCEPTED_RUNTIME_PROVIDER")


def build_adapter_harness(source: str, request: Mapping[str, Any]) -> str:
    """Build the trusted, deterministic harness executed inside the boundary."""
    payload = base64.b64encode(source.encode("utf-8")).decode("ascii")
    source_sha = _sha(source.encode("utf-8"))
    action = str(request["action"])
    class_name = str(request["class_name"])
    nonce = str(request["nonce"])
    repetitions = int(request.get("repetitions", 2))
    return f'''from __future__ import annotations
import base64
import hashlib
import json
import sys
import types

SOURCE = base64.b64decode({payload!r}).decode("utf-8")
EXPECTED_SHA = {source_sha!r}
ACTION = {action!r}
CLASS_NAME = {class_name!r}
NONCE = {nonce!r}
REPETITIONS = {repetitions!r}

if hashlib.sha256(SOURCE.encode("utf-8")).hexdigest() != EXPECTED_SHA:
    raise SystemExit("SOURCE_SHA256_MISMATCH")

class AdapterExecutionResult:
    def __init__(self, status, result=None, reason=None):
        self.status = status
        self.result = result
        self.reason = reason

stub = types.ModuleType("phoenix.autonomy.executor_adapters")
stub.AdapterExecutionResult = AdapterExecutionResult
stub.AdapterExecutionContext = object
phoenix = types.ModuleType("phoenix")
autonomy = types.ModuleType("phoenix.autonomy")
phoenix.autonomy = autonomy
autonomy.executor_adapters = stub
sys.modules["phoenix"] = phoenix
sys.modules["phoenix.autonomy"] = autonomy
sys.modules["phoenix.autonomy.executor_adapters"] = stub

namespace = {{"__name__": "phoenix_phase9_candidate"}}
exec(compile(SOURCE, "candidate.py", "exec"), namespace, namespace)
adapter = namespace[CLASS_NAME](None)

class Step:
    action = ACTION

class Context:
    step = Step()

results = []
for _ in range(REPETITIONS):
    value = adapter.execute(Context())
    results.append({{
        "status": value.status,
        "result": value.result,
        "reason": value.reason,
    }})

print(json.dumps({{
    "schema": "PHOENIX_PHASE9_BOUNDARY_RESULT_V1",
    "nonce": NONCE,
    "source_sha256": EXPECTED_SHA,
    "candidate_code_executed": True,
    "results": results,
}}, sort_keys=True, separators=(",", ":")))
'''


class PodmanMachineRuntimeProvider:
    provider_id = "containers.podman.machine.rootless"
    provider_version = "1.0.0"

    def __init__(
        self,
        policy: Mapping[str, Any],
        runtime_root: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ):
        self.policy = dict(policy)
        self.runtime_root = Path(runtime_root)
        self.environ = dict(os.environ if environ is None else environ)
        self.executable = shutil.which("podman")

    def _run(self, args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            text=True,
            encoding="utf-8",
            errors="strict",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )

    def _image(self) -> str:
        variable = str(self.policy["podman"]["image_environment_variable"])
        return str(self.environ.get(variable, "")).strip()

    def probe(self) -> RuntimeProviderProbe:
        reasons: list[str] = []
        evidence: dict[str, Any] = {
            "automatic_install": False,
            "automatic_pull": False,
            "network_policy": "DENY",
            "root_filesystem": "READ_ONLY",
        }
        image = self._image()
        if not self.executable:
            reasons.append("PODMAN_EXECUTABLE_NOT_FOUND")
        if not image:
            reasons.append("PODMAN_DIGEST_BOUND_IMAGE_NOT_CONFIGURED")
        elif "@sha256:" not in image.lower():
            reasons.append("PODMAN_IMAGE_NOT_DIGEST_BOUND")
        if reasons:
            return RuntimeProviderProbe(
                self.provider_id, self.provider_version, False, True, False,
                tuple(reasons), evidence,
            )
        try:
            version = self._run([self.executable, "version", "--format", "json"], timeout=15)
            info = self._run([self.executable, "info", "--format", "json"], timeout=15)
            inspect = self._run(
                [self.executable, "image", "inspect", image, "--format", "json"],
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            reasons.append("PODMAN_PROBE_FAILED:" + type(exc).__name__)
            return RuntimeProviderProbe(
                self.provider_id, self.provider_version, False, True, False,
                tuple(reasons), evidence,
            )
        if version.returncode or info.returncode or inspect.returncode:
            reasons.append("PODMAN_MACHINE_OR_LOCAL_IMAGE_UNAVAILABLE")
        try:
            info_obj = json.loads(info.stdout or "{}")
        except json.JSONDecodeError:
            info_obj = {}
            reasons.append("PODMAN_INFO_JSON_INVALID")
        host = info_obj.get("host") or info_obj.get("Host") or {}
        security = host.get("security") or host.get("Security") or {}
        rootless = security.get("rootless")
        if rootless is None:
            rootless = security.get("Rootless")
        host_os = str(host.get("os") or host.get("OS") or "").lower()
        if rootless is not True:
            reasons.append("PODMAN_CONNECTION_NOT_ROOTLESS")
        if host_os and host_os != "linux":
            reasons.append("PODMAN_MACHINE_SERVER_NOT_LINUX")
        digest = image.lower().partition("@sha256:")[2]
        if digest and digest not in (inspect.stdout or "").lower():
            reasons.append("PODMAN_LOCAL_IMAGE_DIGEST_MISMATCH")
        evidence.update({
            "image": image,
            "rootless": rootless is True,
            "server_os": host_os or "unknown",
            "version_probe_sha256": _sha((version.stdout or "").encode("utf-8")),
            "image_inspect_sha256": _sha((inspect.stdout or "").encode("utf-8")),
        })
        available = not reasons
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            available,
            True,
            available,
            tuple(reasons),
            evidence,
        )

    def execution_command(self, image: str) -> list[str]:
        p = self.policy["execution_limits"]
        return [
            str(self.executable), "run", "--pull=never", "--rm",
            "--network=none", "--read-only", "--cap-drop=all",
            "--security-opt=no-new-privileges", "--pids-limit", str(p["pids"]),
            "--memory", f"{int(p['memory_megabytes'])}m",
            "--cpus", str(p["cpus"]), "--user", "65534:65534",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m",
            "-i", image, "python3", "-I", "-B", "-",
        ]

    def execute(self, source: str, request: dict[str, Any]) -> dict[str, Any]:
        probe = self.probe()
        if not probe.execution_enabled:
            raise PermissionError("PODMAN_RUNTIME_NOT_ADMITTED:" + ",".join(probe.reasons))
        harness = build_adapter_harness(source, request)
        command = self.execution_command(self._image())
        started = time.monotonic()
        try:
            cp = self._run(
                command,
                input=harness,
                timeout=float(self.policy["execution_limits"]["timeout_seconds"]),
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            cp = subprocess.CompletedProcess(command, 124, exc.stdout or "", exc.stderr or "")
            timed_out = True
        elapsed = round(time.monotonic() - started, 6)
        stdout = cp.stdout or ""
        stderr = cp.stderr or ""
        if len(stdout.encode("utf-8")) > int(self.policy["execution_limits"]["stdout_bytes"]):
            raise RuntimeError("PODMAN_STDOUT_LIMIT_EXCEEDED")
        if len(stderr.encode("utf-8")) > int(self.policy["execution_limits"]["stderr_bytes"]):
            raise RuntimeError("PODMAN_STDERR_LIMIT_EXCEEDED")
        if timed_out:
            raise TimeoutError("PODMAN_CANDIDATE_TIMEOUT")
        if cp.returncode:
            raise RuntimeError(f"PODMAN_CANDIDATE_EXIT_{cp.returncode}:{stderr[-1000:]}")
        lines = [line for line in stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("PODMAN_CANDIDATE_RESULT_MISSING")
        result = json.loads(lines[-1])
        return {
            "provider": probe.to_dict(),
            "boundary_result": result,
            "exit_code": cp.returncode,
            "elapsed_seconds": elapsed,
            "timed_out": False,
            "stdout_sha256": _sha(stdout.encode("utf-8")),
            "stderr_sha256": _sha(stderr.encode("utf-8")),
            "command_policy": {
                "pull": "never", "network": "none", "rootfs": "read_only",
                "capabilities": "drop_all", "no_new_privileges": True,
                "host_mounts": False,
            },
        }


class WindowsSandboxRuntimeProvider:
    provider_id = "microsoft.windows_sandbox.hardened"
    provider_version = "1.0.0"

    def __init__(self, policy: Mapping[str, Any], runtime_root: Path):
        self.policy = dict(policy)
        self.runtime_root = Path(runtime_root)
        self.executable = shutil.which("WindowsSandbox.exe") if os.name == "nt" else None

    def probe(self) -> RuntimeProviderProbe:
        reasons: list[str] = []
        python_root = Path(sys.base_prefix).resolve()
        python_exe = Path(sys.executable).resolve()
        try:
            python_relative = str(python_exe.relative_to(python_root)).replace("/", "\\")
        except ValueError:
            python_relative = ""
            reasons.append("PYTHON_EXECUTABLE_OUTSIDE_BASE_PREFIX")
        if os.name != "nt":
            reasons.append("WINDOWS_SANDBOX_REQUIRES_WINDOWS")
        if not self.executable:
            reasons.append("WINDOWS_SANDBOX_EXECUTABLE_NOT_FOUND")
        if not python_root.is_dir() or not python_exe.is_file():
            reasons.append("MAPPABLE_PYTHON_RUNTIME_NOT_FOUND")
        evidence = {
            "automatic_install": False,
            "networking": "Disable",
            "clipboard_redirection": "Disable",
            "printer_redirection": "Disable",
            "audio_input": "Disable",
            "video_input": "Disable",
            "vGPU": "Disable",
            "protected_client": "Enable",
            "input_mapping": "READ_ONLY",
            "output_mapping": "EPHEMERAL_OUTSIDE_REPOSITORY",
            "python_relative_path": python_relative,
        }
        available = not reasons
        return RuntimeProviderProbe(
            self.provider_id,
            self.provider_version,
            available,
            True,
            available,
            tuple(reasons),
            evidence,
        )

    def build_wsb_config(self, input_dir: Path, output_dir: Path, python_root: Path) -> str:
        memory = int(self.policy["execution_limits"]["memory_megabytes"])
        return (
            "<Configuration>\n"
            "  <VGpu>Disable</VGpu>\n"
            "  <Networking>Disable</Networking>\n"
            "  <AudioInput>Disable</AudioInput>\n"
            "  <VideoInput>Disable</VideoInput>\n"
            "  <ProtectedClient>Enable</ProtectedClient>\n"
            "  <PrinterRedirection>Disable</PrinterRedirection>\n"
            "  <ClipboardRedirection>Disable</ClipboardRedirection>\n"
            f"  <MemoryInMB>{memory}</MemoryInMB>\n"
            "  <MappedFolders>\n"
            f"    <MappedFolder><HostFolder>{xml_escape(str(input_dir))}</HostFolder><SandboxFolder>C:\\PhoenixInput</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>\n"
            f"    <MappedFolder><HostFolder>{xml_escape(str(output_dir))}</HostFolder><SandboxFolder>C:\\PhoenixOutput</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>\n"
            f"    <MappedFolder><HostFolder>{xml_escape(str(python_root))}</HostFolder><SandboxFolder>C:\\PhoenixPython</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>\n"
            "  </MappedFolders>\n"
            "  <LogonCommand><Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\PhoenixInput\\run.ps1</Command></LogonCommand>\n"
            "</Configuration>\n"
        )

    def execute(self, source: str, request: dict[str, Any]) -> dict[str, Any]:
        probe = self.probe()
        if not probe.execution_enabled:
            raise PermissionError("WINDOWS_SANDBOX_NOT_ADMITTED:" + ",".join(probe.reasons))
        execution_id = "WSB-" + uuid.uuid4().hex[:16].upper()
        root = self.runtime_root / "windows_sandbox" / execution_id
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir(parents=True, exist_ok=False)
        output_dir.mkdir(parents=True, exist_ok=False)
        harness = build_adapter_harness(source, request)
        (input_dir / "harness.py").write_text(harness, encoding="utf-8", newline="\n")
        python_root = Path(sys.base_prefix).resolve()
        python_relative = str(Path(sys.executable).resolve().relative_to(python_root)).replace("/", "\\")
        run_ps1 = (
            "$ErrorActionPreference='Stop'\n"
            "$out='C:\\PhoenixOutput\\stdout.txt'\n"
            "$err='C:\\PhoenixOutput\\stderr.txt'\n"
            f"$python='C:\\PhoenixPython\\{python_relative}'\n"
            "$lines=@(& $python -I -B 'C:\\PhoenixInput\\harness.py' 2> $err)\n"
            "$code=$LASTEXITCODE\n"
            "$utf8=New-Object System.Text.UTF8Encoding($false)\n"
            "[IO.File]::WriteAllLines($out,@($lines),$utf8)\n"
            "$wrapper=[ordered]@{schema='PHOENIX_PHASE9_WSB_WRAPPER_V1';exit_code=$code;completed=$true}\n"
            "[IO.File]::WriteAllText('C:\\PhoenixOutput\\wrapper.json',($wrapper|ConvertTo-Json -Compress),$utf8)\n"
            "if($code -eq 0 -and $lines.Count -gt 0){[IO.File]::WriteAllText('C:\\PhoenixOutput\\result.json',\"$($lines[-1])\",$utf8)}\n"
        )
        (input_dir / "run.ps1").write_text(run_ps1, encoding="utf-8-sig", newline="\r\n")
        config = self.build_wsb_config(input_dir, output_dir, python_root)
        config_path = root / "phase9.wsb"
        config_path.write_text(config, encoding="utf-8", newline="\r\n")
        timeout = float(self.policy["execution_limits"]["timeout_seconds"])
        started = time.monotonic()
        process = subprocess.Popen([str(self.executable), str(config_path)])
        wrapper_path = output_dir / "wrapper.json"
        result_path = output_dir / "result.json"
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline and not wrapper_path.is_file():
                if process.poll() is not None and not wrapper_path.is_file():
                    break
                time.sleep(0.2)
            if not wrapper_path.is_file():
                raise TimeoutError("WINDOWS_SANDBOX_CANDIDATE_TIMEOUT_OR_EARLY_EXIT")
            wrapper = json.loads(wrapper_path.read_text(encoding="utf-8-sig"))
            if int(wrapper.get("exit_code", -1)) != 0 or not result_path.is_file():
                stderr_path = output_dir / "stderr.txt"
                stderr = stderr_path.read_text(encoding="utf-8-sig") if stderr_path.is_file() else ""
                raise RuntimeError("WINDOWS_SANDBOX_CANDIDATE_FAILED:" + stderr[-1000:])
            result = json.loads(result_path.read_text(encoding="utf-8-sig"))
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
        elapsed = round(time.monotonic() - started, 6)
        stdout_path = output_dir / "stdout.txt"
        stderr_path = output_dir / "stderr.txt"
        stdout = stdout_path.read_bytes() if stdout_path.is_file() else b""
        stderr = stderr_path.read_bytes() if stderr_path.is_file() else b""
        if len(stdout) > int(self.policy["execution_limits"]["stdout_bytes"]):
            raise RuntimeError("WINDOWS_SANDBOX_STDOUT_LIMIT_EXCEEDED")
        if len(stderr) > int(self.policy["execution_limits"]["stderr_bytes"]):
            raise RuntimeError("WINDOWS_SANDBOX_STDERR_LIMIT_EXCEEDED")
        return {
            "provider": probe.to_dict(),
            "boundary_result": result,
            "exit_code": 0,
            "elapsed_seconds": elapsed,
            "timed_out": False,
            "stdout_sha256": _sha(stdout),
            "stderr_sha256": _sha(stderr),
            "command_policy": {
                "network": "disabled", "clipboard": "disabled",
                "input": "read_only", "output": "ephemeral_outside_repository",
                "protected_client": True,
            },
            "evidence_root": str(root),
        }


def select_runtime_provider(
    policy: Mapping[str, Any], runtime_root: Path
) -> IsolatedRuntimeProvider:
    reasons: list[str] = []
    podman = PodmanMachineRuntimeProvider(policy, runtime_root)
    podman_probe = podman.probe()
    if podman_probe.execution_enabled:
        return podman
    reasons.extend(podman_probe.reasons)
    sandbox = WindowsSandboxRuntimeProvider(policy, runtime_root)
    sandbox_probe = sandbox.probe()
    if sandbox_probe.execution_enabled:
        return sandbox
    reasons.extend(sandbox_probe.reasons)
    return DisabledRuntimeProvider(tuple(reasons))
