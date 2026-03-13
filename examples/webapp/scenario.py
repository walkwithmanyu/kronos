"""
Kronos Example — Web App / SaaS Scenario
==========================================
Simulates 30 days of a SaaS product:
signups, onboarding steps, feature usage, upgrades, churn, and support tickets.

Swap the stub functions below for your real API/DB calls.

To run:
    kronos preview examples/webapp/scenario.py --days 30 --minutes 45
    kronos run    examples/webapp/scenario.py --days 30 --minutes 45
"""

from kronos import Kronos

USERS = [
    ("alice@startup.io",    "Alice Chen",    "free"),
    ("bob@agency.co",       "Bob Tremblay",  "free"),
    ("carol@corp.com",      "Carol Osei",    "free"),
    ("dave@freelance.dev",  "Dave Kim",      "free"),
    ("eve@scaleup.io",      "Eve Martins",   "free"),
    ("frank@bigco.com",     "Frank Diallo",  "free"),
    ("grace@studio.io",     "Grace Lim",     "free"),
    ("henry@agency.net",    "Henry Russo",   "free"),
    ("isla@product.co",     "Isla Singh",    "free"),
    ("jake@devshop.io",     "Jake Okonkwo",  "free"),
]

# ── Replace with your real app calls ─────────────────────────────────────────

def signup(email, name, plan):
    print(f"    👤 Signup: {name} ({email}) — {plan}")

def onboarding_step(email, step):
    print(f"    ✅ Onboarding [{step}]: {email}")

def feature_used(email, feature):
    print(f"    🔧 Feature used — {feature}: {email}")

def upgrade(email, to_plan):
    print(f"    ⬆  Upgrade: {email} → {to_plan}")

def churn(email, reason):
    print(f"    ❌ Churn: {email} — {reason}")

def support_ticket(email, issue):
    print(f"    🎫 Ticket: {email} — {issue}")

def send_nudge_email(email, nudge_type):
    print(f"    📧 Nudge [{nudge_type}] → {email}")

def run_health_check():
    print(f"    💓 System health check passed")

# ── Build scenario ────────────────────────────────────────────────────────────

def build(k: Kronos):

    # ── Signups staggered across first week
    signup_days = [0, 0, 1, 1, 2, 3, 4, 5, 6, 7]
    for i, (email, name, plan) in enumerate(USERS):
        day = signup_days[i]
        k.schedule(day, 9 + i * 0.3, f"Signup: {name}",
                   lambda e=email, n=name, p=plan: signup(e, n, p))

    # ── Onboarding steps (days 1–5 for early signups)
    onboarding = [
        ("profile_complete",  1,  9.0),
        ("first_project",     1,  14.0),
        ("invite_teammate",   2,  10.0),
        ("connect_integration", 3, 11.0),
        ("published_first",   4,  15.0),
    ]
    for email, _, _ in USERS[:6]:
        for step, day, hour in onboarding:
            k.schedule(day, hour, f"Onboarding [{step}]: {email}",
                       lambda e=email, s=step: onboarding_step(e, s))

    # ── Daily health checks
    for day in range(1, 31):
        k.schedule(day, 6, "Daily health check", run_health_check)

    # ── Feature usage (spread through weeks 2–4)
    features = ["dashboard", "export_csv", "api_key", "webhooks", "analytics"]
    usage_events = [
        (8,  9,  0, "dashboard"),
        (8,  10, 1, "export_csv"),
        (9,  11, 2, "api_key"),
        (10, 9,  3, "dashboard"),
        (10, 14, 4, "webhooks"),
        (11, 10, 5, "analytics"),
        (12, 9,  6, "export_csv"),
        (13, 11, 7, "api_key"),
        (14, 9,  8, "webhooks"),
        (15, 10, 9, "analytics"),
        (16, 9,  0, "analytics"),
        (17, 11, 1, "webhooks"),
        (18, 14, 2, "export_csv"),
        (19, 9,  3, "api_key"),
        (20, 10, 4, "analytics"),
    ]
    for day, hour, ui, feat in usage_events:
        email = USERS[ui][0]
        k.schedule(day, hour, f"Feature [{feat}]: {email}",
                   lambda e=email, f=feat: feature_used(e, f))

    # ── Upgrades (heavy users go paid around day 14–18)
    upgrades = [
        (14, 10, 0, "pro"),
        (15, 11, 1, "pro"),
        (16, 9,  2, "team"),
        (17, 14, 4, "pro"),
        (18, 10, 5, "team"),
    ]
    for day, hour, ui, plan in upgrades:
        email = USERS[ui][0]
        k.schedule(day, hour, f"Upgrade → {plan}: {email}",
                   lambda e=email, p=plan: upgrade(e, p))

    # ── Nudge emails for users who haven't upgraded
    for ui in [3, 6, 7, 8, 9]:
        email = USERS[ui][0]
        k.schedule(12, 18, f"Nudge [upgrade_prompt]: {email}",
                   lambda e=email: send_nudge_email(e, "upgrade_prompt"))

    # ── Support tickets
    tickets = [
        (10, 11, 3, "Export not working for large datasets"),
        (15, 14, 7, "Webhook endpoint not receiving events"),
        (20, 10, 8, "Billing page shows wrong amount"),
        (25, 9,  9, "Cannot invite more than 3 teammates"),
    ]
    for day, hour, ui, issue in tickets:
        email = USERS[ui][0]
        k.schedule(day, hour, f"Support ticket: {email}",
                   lambda e=email, i=issue: support_ticket(e, i))

    # ── Churn (days 22–28, users who never engaged)
    churn_events = [
        (22, 9, 6, "Not using it enough"),
        (25, 10, 7, "Found a cheaper alternative"),
        (28, 9, 9, "Project finished"),
    ]
    for day, hour, ui, reason in churn_events:
        email = USERS[ui][0]
        k.schedule(day, hour, f"Churn: {email}",
                   lambda e=email, r=reason: churn(e, r))

    # ── Win-back emails for churned users
    for day, hour, ui, _ in churn_events:
        email = USERS[ui][0]
        k.schedule(day + 2, 10, f"Win-back email → {email}",
                   lambda e=email: send_nudge_email(e, "winback"))
