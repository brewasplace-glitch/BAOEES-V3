from __future__ import annotations
import json
from pathlib import Path
import re

def _identifier(value: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    if not result:
        raise ValueError("Invalid function name.")
    return ("f_" + result) if result[0].isdigit() else result

def generate_domain_scaffolding(
    repository_root: Path,
    domain: str,
    output_root: Path,
    limit: int | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict:
    repository_root = repository_root.resolve()
    registry_path = repository_root / "engineering_kernel/specification/functions/function_registry.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    selected = [x for x in data["functions"] if x.get("domain") == domain.upper()]
    if not selected:
        raise ValueError(f"Unknown or empty domain: {domain}")
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        selected = selected[:limit]

    target_root = repository_root / output_root / domain.lower()
    created, skipped = [], 0
    for item in selected:
        target = target_root / (item["id"].lower().replace("-", "_") + ".py")
        if target.exists() and not overwrite:
            skipped += 1
            continue
        created.append(target.relative_to(repository_root).as_posix())
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            name = _identifier(item["name"])
            content = (
                '"""Generated PEK scaffold for ' + item["id"] + '."""\n\n'
                'def ' + name + '(*args, **kwargs):\n'
                '    """' + item.get("purpose", "Generated function.") + '"""\n'
                '    raise NotImplementedError("' + item["id"] + ' is not implemented.")\n'
            )
            target.write_text(content, encoding="utf-8", newline="\n")
    return {
        "domain": domain.upper(), "selected": len(selected),
        "created": len(created), "skipped": skipped,
        "dry_run": dry_run, "files": created
    }
