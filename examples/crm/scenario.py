"""
Kronos Example — CRM Pipeline Scenario
=======================================
Simulates 10 leads moving through a 7-stage CRM pipeline over 30 days.

Uses DataFactory to generate realistic contacts, budgets, and notes.
Uses KronosStore to write everything to a real SQLite database.

No external dependencies required — pure stdlib.

To run:
    kronos preview examples/crm/scenario.py --days 30 --minutes 45
    kronos run    examples/crm/scenario.py --days 30 --minutes 45

After the run:
    sqlite3 kronos_test.db "SELECT name, stage FROM kn_contacts JOIN kn_deals ON kn_contacts.id=kn_deals.contact_id;"

To wipe test data:
    python3 -c "from kronos.store import KronosStore; KronosStore().cleanup()"
"""

from kronos import Kronos
from kronos.factory import DataFactory
from kronos.store import KronosStore


def build(k: Kronos):
    f     = DataFactory(seed=42)
    store = KronosStore()
    ids   = {}   # client_index → {contact_id, deal_id}

    # ── Preflight ─────────────────────────────────────────────
    k.add_check("Database", lambda: ("ok", f"kronos_test.db ready")
                if store.summary() is not None else ("fail", "store error"))

    # ── Generate 10 contacts upfront (deterministic with seed) ─
    contacts = f.contacts(10)

    TIMELINE = [
        (0,  9,  0, "lead",    ""), (0,  11, 1, "lead",    ""),
        (1,  9,  2, "lead",    ""), (1,  14, 3, "lead",    ""),
        (2,  9,  4, "lead",    ""), (2,  11, 5, "lead",    ""),
        (3,  9,  6, "lead",    ""), (3,  15, 7, "lead",    ""),
        (4,  9,  8, "lead",    ""), (4,  11, 9, "lead",    ""),
        (3,  10, 0, "advance", "DISCOVERY CALL"),
        (4,  10, 1, "advance", "DISCOVERY CALL"),
        (5,  10, 2, "advance", "DISCOVERY CALL"),
        (5,  14, 3, "advance", "DISCOVERY CALL"),
        (6,  10, 4, "advance", "DISCOVERY CALL"),
        (4,  15, 0, "note",    ""),
        (5,  15, 1, "note",    ""),
        (8,  10, 0, "advance", "PROPOSAL SENT"),
        (9,  10, 1, "advance", "PROPOSAL SENT"),
        (9,  14, 2, "advance", "PROPOSAL SENT"),
        (11, 10, 4, "advance", "PROPOSAL SENT"),
        (13, 9,  0, "advance", "NEGOTIATION"),
        (13, 14, 1, "advance", "NEGOTIATION"),
        (14, 9,  2, "advance", "NEGOTIATION"),
        (14, 11, 0, "note",    ""),
        (15, 10, 0, "advance", "PROJECT ACTIVE"),
        (16, 10, 1, "advance", "PROJECT ACTIVE"),
        (18, 10, 4, "advance", "PROJECT ACTIVE"),
        (22, 9,  0, "advance", "DELIVERED"),
        (23, 9,  1, "advance", "DELIVERED"),
        (24, 14, 4, "advance", "DELIVERED"),
        (25, 9,  0, "advance", "INVOICE SENT"),
        (26, 9,  1, "advance", "INVOICE SENT"),
        (27, 9,  2, "advance", "INVOICE SENT"),
        (28, 9,  0, "advance", "CLOSED"),
        (29, 9,  1, "advance", "CLOSED"),
        (30, 9,  2, "advance", "CLOSED"),
    ]

    for day, hour, ci, action, extra in TIMELINE:
        c = contacts[ci]

        if action == "lead":
            def _onboard(ci=ci, c=c):
                cid = store.add_contact(c)
                did = store.add_deal(cid, stage="LEAD", project=c["project"],
                                     budget=c["budget"], next_action=c["next_action"])
                ids[ci] = {"contact_id": cid, "deal_id": did}
                print(f"           + {c['name']} ({c['company']}) — {c['project']} [budget: {c['budget']:,}]")
            k.schedule(day, hour, f"New lead: {c['name']}", _onboard)

        elif action == "advance":
            def _advance(ci=ci, c=c, stage=extra):
                if ci not in ids: return
                note = f.crm_note(stage)
                store.advance_deal(ids[ci]["deal_id"], stage, note)
                print(f"           → {c['name']}: {stage}  | {note}")
            k.schedule(day, hour, f"Advance → {extra}: {c['name']}", _advance)

        elif action == "note":
            def _note(ci=ci, c=c):
                if ci not in ids: return
                stage = store.get_deal_stage(ids[ci]["deal_id"])
                note  = f.crm_note(stage)
                store.add_note(ids[ci]["deal_id"], note)
                print(f"           📝 {c['name']}: {note}")
            k.schedule(day, hour, f"Note: {c['name']}", _note)

    k.schedule(30, 23.9, "Run summary", lambda: store.print_summary())
