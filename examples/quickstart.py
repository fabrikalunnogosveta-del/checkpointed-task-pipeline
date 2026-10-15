"""Quickstart — run, crash-resume, no GPU required."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from task_pipeline import Pipeline, Stage, StageResult


def main() -> None:
    state = Path(__file__).parent / "_state_demo"

    def research(ctx):
        return StageResult(ok=True, data={"topics": 10})

    def render(ctx):
        return StageResult(ok=True, data={"frames": 1000})

    def qc(ctx):
        return StageResult(ok=True)

    pipe = Pipeline(
        name="demo",
        stages=[Stage("research", research), Stage("render", render), Stage("qc", qc)],
        state_dir=state,
    )
    r1 = pipe.run()
    print("run1:", r1.completed, "ok=", r1.ok)

    r2 = pipe.run(resume=True)
    print("run2 (resume):", "skipped=", r2.skipped)


if __name__ == "__main__":
    main()
