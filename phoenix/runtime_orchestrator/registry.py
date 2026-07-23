"""Plugin and engine registry for Phoenix runtimes."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import importlib.util
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class EngineDescriptor:
    engine_id: str
    version: str
    python_module: str
    required: bool = False


@dataclass(frozen=True)
class EngineHealth:
    engine_id: str
    version: str
    status: str
    details: str


class EngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, EngineDescriptor] = {}

    def register(self, descriptor: EngineDescriptor) -> None:
        if descriptor.engine_id in self._engines:
            raise ValueError(
                f"Engine already registered: {descriptor.engine_id}"
            )
        self._engines[descriptor.engine_id] = descriptor

    def register_many(
        self,
        descriptors: Iterable[EngineDescriptor],
    ) -> None:
        for descriptor in descriptors:
            self.register(descriptor)

    def health(self) -> tuple[EngineHealth, ...]:
        results = []
        for descriptor in sorted(
            self._engines.values(),
            key=lambda item: item.engine_id,
        ):
            available = (
                importlib.util.find_spec(descriptor.python_module)
                is not None
            )
            results.append(
                EngineHealth(
                    engine_id=descriptor.engine_id,
                    version=descriptor.version,
                    status="healthy" if available else "unavailable",
                    details=descriptor.python_module,
                )
            )
        return tuple(results)

    def required_engines_available(self) -> bool:
        health_map = {
            item.engine_id: item.status
            for item in self.health()
        }
        return all(
            not descriptor.required
            or health_map[descriptor.engine_id] == "healthy"
            for descriptor in self._engines.values()
        )

    def to_dict(self) -> dict:
        return {
            "engines": [
                asdict(item)
                for item in sorted(
                    self._engines.values(),
                    key=lambda value: value.engine_id,
                )
            ],
            "health": [
                asdict(item)
                for item in self.health()
            ],
        }

    def write(self, destination: str | Path) -> Path:
        path = Path(destination).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path
