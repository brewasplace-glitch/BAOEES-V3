from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import json
from .engines import create_adapter

def execute_job(job_path: Path, dry_run: bool = False) -> dict:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    required = {"schema_version","job_id","engine_id","input_path","output_dir"}
    missing = sorted(required - set(job))
    if missing:
        raise ValueError("Missing job fields: " + ", ".join(missing))
    adapter = create_adapter(job["engine_id"])
    result = adapter.run(job, dry_run=dry_run)
    envelope = {
        "schema_version": "phoenix.engine-run-envelope/5.0.0",
        "job_id": job["job_id"],
        "engine": job["engine_id"],
        "result": asdict(result),
        "professional_review_required": True,
        "result_fabricated": False,
    }
    output = Path(job["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "phoenix_run_envelope.json").write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n"
    )
    return envelope
