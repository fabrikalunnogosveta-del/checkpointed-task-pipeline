# checkpointed-task-pipeline

**Checkpointed orchestration for long jobs — resume after crash, never lose 3 hours of GPU work.**

**This is the solution, not the problem.** Long-running pipelines die on OOM, timeouts,
and power blips. This library makes **progress durable** and **restarts cheap**.

[![CI](https://github.com/fabrikalunnogosveta-del/checkpointed-task-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/fabrikalunnogosveta-del/checkpointed-task-pipeline/actions)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-12%20passed-brightgreen)

---

## The problem we solved

| Problem (before) | Solution (this library) |
|---|---|
| Crash at 95% → restart from zero | **Checkpoint after each stage** |
| Hung worker looks “busy” forever | **Heartbeat + watchdog** |
| Retry duplicates side effects | **Idempotent stage contract** |
| No idea where it died | **Stage status file** (done / failed / pending) |
| Hard-coded sequential script | **Pipeline** of named stages |
| One poison task kills the run | **Fail-fast policy** + skip vs abort |

**Rule:** *checkpoint I/O is cheap. Re-running 3 hours of GPU is not.*

---

## Architecture

```
Pipeline
  ├── Stage("research")   → run → checkpoint
  ├── Stage("render")     → run → checkpoint
  ├── Stage("qc")         → run → checkpoint
  └── Stage("publish")    → run → done

state.json  (atomic write)
  {"research": "done", "render": "failed", "qc": "pending"}

resume() → skip "done", retry "failed", run "pending"
```

---

## How this maps to real jobs

| Job title | What this repo proves |
|---|---|
| **AI / ML Platform Engineer** | long GPU jobs survive crashes |
| **Data / Pipeline Engineer** | staged orchestration + resume |
| **Reliability / LLM Ops** | heartbeat, watchdog, idempotent stages |
| **Backend Python** | atomic state, clear stage contracts |

---

## Install

```bash
git clone https://github.com/fabrikalunnogosveta-del/checkpointed-task-pipeline.git
cd checkpointed-task-pipeline
pip install -r requirements.txt
```

## Quickstart

```python
from pathlib import Path
from task_pipeline import Pipeline, Stage, StageResult

def research(ctx):
    return StageResult(ok=True, data={"topics": 10})

def render(ctx):
    # pretend GPU work
    return StageResult(ok=True, data={"frames": 1000})

pipe = Pipeline(
    name="video",
    stages=[Stage("research", research), Stage("render", render)],
    state_dir=Path("./state"),
)
report = pipe.run()
print(report.completed)  # ["research", "render"]

# After crash — resume without redoing finished stages
report2 = pipe.run(resume=True)
```

---

## Testing philosophy

- completed stages are **not re-run** on resume
- failed stage can be retried
- atomic state write survives kill mid-run
- heartbeat marks liveness
- pipeline reports stage-by-stage status

```bash
python -m pytest tests/ -q
```

---

## Production context

Pattern extracted from a **59-phase multi-agent production pipeline** (GPU rendering,
watchdog, retries, checkpointing). This repo is the **standalone orchestration core**.

---

## Related

- [guards-and-laws](https://github.com/fabrikalunnogosveta-del/guards-and-laws)
- [structured-llm-output-guard](https://github.com/fabrikalunnogosveta-del/structured-llm-output-guard)
- [humanlike-browser-engine](https://github.com/fabrikalunnogosveta-del/humanlike-browser-engine)
- [deliverability-toolkit](https://github.com/fabrikalunnogosveta-del/deliverability-toolkit)

---

## License

MIT

## Author

**Maxim Parshshin** — AI/LLM systems, pipelines, reliability. Remote contracts.
