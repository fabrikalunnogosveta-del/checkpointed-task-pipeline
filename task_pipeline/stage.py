"""Stage contract — one unit of work with a clear result."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class Stage:
    name: str
    fn: Callable[[Dict[str, Any]], StageResult]
    retry: int = 0

    def run(self, ctx: Dict[str, Any]) -> StageResult:
        try:
            return self.fn(ctx)
        except Exception as exc:  # noqa: BLE001 — stage errors become results
            return StageResult(ok=False, error=str(exc))
