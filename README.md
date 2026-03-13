# Kronos — Compress time. Test everything.

**Simulate weeks of real activity in minutes.**
Kronos is a lightweight Python engine that maps a multi-day event timeline onto a short real-time window. Events fire at proportionally compressed intervals — against your real database, real APIs, and real integrations.

```
60 real minutes = 32 simulated days
1 real second   = ~25 simulated minutes
```

---

## Why Kronos?

Most testing tools simulate load (concurrent requests). Kronos simulates **time** — the realistic gap between a user signing up on Monday, upgrading on Friday, and churning three weeks later.

It's built for testing:
- **CRM pipelines** — leads moving through stages over weeks
- **SaaS apps** — signups, onboarding, upgrades, churn over a month
- **E-commerce** — orders, fulfilment, refunds, inventory cycles
- **Workflow tools** — anything where time gaps between steps matter

---

## Install

```bash
pip install kronos-engine
```

Or clone and install locally:
```bash
git clone https://github.com/YOUR_USERNAME/kronos.git
cd kronos
pip install -e .
```

---

## Quickstart

### 1. Write a scenario file

```python
# my_scenario.py
from kronos import Kronos

def signup(email):
    print(f"User signed up: {email}")

def upgrade(email, plan):
    print(f"User upgraded: {email} → {plan}")

def churn(email):
    print(f"User churned: {email}")

def build(k: Kronos):
    k.schedule(day=0,  hour=9,  description="Signup: alice@test.com",   func=lambda: signup("alice@test.com"))
    k.schedule(day=7,  hour=14, description="Upgrade: alice → pro",      func=lambda: upgrade("alice@test.com", "pro"))
    k.schedule(day=25, hour=9,  description="Churn: alice@test.com",     func=lambda: churn("alice@test.com"))
```

### 2. Preview the timeline

```bash
kronos preview my_scenario.py --days 30 --minutes 45
```

```
  Kronos — 30 sim-days in 45 real-minutes
  Compression: 960x  |  Events: 3

  SIM DATE       REAL TIME   DESCRIPTION
  ──────────────────────────────────────────────────────────────
  14 Mar 2026     0:00:00   Signup: alice@test.com
  21 Mar 2026     0:10:30   Upgrade: alice → pro
  08 Apr 2026     0:37:30   Churn: alice@test.com
```

### 3. Run it

```bash
kronos run my_scenario.py --days 30 --minutes 45
```

Kronos fires each function at the right real-time moment. Connect your functions to your real DB, API, or SDK — Kronos does the rest.

---

## Connect to your system

Replace the print stubs with your actual calls:

```python
# REST API
import requests
def place_order(customer_id, product_id):
    requests.post("https://your-api.com/orders", json={...})

# Database
import sqlite3
def add_lead(name, email):
    conn = sqlite3.connect("myapp.db")
    conn.execute("INSERT INTO leads (name, email) VALUES (?, ?)", (name, email))
    conn.commit()

# Any SDK (HubSpot, Stripe, Shopify, Notion...)
def advance_deal(deal_id, stage):
    hubspot_client.crm.deals.basic_api.update(deal_id, {"dealstage": stage})
```

---

## Built-in examples

| Example | What it simulates |
|---|---|
| [`examples/crm/`](examples/crm/) | 10 leads through a 7-stage pipeline over 30 days |
| [`examples/ecommerce/`](examples/ecommerce/) | Orders, fulfilment, refunds, flash sales, inventory alerts |
| [`examples/webapp/`](examples/webapp/) | SaaS signups, onboarding, upgrades, churn, support tickets |
| [`examples/postoffice/`](examples/postoffice/) | Full PostOffice CRM + website pipeline (the original Kronos scenario) |

Run any of them:
```bash
kronos preview examples/crm/scenario.py
kronos run    examples/ecommerce/scenario.py --days 30 --minutes 30
```

---

## API

### `Kronos(real_minutes, sim_days, label, on_event, on_error)`

| Param | Type | Default | Description |
|---|---|---|---|
| `real_minutes` | float | 60 | How long the simulation runs in real time |
| `sim_days` | int | 32 | How many days to simulate |
| `label` | str | "KRONOS" | Banner label shown at run start |
| `on_event` | Callable | None | Called after every successful event: `(event, sim_date)` |
| `on_error` | Callable | None | Called on any failed event: `(event, sim_date, exc)` |

### `k.schedule(day, hour, description, func)`

Queues an event. `func` is called with zero arguments. Use lambda closures for parameterised calls.

### `k.run()` → `dict`

Runs the simulation. Returns `{total, success, failed, elapsed_seconds, errors}`.

### `k.preview()`

Prints the full event timeline without executing anything.

---

## How time compression works

```
compression_ratio = (sim_days × 86400) / (real_minutes × 60)

real_fire_time = sim_offset_seconds / compression_ratio
```

Default (32 days / 60 min):
- **1,536× compression**
- Every 1 real second = 25.6 simulated minutes
- Every 2 real minutes ≈ 1 simulated day

---

## Error handling

Failed events don't stop the run. After completion:

```
  ┌──────────────────────────────────────────────────────┐
  │  ✅  Run complete                                     │
  │  Duration : 1m 3s                                    │
  │  Total    : 47                                       │
  │  Success  : 45                                       │
  │  Failed   : 2                                        │
  └──────────────────────────────────────────────────────┘

  ⚠  Errors:
     Day 12 [26 Mar 2026] — Webhook: alice@test.com
     Connection refused: localhost:4000
```

---

## Zero dependencies

Kronos core (`kronos/engine.py`) uses only Python stdlib — `time`, `threading`, `datetime`. No pip install required if you copy the file directly.

---

## License

MIT — use it, fork it, ship it.

---

## Built by NASCORP

Kronos was extracted from [PostOffice](https://github.com/YOUR_USERNAME/postoffice), a local business operations platform. It grew into a standalone tool because we needed to stress test an entire month of client pipeline activity before going live.

If you build something with it, open a PR with your scenario in `examples/`.
