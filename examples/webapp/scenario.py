"""
Kronos Example — Web App / SaaS Scenario
==========================================
Simulates 30 days of a SaaS product:
signups, onboarding, feature usage, upgrades, churn, and support tickets.

Uses DataFactory + KronosStore — generates real data, writes to SQLite.

To run:
    kronos preview examples/webapp/scenario.py --days 30 --minutes 45
    kronos run    examples/webapp/scenario.py --days 30 --minutes 45

After the run:
    sqlite3 kronos_test.db "SELECT name, plan, churned FROM kn_users;"

To wipe test data:
    python3 -c "from kronos.store import KronosStore; KronosStore().cleanup()"
"""

from kronos import Kronos
from kronos.factory import DataFactory
from kronos.store import KronosStore


def build(k: Kronos):
    f     = DataFactory(seed=99)
    store = KronosStore()
    uids  = {}   # index → user_id

    k.add_check("Database", lambda: ("ok", "kronos_test.db ready"))

    # Generate 10 users upfront
    users = f.saas_users(10)

    # ── Signups: days 0–7 ─────────────────────────────────────
    signup_days = [0, 0, 1, 1, 2, 3, 4, 5, 6, 7]
    for i, (u, day) in enumerate(zip(users, signup_days)):
        def _signup(i=i, u=u):
            uid = store.add_user(u)
            uids[i] = uid
            print(f"           👤 Signup: {u['name']} ({u['email']}) — {u['plan']}")
        k.schedule(day, 9 + i * 0.4, f"Signup: {u['name']}", _signup)

    # ── Onboarding steps ──────────────────────────────────────
    ONBOARD = [
        (1, 10, 0), (1, 14, 1), (2, 10, 2), (2, 14, 3),
        (3, 10, 4), (3, 14, 5), (4, 10, 0), (4, 14, 1),
    ]
    for day, hour, ui in ONBOARD:
        def _onboard(ui=ui):
            if ui not in uids: return
            step = f.onboarding_step()
            store.log_event(uids[ui], "onboarding", step)
            print(f"           ✅ Onboarding [{step}]: {users[ui]['name']}")
        k.schedule(day, hour, f"Onboarding: {users[ui]['name']}", _onboard)

    # ── Daily health checks ───────────────────────────────────
    for day in range(1, 31):
        k.schedule(day, 6, "Health check", lambda: print("           💓 Health check passed"))

    # ── Feature usage ─────────────────────────────────────────
    USAGE = [
        (8,9,0),(8,10,1),(9,11,2),(10,9,3),(10,14,4),
        (11,10,5),(12,9,6),(13,11,7),(14,9,8),(15,10,9),
        (16,9,0),(17,11,1),(18,14,2),(19,9,3),(20,10,4),
    ]
    for day, hour, ui in USAGE:
        def _feature(ui=ui):
            if ui not in uids: return
            feat = f.feature()
            store.log_event(uids[ui], "feature_used", feat)
            print(f"           🔧 {users[ui]['name']} used [{feat}]")
        k.schedule(day, hour, f"Feature: {users[ui]['name']}", _feature)

    # ── Upgrades ──────────────────────────────────────────────
    UPGRADES = [(14,10,0),(15,11,1),(16,9,2),(17,14,4),(18,10,5)]
    for day, hour, ui in UPGRADES:
        def _upgrade(ui=ui):
            if ui not in uids: return
            to_plan = f.upgrade_plan(users[ui]["plan"])
            store.upgrade_user(uids[ui], to_plan)
            print(f"           ⬆  {users[ui]['name']}: {users[ui]['plan']} → {to_plan}")
        k.schedule(day, hour, f"Upgrade: {users[ui]['name']}", _upgrade)

    # ── Nudge emails ──────────────────────────────────────────
    for ui in [3, 6, 7]:
        def _nudge(ui=ui):
            if ui not in uids: return
            nudge = f.nudge_type()
            store.log_event(uids[ui], "nudge_email", nudge)
            print(f"           📧 Nudge [{nudge}] → {users[ui]['name']}")
        k.schedule(12, 18 + ui * 0.1, f"Nudge: {users[ui]['name']}", _nudge)

    # ── Support tickets ───────────────────────────────────────
    TICKETS = [(10,11,3),(15,14,7),(20,10,8),(25,9,9)]
    for day, hour, ui in TICKETS:
        def _ticket(ui=ui):
            if ui not in uids: return
            ticket = f.support_ticket()
            store.add_ticket(uids[ui], ticket)
            print(f"           🎫 Ticket: {users[ui]['name']} — {ticket['issue']}")
        k.schedule(day, hour, f"Ticket: {users[ui]['name']}", _ticket)

    # ── Churn ─────────────────────────────────────────────────
    CHURN = [(22,9,6),(25,10,7),(28,9,9)]
    for day, hour, ui in CHURN:
        def _churn(ui=ui):
            if ui not in uids: return
            reason = f.churn_reason()
            store.churn_user(uids[ui], reason)
            print(f"           ❌ Churn: {users[ui]['name']} — {reason}")
        k.schedule(day, hour, f"Churn: {users[ui]['name']}", _churn)

        def _winback(ui=ui):
            if ui not in uids: return
            store.log_event(uids[ui], "nudge_email", "winback")
            print(f"           📧 Win-back → {users[ui]['name']}")
        k.schedule(day + 2, 10, f"Win-back: {users[ui]['name']}", _winback)

    k.schedule(30, 23.9, "Run summary", lambda: store.print_summary())
