"""
Kronos Engine — core time-compression logic.
Zero external dependencies. Copy this file into any project.
"""

import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable, List, Optional


class KronosEvent:
    """A single scheduled event in the simulation."""

    def __init__(
        self,
        sim_day: int,
        sim_hour: float,
        description: str,
        func: Callable,
    ):
        self.sim_day = sim_day
        self.sim_hour = sim_hour
        self.description = description
        self.func = func

    @property
    def sim_offset_seconds(self) -> float:
        """Seconds from sim-start when this event occurs."""
        return (self.sim_day * 86400) + (self.sim_hour * 3600)

    def __repr__(self):
        return f"KronosEvent(day={self.sim_day}, hour={self.sim_hour:.1f}, desc={self.description!r})"


class Kronos:
    """
    Time-compression engine.

    Maps N simulated days onto M real minutes.
    Events fire at proportionally compressed intervals.

    Example
    -------
    >>> k = Kronos(real_minutes=60, sim_days=32)
    >>> k.schedule(day=1, hour=9, description="User signs up", func=my_signup_fn)
    >>> k.run()
    """

    def __init__(
        self,
        real_minutes: float = 60,
        sim_days: int = 32,
        label: str = "KRONOS",
        on_event: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ):
        self.real_minutes = real_minutes
        self.sim_days = sim_days
        self.label = label
        self.on_event = on_event    # callback(event, sim_date) after each success
        self.on_error = on_error    # callback(event, sim_date, exc) on failure

        self.real_secs = real_minutes * 60
        self.total_sim_secs = sim_days * 86400
        self.events: List[KronosEvent] = []
        self.errors: List[dict] = []
        self.state: dict = {}

        self._start_time: Optional[float] = None

    # ── properties ────────────────────────────────────────────

    @property
    def compression_ratio(self) -> float:
        """How many simulated seconds per real second."""
        return self.total_sim_secs / self.real_secs

    @property
    def seconds_per_sim_day(self) -> float:
        return self.real_secs / self.sim_days

    # ── scheduling ────────────────────────────────────────────

    def schedule(
        self,
        day: int,
        hour: float,
        description: str,
        func: Callable,
    ) -> "Kronos":
        """Add an event to the timeline. Returns self for chaining."""
        self.events.append(KronosEvent(day, hour, description, func))
        self.events.sort(key=lambda e: e.sim_offset_seconds)
        return self

    # ── execution ─────────────────────────────────────────────

    def run(self) -> dict:
        """
        Run the simulation. Blocks until all events have fired or real time expires.
        Returns a summary dict: {total, success, failed, errors}.
        """
        self.events.sort(key=lambda e: e.sim_offset_seconds)
        self.errors = []
        self._start_time = time.time()

        self._print_banner()

        success = 0
        for event in self.events:
            real_delay = event.sim_offset_seconds / self.compression_ratio
            fire_at = self._start_time + real_delay
            wait = fire_at - time.time()
            if wait > 0:
                time.sleep(wait)
            result = self._fire(event)
            if result:
                success += 1

        elapsed = time.time() - self._start_time
        summary = {
            "total": len(self.events),
            "success": success,
            "failed": len(self.errors),
            "elapsed_seconds": round(elapsed, 1),
            "errors": self.errors,
        }
        self._print_done(elapsed, summary)
        return summary

    def preview(self) -> None:
        """Print the full event timeline without executing anything."""
        self.events.sort(key=lambda e: e.sim_offset_seconds)
        ratio = self.compression_ratio
        print(f"\n  Kronos — {self.sim_days} sim-days in {self.real_minutes} real-minutes")
        print(f"  Compression: {ratio:.0f}x  |  Events: {len(self.events)}\n")
        print(f"  {'SIM DATE':<14} {'REAL TIME':>10}   DESCRIPTION")
        print("  " + "─" * 62)

        for ev in self.events:
            sim_date = self._sim_date(ev)
            real_secs = ev.sim_offset_seconds / ratio
            real_ts = str(timedelta(seconds=int(real_secs)))
            print(f"  {sim_date:<14} {real_ts:>10}   {ev.description}")

        print(f"\n  Total: {len(self.events)} events over {self.sim_days} days "
              f"({self.real_minutes} real minutes)\n")

    # ── internals ─────────────────────────────────────────────

    def _fire(self, event: KronosEvent) -> bool:
        sim_date = self._sim_date(event)
        elapsed = time.time() - self._start_time
        real_ts = str(timedelta(seconds=int(elapsed)))
        print(f"  [{real_ts}] Day {event.sim_day:>2} {sim_date}  ▶  {event.description}")

        try:
            Thread(target=event.func, daemon=True).start()
            if self.on_event:
                self.on_event(event, sim_date)
            return True
        except Exception as exc:
            err = {
                "sim_day": event.sim_day,
                "sim_date": sim_date,
                "description": event.description,
                "error": str(exc),
            }
            self.errors.append(err)
            print(f"  ⚠  ERROR on day {event.sim_day}: {exc}")
            if self.on_error:
                self.on_error(event, sim_date, exc)
            return False

    def _sim_date(self, event: KronosEvent) -> str:
        base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (base + timedelta(days=event.sim_day)).strftime("%d %b %Y")

    def _real_time_for_event(self, event: KronosEvent) -> str:
        if self._start_time is None:
            return "--:--:--"
        fire_at = self._start_time + event.sim_offset_seconds / self.compression_ratio
        return datetime.fromtimestamp(fire_at).strftime("%H:%M:%S")

    def _print_banner(self):
        ratio = self.compression_ratio
        finish = datetime.now() + timedelta(minutes=self.real_minutes)
        print()
        print("  ┌" + "─" * 54 + "┐")
        print(f"  │  {self.label:<52}│")
        print("  ├" + "─" * 54 + "┤")
        print(f"  │  Sim days   : {self.sim_days:<38}│")
        print(f"  │  Real time  : {self.real_minutes} minutes{'':<31}│")
        print(f"  │  Ratio      : {ratio:.0f}x compression{'':<28}│")
        print(f"  │  Events     : {len(self.events):<38}│")
        print(f"  │  Finishes   : {finish.strftime('%H:%M:%S'):<38}│")
        print("  └" + "─" * 54 + "┘")
        print()

    def _print_done(self, elapsed: float, summary: dict):
        m, s = divmod(int(elapsed), 60)
        print()
        print("  ┌" + "─" * 54 + "┐")
        print(f"  │  ✅  Run complete{'':<36}│")
        print(f"  │  Duration : {m}m {s}s{'':<38}│")
        print(f"  │  Total    : {summary['total']:<40}│")
        print(f"  │  Success  : {summary['success']:<40}│")
        print(f"  │  Failed   : {summary['failed']:<40}│")
        print("  └" + "─" * 54 + "┘")
        print()
        if summary["errors"]:
            print("  ⚠  Errors:")
            for e in summary["errors"]:
                print(f"     Day {e['sim_day']} [{e['sim_date']}] — {e['description']}")
                print(f"     {e['error']}")
            print()
