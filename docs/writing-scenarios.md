# Writing a Kronos Scenario

A scenario is a plain Python file with a single `build(k: Kronos)` function.
Inside that function, you call `k.schedule()` to queue events. That's it.

---

## Minimal example

```python
from kronos import Kronos

def build(k: Kronos):
    k.schedule(day=1,  hour=9,  description="User signs up",    func=my_signup_fn)
    k.schedule(day=3,  hour=14, description="User upgrades",    func=my_upgrade_fn)
    k.schedule(day=30, hour=9,  description="User churns",      func=my_churn_fn)
```

Run it:
```bash
kronos run my_scenario.py --days 30 --minutes 45
```

---

## k.schedule() signature

```python
k.schedule(
    day:         int,       # Simulated day number (0 = day of run)
    hour:        float,     # Hour of the simulated day (0.0 – 23.9)
    description: str,       # Human-readable label shown in the terminal
    func:        Callable,  # Zero-argument callable fired at this moment
)
```

Events are automatically sorted by `(day, hour)` before the run starts.

---

## How time compression works

```
real_seconds = sim_offset_seconds / compression_ratio

compression_ratio = (sim_days × 86400) / (real_minutes × 60)
```

For the default 32 days / 60 minutes:
- compression ratio = **1,536×**
- 1 real second = **25.6 simulated minutes**
- 1 real minute = **~1 simulated day**

---

## Connecting to your real system

Replace the stub print functions in any example with your actual API calls.

### REST API
```python
import requests

def place_order(customer_id, product_id, qty):
    requests.post("https://your-api.com/orders", json={
        "customer_id": customer_id,
        "product_id": product_id,
        "quantity": qty,
    })
```

### Database (SQLite / PostgreSQL / MySQL)
```python
import sqlite3

def add_lead(name, email):
    conn = sqlite3.connect("myapp.db")
    conn.execute("INSERT INTO leads (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
```

### SDK (HubSpot, Stripe, Shopify…)
```python
import hubspot

def advance_deal(deal_id, stage):
    client = hubspot.Client.create(access_token="YOUR_TOKEN")
    client.crm.deals.basic_api.update(deal_id, {"dealstage": stage})
```

---

## Using lambda closures correctly

Because Python closures capture variables by reference, always use default
argument binding when scheduling inside a loop:

```python
# ✅ Correct — value is bound at schedule time
for client in clients:
    k.schedule(1, 9, f"Onboard {client}",
               lambda c=client: onboard(c))   # c=client binds the value

# ❌ Wrong — all lambdas capture the last value of `client`
for client in clients:
    k.schedule(1, 9, f"Onboard {client}",
               lambda: onboard(client))
```

---

## Error handling

If your `func` raises an exception, Kronos catches it, logs it, and continues
with the next event. After the run, the summary shows which events failed.

To handle errors yourself, pass `on_error` to the Kronos constructor:

```python
def my_error_handler(event, sim_date, exc):
    print(f"FAILED on {sim_date}: {event.description} — {exc}")

k = Kronos(real_minutes=60, sim_days=32, on_error=my_error_handler)
```

---

## Previewing without running

```bash
kronos preview my_scenario.py --days 32 --minutes 60
```

Prints the full timeline with real-clock offsets — no DB writes, no API calls.

---

## Adding preflight checks

Preflight checks run before the simulation starts. They scan your integrations,
show a status table, and ask for confirmation. If any check fails, the run is blocked.

```python
from kronos import Kronos
import requests, pathlib, json

def build(k: Kronos):
    # Register checks with k.add_check(label, fn)
    # fn must return ("ok"|"warn"|"fail", "detail string")

    def check_db():
        if not pathlib.Path("myapp.db").exists():
            return "fail", "myapp.db not found"
        return "ok", "database reachable"

    def check_api():
        try:
            r = requests.get("https://api.example.com/ping", timeout=5)
            return ("ok", "API reachable") if r.ok else ("fail", f"HTTP {r.status_code}")
        except Exception as e:
            return "warn", str(e)

    def check_token():
        p = pathlib.Path("token.json")
        if not p.exists():
            return "fail", "token.json missing"
        scopes = json.loads(p.read_text()).get("scopes", [])
        if "https://example.com/auth/send" not in scopes:
            return "warn", "missing send scope"
        return "ok", "token valid"

    k.add_check("Database", check_db)
    k.add_check("API",      check_api)
    k.add_check("Token",    check_token)

    # ... then schedule your events as normal
    k.schedule(1, 9, "First event", my_fn)
```

Run preflight without simulating:
```bash
kronos preflight my_scenario.py
```

Skip preflight when you're confident everything is working:
```bash
kronos run my_scenario.py --skip-preflight
```

---

## Chaining multiple scenarios

```python
from kronos import Kronos
from examples.crm.scenario import build as build_crm
from examples.ecommerce.scenario import build as build_ecom

k = Kronos(real_minutes=90, sim_days=32)
build_crm(k)
build_ecom(k)
k.run()
```
