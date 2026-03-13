"""
Kronos engine tests.
"""
import time
import pytest
from kronos.engine import Kronos, KronosEvent, KronosCheck


# ── KronosEvent ───────────────────────────────────────────────────────────────

def test_event_offset_seconds():
    ev = KronosEvent(sim_day=1, sim_hour=6, description="test", func=lambda: None)
    assert ev.sim_offset_seconds == 1 * 86400 + 6 * 3600


def test_event_repr():
    ev = KronosEvent(1, 9.0, "signup", lambda: None)
    assert "day=1" in repr(ev)
    assert "signup" in repr(ev)


# ── Kronos properties ─────────────────────────────────────────────────────────

def test_compression_ratio():
    k = Kronos(real_minutes=60, sim_days=32)
    expected = (32 * 86400) / (60 * 60)
    assert k.compression_ratio == pytest.approx(expected)   # 768x


def test_seconds_per_sim_day():
    k = Kronos(real_minutes=60, sim_days=30)
    assert k.seconds_per_sim_day == pytest.approx((60 * 60) / 30)


# ── Scheduling ────────────────────────────────────────────────────────────────

def test_schedule_returns_self():
    k = Kronos(real_minutes=1, sim_days=1)
    result = k.schedule(0, 9, "test", lambda: None)
    assert result is k


def test_schedule_sorted():
    k = Kronos(real_minutes=10, sim_days=5)
    k.schedule(3, 9, "late",  lambda: None)
    k.schedule(1, 9, "early", lambda: None)
    k.schedule(2, 9, "mid",   lambda: None)
    offsets = [e.sim_offset_seconds for e in k.events]
    assert offsets == sorted(offsets)


def test_schedule_multiple_events():
    k = Kronos(real_minutes=1, sim_days=10)
    for i in range(5):
        k.schedule(i, 9, f"event {i}", lambda: None)
    assert len(k.events) == 5


# ── Preflight ─────────────────────────────────────────────────────────────────

def test_add_check_returns_self():
    k = Kronos(real_minutes=1, sim_days=1)
    result = k.add_check("test", lambda: ("ok", "all good"))
    assert result is k


def test_preflight_no_checks_returns_true():
    k = Kronos(real_minutes=1, sim_days=1)
    assert k.preflight(ask=False) is True


def test_preflight_all_ok(capsys):
    k = Kronos(real_minutes=1, sim_days=1)
    k.add_check("Alpha", lambda: ("ok", "working"))
    k.add_check("Beta",  lambda: ("ok", "working"))
    result = k.preflight(ask=False)
    assert result is True
    out = capsys.readouterr().out
    assert "✅" in out
    assert "All systems go" in out


def test_preflight_with_warning(capsys):
    k = Kronos(real_minutes=1, sim_days=1)
    k.add_check("Thing", lambda: ("warn", "degraded"))
    result = k.preflight(ask=False)
    assert result is True   # warns don't block
    out = capsys.readouterr().out
    assert "⚠" in out


def test_preflight_with_fatal(capsys):
    k = Kronos(real_minutes=1, sim_days=1)
    k.add_check("Thing", lambda: ("fail", "broken"))
    result = k.preflight(ask=False)
    assert result is False
    out = capsys.readouterr().out
    assert "❌" in out


def test_preflight_check_exception(capsys):
    def bad_check():
        raise RuntimeError("connection refused")

    k = Kronos(real_minutes=1, sim_days=1)
    k.add_check("Exploder", bad_check)
    result = k.preflight(ask=False)
    assert result is False   # exception → fail


# ── KronosCheck ───────────────────────────────────────────────────────────────

def test_kronos_check_ok():
    c = KronosCheck("DB", lambda: ("ok", "reachable"))
    label, status, detail = c.run()
    assert label == "DB"
    assert status == "ok"
    assert detail == "reachable"


def test_kronos_check_exception():
    def boom():
        raise ValueError("no connection")

    c = KronosCheck("DB", boom)
    label, status, detail = c.run()
    assert status == "fail"
    assert "no connection" in detail


# ── Run (fast micro-simulation) ───────────────────────────────────────────────

def test_run_fires_events():
    fired = []
    k = Kronos(real_minutes=0.05, sim_days=1)   # 3 real seconds
    k.schedule(0, 0,    "first",  lambda: fired.append("first"))
    k.schedule(0, 23.9, "last",   lambda: fired.append("last"))

    summary = k.run(skip_preflight=True)

    time.sleep(0.1)   # let daemon threads finish
    assert summary["total"] == 2
    assert summary["success"] == 2
    assert "first" in fired
    assert "last"  in fired


def test_run_returns_summary():
    k = Kronos(real_minutes=0.02, sim_days=1)
    k.schedule(0, 0, "ping", lambda: None)
    summary = k.run(skip_preflight=True)
    assert "total" in summary
    assert "success" in summary
    assert "failed" in summary
    assert "elapsed_seconds" in summary


def test_run_aborted_when_preflight_fails():
    k = Kronos(real_minutes=0.02, sim_days=1)
    k.add_check("Fatal", lambda: ("fail", "broken"))
    k.schedule(0, 0, "should not fire", lambda: (_ for _ in ()).throw(AssertionError("fired!")))
    summary = k.run(skip_preflight=False)
    assert summary.get("aborted") is True


def test_run_skip_preflight():
    """--skip-preflight bypasses even failing checks."""
    k = Kronos(real_minutes=0.02, sim_days=1)
    k.add_check("Fatal", lambda: ("fail", "broken"))
    k.schedule(0, 0, "event", lambda: None)
    summary = k.run(skip_preflight=True)
    assert summary["total"] == 1
