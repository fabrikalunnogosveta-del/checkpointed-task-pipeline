"""Heartbeat + watchdog — liveness without killing the pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional


@dataclass
class Heartbeat:
    """Write a timestamp file so a watchdog can see the job is alive."""

    path: Path
    clock: Callable[[], float] = time.time

    def beat(self) -> float:
        ts = self.clock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(ts), encoding="utf-8")
        return ts

    def last_beat(self) -> Optional[float]:
        if not self.path.exists():
            return None
        try:
            return float(self.path.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    def is_alive(self, max_age_s: float = 60.0) -> bool:
        last = self.last_beat()
        if last is None:
            return False
        return (self.clock() - last) <= max_age_s


@dataclass
class Watchdog:
    """Mark hung jobs when heartbeat is stale. Never raises."""

    heartbeat: Heartbeat
    max_age_s: float = 60.0
    clock: Callable[[], float] = time.time

    def check(self) -> Dict[str, bool]:
        return {"alive": self.heartbeat.is_alive(self.max_age_s)}
