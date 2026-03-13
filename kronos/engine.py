"""
Kronos Engine — core time-compression logic.
Zero external dependencies. Copy this file into any project.
"""

import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable, List, Optional, Tuple


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


class KronosCheck:
    """
    A single preflight check.

    Pass a zero-argument callable that returns (status, detail):
        status : "ok" | "warn" | "fail"
        detail : short string shown in the preflight table

    Example
    -------
    >>> def check_db():
    ...     import sqlite3, pathlib
    ...     if not pathlib.Path("myapp.db").exists():
    ...         return "fail", "myapp.db not found"
    ...     return "ok", "database reachable"
    ...
    >>> KronosCheck("Database", check_db)
    """

    def __init__(self, label: str, func: Callable):
        self.label = label
        self.func = func

    def run(self) -> Tuple[str, str, str]:
        """Returns (label, status, detail)."""
        try:
            status, detail = self.func()
            return self.label, status, str(detail)
        except Exception as exc:
            return self.label, "fail", str(exc)


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

    Adding preflight checks
    -----------------------
    >>> def check_api():
    ...     r = requests.get("https://api.example.com/ping", timeout=5)
    ...     return ("ok", "reachable") if r.ok else ("fail", f"HTTP {r.status_code}")
    ...
    >>> k.add_check("API", check_api)
    >>> k.run()   # preflight runs automatically before simulation
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
        self.checks: List[KronosCheck] = []
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

    def add_check(self, label: str, func: Callable) -> "Kronos":
        """
        Register a preflight check. func() must return (status, detail).
        status: 'ok' | 'warn' | 'fail'
        Returns self for chaining.
        """
        self.checks.append(KronosCheck(label, func))
        return self

    # ── preflight ─────────────────────────────────────────────

    def preflight(self, ask: bool = True) -> bool:
        """
        Run all registered preflight checks.
        Prints a status table and optionally asks the user to confirm.

        Parameters
        ----------
        ask : bool
            If True, prompt the user before returning True.
            Set to False in automated/CI environments.

        Returns
        -------
        bool — True to proceed, False to abort.
        """
        if not self.checks:
            return True     # nothing to check, proceed

        results = [c.run() for c in self.checks]
        fatals  = sum(1 for _, s, _ in results if s == "fail")
        warns   = sum(1 for _, s, _ in results if s == "warn")

        ICON = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}
        W    = 42
        SEP  = "─" * 62

        print()
        print(f"  ┌{SEP}┐")
        print(f"  │  {'KRONOS PREFLIGHT':<60}│")
        print(f"  ├{SEP}┤")

        for label, status, detail in results:
            icon = ICON.get(status, "  ")
            pad  = 20 - len(label)
            print(f"  │  {icon}  {label}{' ' * pad}{detail[:W]:<{W}}│")

        print(f"  ├{SEP}┤")

        if fatals == 0 and warns == 0:
            print(f"  │  {'All systems go — ready to simulate.':<60}│")
            verdict = "go"
        elif fatals == 0:
            print(f"  │  {f'{warns} warning(s) — some features may be limited.':<60}│")
            verdict = "warn"
        else:
            print(f"  │  {f'{fatals} critical issue(s) — fix before running.':<60}│")
            verdict = "fail"

        print(f"  └{SEP}┘")
        print()

        if verdict == "fail":
            print("  ❌  Preflight failed. Fix the issues above and try again.\n")
            return False

        if not ask:
            return True

        if verdict == "warn":
            print("  ⚠️   Some features will be limited.\n")

        try:
            answer = input("  Proceed with simulation? [Y/n] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n  Aborted.")
            return False

        if answer in ("", "y", "yes"):
            print()
            return True

        print("\n  Simulation cancelled.\n")
        return False

    # ── execution ─────────────────────────────────────────────

    def run(self, skip_preflight: bool = False) -> dict:
        """
        Run the simulation. Blocks until all events fire or real time expires.

        Parameters
        ----------
        skip_preflight : bool
            Skip preflight checks (useful in tests or CI).

        Returns
        -------
        dict — {total, success, failed, elapsed_seconds, errors}
        """
        if not skip_preflight and self.checks:
            if not self.preflight():
                return {"total": 0, "success": 0, "failed": 0,
                        "elapsed_seconds": 0, "errors": [], "aborted": True}

        self.events.sort(key=lambda e: e.sim_offset_seconds)
        self.errors = []
        self._start_time = time.time()

        self._print_banner()

        success = 0
        for event in self.events:
            real_delay = event.sim_offset_seconds / self.compression_ratio
            fire_at    = self._start_time + real_delay
            wait       = fire_at - time.time()
            if wait > 0:
                time.sleep(wait)
            if self._fire(event):
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
            real_ts   = str(timedelta(seconds=int(real_secs)))
            print(f"  {sim_date:<14} {real_ts:>10}   {ev.description}")

        print(f"\n  Total: {len(self.events)} events over {self.sim_days} days "
              f"({self.real_minutes} real minutes)\n")

    # ── internals ─────────────────────────────────────────────

    def _fire(self, event: KronosEvent) -> bool:
        sim_date = self._sim_date(event)
        elapsed  = time.time() - self._start_time
        real_ts  = str(timedelta(seconds=int(elapsed)))
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

    def _print_banner(self):
        ratio  = self.compression_ratio
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
        if summary.get("errors"):
            print("  ⚠  Errors:")
            for e in summary["errors"]:
                print(f"     Day {e['sim_day']} [{e['sim_date']}] — {e['description']}")
                print(f"     {e['error']}")
            print()
