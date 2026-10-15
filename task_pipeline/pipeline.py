"""Pipeline — run stages with checkpoints and resume."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stage import Stage, StageResult, StageStatus
from .state import StateStore


@dataclass
class PipelineReport:
    completed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failed


@dataclass
class Pipeline:
    name: str
    stages: List[Stage]
    state_dir: Path
    fail_fast: bool = True

    def __post_init__(self) -> None:
        self._store = StateStore(self.state_dir)

    def run(self, resume: bool = True, ctx: Optional[Dict[str, Any]] = None) -> PipelineReport:
        report = PipelineReport()
        context: Dict[str, Any] = dict(ctx or {})
        context.setdefault("pipeline", self.name)

        for stage in self.stages:
            if resume and self._store.get_status(stage.name) == StageStatus.DONE.value:
                report.skipped.append(stage.name)
                continue

            self._store.set_status(stage.name, StageStatus.RUNNING)
            result: Optional[StageResult] = None
            attempts = 1 + max(0, stage.retry)
            for _ in range(attempts):
                result = stage.run(context)
                if result.ok:
                    break

            if result is not None and result.ok:
                self._store.set_status(stage.name, StageStatus.DONE)
                report.completed.append(stage.name)
                context.update(result.data or {})
            else:
                err = (result.error if result else "unknown") or "failed"
                self._store.set_status(stage.name, StageStatus.FAILED)
                report.failed.append(stage.name)
                report.errors[stage.name] = err
                if self.fail_fast:
                    return report

        return report

    def reset(self) -> None:
        self._store.save({})
