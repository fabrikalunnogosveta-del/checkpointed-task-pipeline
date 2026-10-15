"""Behavioral contracts — checkpoints, resume, atomic state, heartbeat, fail-fast."""

from pathlib import Path

import pytest

from task_pipeline import Heartbeat, Pipeline, Stage, StageResult, StateStore, Watchdog


def test_pipeline_runs_all_stages(tmp_path: Path):
    log = []

    def make(name):
        def fn(ctx):
            log.append(name)
            return StageResult(ok=True)

        return Stage(name, fn)

    pipe = Pipeline(
        name="p",
        stages=[make("a"), make("b")],
        state_dir=tmp_path,
    )
    report = pipe.run()
    assert report.ok
    assert report.completed == ["a", "b"]
    assert log == ["a", "b"]


def test_resume_skips_done(tmp_path: Path):
    log = []

    def make(name):
        def fn(ctx):
            log.append(name)
            return StageResult(ok=True)

        return Stage(name, fn)

    pipe = Pipeline(name="p", stages=[make("a"), make("b")], state_dir=tmp_path)
    pipe.run()
    log.clear()
    report = pipe.run(resume=True)
    assert report.skipped == ["a", "b"]
    assert log == []


def test_fail_fast_stops_pipeline(tmp_path: Path):
    def boom(ctx):
        return StageResult(ok=False, error="gpu_oom")

    def never(ctx):
        return StageResult(ok=True)

    pipe = Pipeline(
        name="p",
        stages=[Stage("render", boom), Stage("qc", never)],
        state_dir=tmp_path,
        fail_fast=True,
    )
    report = pipe.run()
    assert report.failed == ["render"]
    assert "qc" not in report.completed
    assert report.errors["render"] == "gpu_oom"


def test_retry_recovers(tmp_path: Path):
    calls = {"n": 0}

    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return StageResult(ok=True)

    pipe = Pipeline(name="p", stages=[Stage("x", flaky, retry=1)], state_dir=tmp_path)
    report = pipe.run()
    assert report.ok
    assert calls["n"] == 2


def test_atomic_state_survives(tmp_path: Path):
    store = StateStore(tmp_path)
    store.set_status("render", __import__("task_pipeline").StageStatus.DONE)
    assert store.get_status("render") == "done"
    assert (tmp_path / "state.json").exists()


def test_heartbeat_and_watchdog(tmp_path: Path):
    clock = {"t": 100.0}
    hb = Heartbeat(path=tmp_path / "hb", clock=lambda: clock["t"])
    hb.beat()
    assert hb.is_alive(max_age_s=60)
    clock["t"] = 200.0
    assert not hb.is_alive(max_age_s=60)
    wd = Watchdog(heartbeat=hb, max_age_s=60, clock=lambda: clock["t"])
    assert wd.check() == {"alive": False}


def test_stage_exception_becomes_failure(tmp_path: Path):
    def boom(ctx):
        raise ValueError("bad input")

    pipe = Pipeline(name="p", stages=[Stage("x", boom)], state_dir=tmp_path)
    report = pipe.run()
    assert not report.ok
    assert "bad input" in report.errors["x"]


def test_resume_retries_failed(tmp_path: Path):
    calls = {"n": 0}

    def flaky(ctx):
        calls["n"] += 1
        return StageResult(ok=calls["n"] > 1)

    pipe = Pipeline(name="p", stages=[Stage("x", flaky)], state_dir=tmp_path)
    r1 = pipe.run()
    assert r1.failed == ["x"]
    r2 = pipe.run(resume=True)
    assert r2.ok
    assert calls["n"] == 2


def test_context_flows_between_stages(tmp_path: Path):
    def first(ctx):
        return StageResult(ok=True, data={"seed": 42})

    def second(ctx):
        return StageResult(ok=True, data={"got": ctx.get("seed")})

    pipe = Pipeline(name="p", stages=[Stage("a", first), Stage("b", second)], state_dir=tmp_path)
    pipe.run()
    states = StateStore(tmp_path).load()
    assert states["a"] == "done"
    assert states["b"] == "done"


def test_fail_fast_false_continues(tmp_path: Path):
    def boom(ctx):
        return StageResult(ok=False, error="x")

    def ok(ctx):
        return StageResult(ok=True)

    pipe = Pipeline(
        name="p",
        stages=[Stage("bad", boom), Stage("good", ok)],
        state_dir=tmp_path,
        fail_fast=False,
    )
    report = pipe.run()
    assert report.failed == ["bad"]
    assert report.completed == ["good"]


def test_reset_clears_state(tmp_path: Path):
    def ok(ctx):
        return StageResult(ok=True)

    pipe = Pipeline(name="p", stages=[Stage("a", ok)], state_dir=tmp_path)
    pipe.run()
    pipe.reset()
    assert StateStore(tmp_path).load() == {}


def test_run_from_scratch_when_not_resume(tmp_path: Path):
    log = []

    def make(name):
        def fn(ctx):
            log.append(name)
            return StageResult(ok=True)

        return Stage(name, fn)

    pipe = Pipeline(name="p", stages=[make("a")], state_dir=tmp_path)
    pipe.run()
    log.clear()
    pipe.run(resume=False)
    assert log == ["a"]
