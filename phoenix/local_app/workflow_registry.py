"""Allow-listed Phoenix workflow registry."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RuntimeJob


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WorkflowRegistry:
    def __init__(self, repository: Path, config: dict[str, Any]):
        self.repository = repository.resolve()
        self.config = config
        self.runtime_root = self.repository / config["runtime_root"]
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, RuntimeJob] = {}
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    def describe(self) -> list[dict[str, Any]]:
        result = []
        for workflow in self.config["workflows"]:
            available = all(
                (self.repository / relative).is_file()
                for relative in workflow.get("required_files", [])
            )
            result.append({
                "id": workflow["id"],
                "label": workflow["label"],
                "available": available,
                "disabled_reason": (
                    None if available else workflow.get(
                        "disabled_reason",
                        "Benodigde runner ontbreekt.",
                    )
                ),
            })
        return result

    def start(self, workflow_id: str) -> RuntimeJob:
        workflow = next(
            (item for item in self.config["workflows"] if item["id"] == workflow_id),
            None,
        )
        if workflow is None:
            raise KeyError(f"Onbekende workflow: {workflow_id}")
        if not all(
            (self.repository / relative).is_file()
            for relative in workflow.get("required_files", [])
        ):
            raise RuntimeError(
                workflow.get("disabled_reason", "Benodigde runner ontbreekt.")
            )

        with self._lock:
            if self._active_job_id is not None:
                active = self._jobs.get(self._active_job_id)
                if active and active.status in {"QUEUED", "RUNNING"}:
                    raise RuntimeError(
                        f"Er draait al een Phoenix-workflow: {active.job_id}"
                    )
            job_id = uuid.uuid4().hex[:12]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = (
                self.runtime_root
                / workflow["output_subdir"]
                / f"{timestamp}_{job_id}"
            )
            output_dir.mkdir(parents=True, exist_ok=False)
            log_path = output_dir / "workflow.log"
            command = [
                sys.executable,
                str(self.repository / workflow["runner"]),
                "--output-dir",
                str(output_dir / "result"),
                workflow["expect_flag"],
            ]
            job = RuntimeJob(
                job_id=job_id,
                workflow_id=workflow_id,
                label=workflow["label"],
                status="QUEUED",
                started_at=utc_now(),
                output_dir=str(output_dir.relative_to(self.repository)),
                log_path=str(log_path.relative_to(self.repository)),
                command=command,
            )
            self._jobs[job_id] = job
            self._active_job_id = job_id
            self._persist(job)
            thread = threading.Thread(
                target=self._run,
                args=(job, log_path),
                daemon=True,
            )
            thread.start()
            return job

    def latest(self) -> RuntimeJob | None:
        if not self._jobs:
            return self._load_latest()
        return sorted(
            self._jobs.values(),
            key=lambda item: item.started_at,
        )[-1]

    def get(self, job_id: str) -> RuntimeJob | None:
        return self._jobs.get(job_id)

    def _run(self, job: RuntimeJob, log_path: Path) -> None:
        job.status = "RUNNING"
        self._persist(job)
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            with log_path.open("w", encoding="utf-8", newline="\n") as log:
                log.write("PROJECT PHOENIX LOCAL WORKFLOW\n")
                log.write("Command: " + json.dumps(job.command) + "\n\n")
                log.flush()
                process = subprocess.Popen(
                    job.command,
                    cwd=self.repository,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    shell=False,
                )
                return_code = process.wait()
            job.return_code = return_code
            job.status = "PASSED" if return_code == 0 else "FAILED"
            if return_code != 0:
                job.error = f"Workflow stopte met exitcode {return_code}."
        except Exception as error:  # pragma: no cover - defensive runtime path
            job.status = "FAILED"
            job.error = str(error)
        finally:
            job.finished_at = utc_now()
            with self._lock:
                if self._active_job_id == job.job_id:
                    self._active_job_id = None
            self._persist(job)

    def _persist(self, job: RuntimeJob) -> None:
        destination = self.runtime_root / "jobs" / f"{job.job_id}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(job.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        latest = self.runtime_root / "latest_job.json"
        latest.write_text(
            json.dumps(job.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    def _load_latest(self) -> RuntimeJob | None:
        path = self.runtime_root / "latest_job.json"
        if not path.is_file():
            return None
        try:
            return RuntimeJob(**json.loads(path.read_text(encoding="utf-8")))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
