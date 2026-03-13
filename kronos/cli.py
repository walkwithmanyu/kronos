"""
Kronos CLI — run a scenario file from the command line.

Usage:
    kronos run scenario.py --days 32 --minutes 60
    kronos preview scenario.py
    kronos preflight scenario.py
    kronos --help
"""

import argparse
import importlib.util
import sys
from .engine import Kronos


def load_scenario(path: str, k: Kronos):
    """Import a scenario file and call its build(k) function."""
    spec = importlib.util.spec_from_file_location("scenario", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "build"):
        print(f"ERROR: {path} must define a build(k: Kronos) function.")
        sys.exit(1)

    mod.build(k)


def main():
    parser = argparse.ArgumentParser(
        prog="kronos",
        description="Kronos — Compress time. Test everything.",
    )
    sub = parser.add_subparsers(dest="cmd")

    # ── run ──────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Run a scenario")
    run_p.add_argument("scenario",         help="Path to scenario .py file")
    run_p.add_argument("--days",           type=int,   default=32)
    run_p.add_argument("--minutes",        type=float, default=60)
    run_p.add_argument("--label",          type=str,   default="KRONOS")
    run_p.add_argument("--skip-preflight", action="store_true",
                       help="Skip preflight checks and run immediately")

    # ── preview ──────────────────────────────────────────────
    prev_p = sub.add_parser("preview", help="Preview event timeline without running")
    prev_p.add_argument("scenario", help="Path to scenario .py file")
    prev_p.add_argument("--days",    type=int,   default=32)
    prev_p.add_argument("--minutes", type=float, default=60)

    # ── preflight ─────────────────────────────────────────────
    pre_p = sub.add_parser("preflight", help="Run preflight checks only, don't simulate")
    pre_p.add_argument("scenario", help="Path to scenario .py file")
    pre_p.add_argument("--days",    type=int,   default=32)
    pre_p.add_argument("--minutes", type=float, default=60)

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return

    k = Kronos(
        real_minutes=args.minutes,
        sim_days=args.days,
        label=getattr(args, "label", "KRONOS"),
    )
    load_scenario(args.scenario, k)

    if args.cmd == "preview":
        k.preview()

    elif args.cmd == "preflight":
        k.preflight(ask=False)

    elif args.cmd == "run":
        skip = getattr(args, "skip_preflight", False)
        try:
            k.run(skip_preflight=skip)
        except KeyboardInterrupt:
            print("\n\n⏸  Kronos interrupted.")


if __name__ == "__main__":
    main()
