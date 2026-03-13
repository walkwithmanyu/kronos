"""
Kronos Example — CRM Pipeline Scenario
=======================================
Simulates 10 leads moving through a 7-stage CRM pipeline over 30 days.
Works with any CRM that has a Python SDK or REST API.

Stages: LEAD → DISCOVERY CALL → PROPOSAL SENT → NEGOTIATION
        → PROJECT ACTIVE → DELIVERED → INVOICE SENT → CLOSED

To run:
    kronos preview examples/crm/scenario.py --days 30 --minutes 45
    kronos run    examples/crm/scenario.py --days 30 --minutes 45
"""

from kronos import Kronos

CLIENTS = [
    ("Arjun Mehta",       "arjun@mehta.in",       "Mehta & Sons",       "Brand Identity"),
    ("Priya Sharma",      "priya@prisync.co",      "PriSync",            "E-Commerce Store"),
    ("Vikram Nair",       "vikram@nairlogistics.in","Nair Logistics",     "Ops Dashboard"),
    ("Sunita Rao",        "sunita@greenleaf.in",   "GreenLeaf Organics", "Marketing Site"),
    ("Rahul Gupta",       "rahul@guptafintech.com","Gupta FinTech",      "SaaS Landing Page"),
    ("Kavitha Menon",     "kavitha@menonarch.in",  "Menon Architecture", "Portfolio Site"),
    ("Deepak Joshi",      "deepak@joshitravel.in", "Joshi Travel",       "Booking Platform"),
    ("Ananya Krishnan",   "ananya@krishnanlaw.in", "Krishnan & Associates","Legal Portal"),
    ("Rohan Malhotra",    "rohan@malhotratech.in", "Malhotra Tech",      "API Integration"),
    ("Neha Patel",        "neha@patelwellness.in", "Patel Wellness",     "Wellness App"),
]

# ── Replace these functions with your real CRM calls ─────────────────────────

def add_lead(name, email, company, project):
    """Add a new lead to your CRM."""
    print(f"    + Lead: {name} ({company}) — {project}")
    # Example (HubSpot):
    # hubspot.crm.contacts.basic_api.create(SimplePublicObjectInput(
    #     properties={"firstname": name, "email": email, "company": company}
    # ))

def advance_stage(name, to_stage, note=""):
    """Move a deal to the next stage."""
    print(f"    → {name}: {to_stage}  {('| ' + note) if note else ''}")

def add_note(name, note):
    """Log a note against a deal."""
    print(f"    📝 {name}: {note}")

def send_email(name, template):
    """Send a stage-matched email."""
    print(f"    ✉  {name}: [{template}] email sent")

# ── Build scenario ────────────────────────────────────────────────────────────

def build(k: Kronos):
    """Called by `kronos run`. Wire all events onto k."""

    TIMELINE = [
        # day  hr   client  action           note/template
        (0,   9,   0,  "lead",    "Intro call booked"),
        (0,   10,  1,  "lead",    "Referral from LinkedIn"),
        (1,   9,   2,  "lead",    "Inbound enquiry"),
        (1,   14,  3,  "lead",    "Cold outreach responded"),
        (2,   9,   4,  "lead",    "Demo requested"),
        (2,   11,  5,  "lead",    "Warm intro via partner"),
        (3,   9,   6,  "lead",    "Website contact form"),
        (3,   15,  7,  "lead",    "Trade show follow-up"),
        (4,   9,   8,  "lead",    "Podcast listener"),
        (4,   11,  9,  "lead",    "Old client returning"),

        (3,   10,  0,  "advance", "DISCOVERY CALL"),
        (4,   10,  1,  "advance", "DISCOVERY CALL"),
        (5,   10,  2,  "advance", "DISCOVERY CALL"),
        (5,   14,  3,  "advance", "DISCOVERY CALL"),
        (6,   10,  4,  "advance", "DISCOVERY CALL"),

        (6,   9,   0,  "email",   "discovery_followup"),
        (7,   9,   1,  "email",   "discovery_followup"),
        (7,   11,  2,  "email",   "discovery_followup"),

        (8,   10,  0,  "advance", "PROPOSAL SENT"),
        (9,   10,  1,  "advance", "PROPOSAL SENT"),
        (9,   14,  2,  "advance", "PROPOSAL SENT"),
        (10,  10,  3,  "advance", "DISCOVERY CALL"),
        (11,  10,  4,  "advance", "PROPOSAL SENT"),
        (11,  14,  5,  "advance", "DISCOVERY CALL"),

        (12,  9,   0,  "advance", "NEGOTIATION"),
        (13,  9,   1,  "advance", "NEGOTIATION"),
        (13,  14,  2,  "advance", "NEGOTIATION"),
        (14,  9,   0,  "note",    "Client requested 10% discount"),
        (14,  11,  1,  "note",    "Needs phased payment plan"),

        (15,  10,  0,  "advance", "PROJECT ACTIVE"),
        (16,  10,  1,  "advance", "PROJECT ACTIVE"),
        (16,  14,  2,  "advance", "NEGOTIATION"),
        (17,  10,  3,  "advance", "PROPOSAL SENT"),
        (18,  10,  4,  "advance", "PROJECT ACTIVE"),
        (18,  14,  5,  "advance", "PROPOSAL SENT"),
        (19,  10,  6,  "advance", "DISCOVERY CALL"),
        (20,  10,  7,  "advance", "DISCOVERY CALL"),
        (21,  10,  8,  "advance", "DISCOVERY CALL"),
        (21,  14,  9,  "advance", "DISCOVERY CALL"),

        (22,  9,   0,  "advance", "DELIVERED"),
        (23,  9,   1,  "advance", "DELIVERED"),
        (23,  14,  2,  "advance", "PROJECT ACTIVE"),
        (24,  9,   3,  "advance", "NEGOTIATION"),
        (24,  14,  4,  "advance", "DELIVERED"),

        (25,  9,   0,  "advance", "INVOICE SENT"),
        (25,  14,  0,  "email",   "invoice"),
        (26,  9,   1,  "advance", "INVOICE SENT"),
        (26,  14,  1,  "email",   "invoice"),
        (27,  9,   2,  "advance", "INVOICE SENT"),
        (27,  14,  2,  "email",   "invoice"),

        (28,  9,   0,  "advance", "CLOSED"),
        (28,  14,  0,  "email",   "closed_thankyou"),
        (29,  9,   1,  "advance", "CLOSED"),
        (29,  14,  1,  "email",   "closed_thankyou"),
        (30,  9,   2,  "advance", "CLOSED"),
    ]

    for (day, hour, ci, action, note) in TIMELINE:
        name, email, company, project = CLIENTS[ci]

        if action == "lead":
            k.schedule(day, hour,
                f"New lead: {name} ({company})",
                lambda n=name, e=email, c=company, p=project: add_lead(n, e, c, p))

        elif action == "advance":
            k.schedule(day, hour,
                f"Advance → {note}: {name}",
                lambda n=name, s=note: advance_stage(n, s))

        elif action == "note":
            k.schedule(day, hour,
                f"Note on {name}",
                lambda n=name, nt=note: add_note(n, nt))

        elif action == "email":
            k.schedule(day, hour,
                f"Email [{note}] → {name}",
                lambda n=name, t=note: send_email(n, t))
