"""Durable stage state — atomic JSON write."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict

from .stage import StageStatus


class StateStore:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / "state.json"

    def load(self) -> Dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self, states: Dict[str, str]) -> None:
        """Atomic write: tmp → fsync → replace."""
        payload = json.dumps(states, indent=2, sort_keys=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.state_dir), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def set_status(self, name: str, status: StageStatus) -> Dict[str, str]:
        states = self.load()
        states[name] = status.value
        self.save(states)
        return states

    def get_status(self, name: str) -> str:
        return self.load().get(name, StageStatus.PENDING.value)
