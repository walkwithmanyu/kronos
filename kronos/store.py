"""
Kronos Store — lightweight SQLite connector for test simulations.

Creates a self-contained `kronos_test.db` with standard tables.
All data written during a run can be wiped with store.cleanup().

Usage
-----
>>> from kronos.store import KronosStore
>>> store = KronosStore()          # creates kronos_test.db in current dir
>>> cid = store.add_contact({...})
>>> store.add_deal(cid, "LEAD", budget=5000)
>>> store.cleanup()                # wipe all Kronos-written rows
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional


# ── Default schema ────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kn_contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT,
    company     TEXT,
    phone       TEXT,
    source      TEXT,
    created_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_deals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id  INTEGER REFERENCES kn_contacts(id),
    project     TEXT,
    budget      INTEGER,
    stage       TEXT DEFAULT 'LEAD',
    next_action TEXT,
    created_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_deal_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     INTEGER REFERENCES kn_deals(id),
    from_stage  TEXT,
    to_stage    TEXT,
    note        TEXT,
    ts          INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer    TEXT,
    email       TEXT,
    product     TEXT,
    quantity    INTEGER,
    unit_price  INTEGER,
    total       INTEGER,
    status      TEXT DEFAULT 'pending',
    created_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    email       TEXT UNIQUE,
    company     TEXT,
    plan        TEXT DEFAULT 'free',
    source      TEXT,
    churned     INTEGER DEFAULT 0,
    created_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES kn_users(id),
    event_type  TEXT,
    detail      TEXT,
    ts          INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    issue       TEXT,
    priority    TEXT,
    channel     TEXT,
    status      TEXT DEFAULT 'open',
    created_at  INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kn_run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name  TEXT,
    row_id      INTEGER,
    run_id      TEXT,
    ts          INTEGER DEFAULT (strftime('%s','now'))
);
"""


class KronosStore:
    """
    SQLite store for Kronos test data.

    All writes are tracked in `kn_run_log` so `cleanup()` can
    delete exactly the rows Kronos created, leaving pre-existing
    data untouched.

    Parameters
    ----------
    path : str | Path
        Path to the SQLite file. Defaults to `kronos_test.db`
        in the current working directory.
    run_id : str | None
        Identifier for this simulation run. Used to scope cleanup.
        Auto-generated if not provided.
    """

    def __init__(
        self,
        path: str = "kronos_test.db",
        run_id: Optional[str] = None,
    ):
        self.path   = Path(path)
        self.run_id = run_id or f"run_{int(time.time())}"
        self._conn  = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── CRM ───────────────────────────────────────────────────

    def add_contact(self, data: dict) -> int:
        """Insert a contact. Returns new row id."""
        cur = self._conn.execute(
            "INSERT INTO kn_contacts (name, email, company, phone, source) VALUES (?,?,?,?,?)",
            (data.get("name"), data.get("email"), data.get("company"),
             data.get("phone"), data.get("source")),
        )
        self._conn.commit()
        self._log("kn_contacts", cur.lastrowid)
        return cur.lastrowid

    def add_deal(
        self,
        contact_id: int,
        stage: str = "LEAD",
        project: str = "",
        budget: int = 0,
        next_action: str = "",
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO kn_deals (contact_id, project, budget, stage, next_action) VALUES (?,?,?,?,?)",
            (contact_id, project, budget, stage, next_action),
        )
        self._conn.commit()
        deal_id = cur.lastrowid
        self._log("kn_deals", deal_id)
        self._conn.execute(
            "INSERT INTO kn_deal_history (deal_id, from_stage, to_stage, note) VALUES (?,NULL,?,?)",
            (deal_id, stage, "Created via Kronos"),
        )
        self._conn.commit()
        return deal_id

    def advance_deal(self, deal_id: int, to_stage: str, note: str = "") -> None:
        row = self._conn.execute(
            "SELECT stage FROM kn_deals WHERE id=?", (deal_id,)
        ).fetchone()
        from_stage = row["stage"] if row else None
        self._conn.execute(
            "UPDATE kn_deals SET stage=? WHERE id=?", (to_stage, deal_id)
        )
        self._conn.execute(
            "INSERT INTO kn_deal_history (deal_id, from_stage, to_stage, note) VALUES (?,?,?,?)",
            (deal_id, from_stage, to_stage, note),
        )
        self._conn.commit()

    def add_note(self, deal_id: int, note: str) -> None:
        row = self._conn.execute(
            "SELECT stage FROM kn_deals WHERE id=?", (deal_id,)
        ).fetchone()
        stage = row["stage"] if row else ""
        self._conn.execute(
            "INSERT INTO kn_deal_history (deal_id, from_stage, to_stage, note) VALUES (?,?,?,?)",
            (deal_id, stage, stage, note),
        )
        self._conn.commit()

    def get_deal_stage(self, deal_id: int) -> str:
        row = self._conn.execute(
            "SELECT stage FROM kn_deals WHERE id=?", (deal_id,)
        ).fetchone()
        return row["stage"] if row else "LEAD"

    # ── E-commerce ────────────────────────────────────────────

    def add_order(self, customer: str, email: str, order: dict) -> int:
        cur = self._conn.execute(
            "INSERT INTO kn_orders (customer, email, product, quantity, unit_price, total, status) "
            "VALUES (?,?,?,?,?,?,?)",
            (customer, email, order["product"], order["quantity"],
             order["unit_price"], order["total"], order.get("status", "pending")),
        )
        self._conn.commit()
        self._log("kn_orders", cur.lastrowid)
        return cur.lastrowid

    def fulfil_order(self, order_id: int) -> None:
        self._conn.execute(
            "UPDATE kn_orders SET status='fulfilled' WHERE id=?", (order_id,)
        )
        self._conn.commit()

    def refund_order(self, order_id: int) -> None:
        self._conn.execute(
            "UPDATE kn_orders SET status='refunded' WHERE id=?", (order_id,)
        )
        self._conn.commit()

    # ── SaaS users ────────────────────────────────────────────

    def add_user(self, user: dict) -> int:
        try:
            cur = self._conn.execute(
                "INSERT INTO kn_users (name, email, company, plan, source) VALUES (?,?,?,?,?)",
                (user["name"], user["email"], user.get("company",""),
                 user.get("plan","free"), user.get("source","")),
            )
            self._conn.commit()
            uid = cur.lastrowid
            self._log("kn_users", uid)
            return uid
        except sqlite3.IntegrityError:
            row = self._conn.execute(
                "SELECT id FROM kn_users WHERE email=?", (user["email"],)
            ).fetchone()
            return row["id"] if row else -1

    def log_event(self, user_id: int, event_type: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO kn_events (user_id, event_type, detail) VALUES (?,?,?)",
            (user_id, event_type, detail),
        )
        self._conn.commit()

    def upgrade_user(self, user_id: int, to_plan: str) -> None:
        self._conn.execute(
            "UPDATE kn_users SET plan=? WHERE id=?", (to_plan, user_id)
        )
        self._conn.commit()
        self.log_event(user_id, "upgrade", f"→ {to_plan}")

    def churn_user(self, user_id: int, reason: str = "") -> None:
        self._conn.execute(
            "UPDATE kn_users SET churned=1 WHERE id=?", (user_id,)
        )
        self._conn.commit()
        self.log_event(user_id, "churn", reason)

    def add_ticket(self, user_id: int, ticket: dict) -> int:
        cur = self._conn.execute(
            "INSERT INTO kn_tickets (user_id, issue, priority, channel) VALUES (?,?,?,?)",
            (user_id, ticket["issue"], ticket.get("priority","medium"),
             ticket.get("channel","email")),
        )
        self._conn.commit()
        self._log("kn_tickets", cur.lastrowid)
        return cur.lastrowid

    # ── Reporting ─────────────────────────────────────────────

    def summary(self) -> dict:
        """Return a dict summarising the current state of all tables."""
        def count(table):
            return self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        return {
            "contacts": count("kn_contacts"),
            "deals":    count("kn_deals"),
            "orders":   count("kn_orders"),
            "users":    count("kn_users"),
            "events":   count("kn_events"),
            "tickets":  count("kn_tickets"),
        }

    def print_summary(self) -> None:
        s = self.summary()
        print()
        print("  ┌─────────────────────────────────────┐")
        print("  │  KRONOS STORE — RUN SUMMARY         │")
        print("  ├─────────────────────────────────────┤")
        for k, v in s.items():
            print(f"  │  {k:<16} {v:>4} rows written      │")
        print(f"  │  DB file  : {str(self.path):<25}│")
        print(f"  │  Run ID   : {self.run_id:<25}│")
        print("  ├─────────────────────────────────────┤")
        print("  │  Run  store.cleanup()  to wipe data │")
        print("  └─────────────────────────────────────┘")
        print()

    # ── Cleanup ───────────────────────────────────────────────

    def cleanup(self) -> None:
        """Delete all rows created in this run. Leaves pre-existing data intact."""
        rows = self._conn.execute(
            "SELECT table_name, row_id FROM kn_run_log WHERE run_id=?",
            (self.run_id,)
        ).fetchall()

        by_table: dict = {}
        for row in rows:
            by_table.setdefault(row["table_name"], []).append(row["row_id"])

        for table, ids in by_table.items():
            placeholders = ",".join("?" * len(ids))
            self._conn.execute(
                f"DELETE FROM {table} WHERE id IN ({placeholders})", ids
            )

        # also clean deal history for deleted deals
        if "kn_deals" in by_table:
            placeholders = ",".join("?" * len(by_table["kn_deals"]))
            self._conn.execute(
                f"DELETE FROM kn_deal_history WHERE deal_id IN ({placeholders})",
                by_table["kn_deals"],
            )

        self._conn.execute(
            "DELETE FROM kn_run_log WHERE run_id=?", (self.run_id,)
        )
        self._conn.commit()
        print(f"  🧹 Cleaned up {len(rows)} rows from run {self.run_id}")

    def close(self) -> None:
        self._conn.close()

    # ── Internal ──────────────────────────────────────────────

    def _log(self, table: str, row_id: int) -> None:
        self._conn.execute(
            "INSERT INTO kn_run_log (table_name, row_id, run_id) VALUES (?,?,?)",
            (table, row_id, self.run_id),
        )
        self._conn.commit()
