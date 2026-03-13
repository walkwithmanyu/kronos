"""
Kronos DataFactory — generates realistic fake data for simulations.

Zero external dependencies. Uses only Python stdlib.
Optionally uses `faker` if installed (pip install faker) for richer output.

Usage
-----
>>> from kronos.factory import DataFactory
>>> f = DataFactory(seed=42)
>>> f.contact()
{'name': 'Priya Mehta', 'email': 'priya.mehta@brightleaf.io', 'company': 'BrightLeaf', ...}
>>> f.order()
{'product': 'Wireless Earbuds', 'quantity': 2, 'unit_price': 2499, 'total': 4998}
"""

import random
import string
import hashlib
from typing import Optional


# ── Raw data pools (stdlib only — no faker needed) ────────────────────────────

_FIRST_NAMES = [
    "Aarav", "Aditi", "Ajay", "Alok", "Amit", "Ananya", "Anjali", "Arjun",
    "Aryan", "Deepak", "Diya", "Divya", "Gaurav", "Ishaan", "Kabir", "Kavita",
    "Kavya", "Kiran", "Manish", "Meera", "Mohan", "Neeraj", "Neha", "Nikhil",
    "Pankaj", "Pooja", "Priya", "Rahul", "Rajesh", "Ravi", "Ritika", "Rohan",
    "Sanjay", "Sanya", "Shreya", "Sneha", "Sunita", "Suresh", "Tanvi", "Vikram",
    "Vikas", "Vinay", "Vivaan", "Yash", "Zara",
    # international mix
    "Alice", "Bob", "Carol", "Dave", "Emma", "Frank", "Grace", "Henry",
    "Isabel", "Jake", "Lena", "Marco", "Nina", "Oscar", "Paula", "Quinn",
    "Rachel", "Sam", "Tanya", "Uma", "Victor", "Wendy", "Xander", "Yuki", "Zoe",
]

_LAST_NAMES = [
    "Agarwal", "Bose", "Chandra", "Chopra", "Das", "Ghosh", "Gupta", "Joshi",
    "Kapoor", "Khanna", "Kumar", "Malhotra", "Mehta", "Mishra", "Nair", "Patel",
    "Pillai", "Rao", "Reddy", "Shah", "Sharma", "Singh", "Sinha", "Tiwari",
    "Varma", "Verma",
    "Chen", "Diallo", "Garcia", "Kim", "Lim", "Martinez", "Osei", "Russo",
    "Schmidt", "Tanaka", "Tremblay", "Williams",
]

_COMPANY_WORDS = [
    "Apex", "Bright", "Clear", "Delta", "Edge", "Fusion", "Globe", "Horizon",
    "Innov", "Jet", "Karma", "Leap", "Mint", "Nova", "Orbit", "Peak",
    "Pulse", "Quest", "Rapid", "Sharp", "Swift", "Titan", "Ultra", "Vibe",
    "Wave", "Xcel", "Zenith",
]

_COMPANY_SUFFIXES = [
    "Tech", "Labs", "Studio", "Works", "Hub", "Co", "Group", "Solutions",
    "Digital", "Systems", "Ventures", "Dynamics", "Analytics", "Media",
    "Designs", "Consulting", "Agency", "Platforms",
]

_DOMAINS = [
    "io", "co", "in", "com", "dev", "app", "ai", "net",
]

_PROJECTS = [
    "Brand Identity", "E-Commerce Store", "Mobile App", "SaaS Dashboard",
    "Landing Page", "Marketing Site", "API Integration", "Ops Dashboard",
    "CRM Setup", "Analytics Platform", "Booking System", "Portfolio Site",
    "Internal Tool", "Data Pipeline", "Automation Workflow", "Web Scraper",
    "Admin Panel", "Customer Portal", "Reporting Suite", "Notification System",
]

_PRODUCTS = [
    ("Wireless Earbuds",    1299, 2999),
    ("Laptop Stand",         499, 1499),
    ("Mechanical Keyboard", 2499, 4999),
    ("USB-C Hub",            799, 1999),
    ("Webcam HD",           1499, 2999),
    ("Smart Speaker",       1999, 3999),
    ("Monitor Light Bar",    699, 1499),
    ("Desk Mat XL",          399,  999),
    ("Cable Management Kit", 299,  699),
    ("Ergonomic Mouse",      999, 2499),
]

_SUPPORT_ISSUES = [
    "Export not working for large datasets",
    "Webhook endpoint not receiving events",
    "Billing page shows wrong amount",
    "Cannot invite more than 3 teammates",
    "Dashboard takes too long to load",
    "Email notifications not arriving",
    "API rate limit hit unexpectedly",
    "CSV import fails on special characters",
    "Password reset link expired too quickly",
    "Integration with Slack stopped working",
    "Charts not rendering on mobile",
    "Search returns no results after update",
]

_CHURN_REASONS = [
    "Not using it enough",
    "Found a cheaper alternative",
    "Project finished — no longer needed",
    "Missing a key feature",
    "Switched to in-house solution",
    "Budget cut",
    "Team too small to need this",
    "Competitor offered better onboarding",
]

_NUDGE_TYPES = [
    "upgrade_prompt", "feature_tip", "winback",
    "usage_milestone", "inactivity_warning", "referral_ask",
]

_CRM_STAGES = [
    "LEAD", "DISCOVERY CALL", "PROPOSAL SENT",
    "NEGOTIATION", "PROJECT ACTIVE", "DELIVERED",
    "INVOICE SENT", "CLOSED",
]

_SAAS_PLANS = ["free", "starter", "pro", "team", "enterprise"]

_SAAS_FEATURES = [
    "dashboard", "export_csv", "api_key", "webhooks",
    "analytics", "team_invite", "custom_domain", "audit_log",
    "sso", "2fa", "bulk_import", "white_label",
]

_ONBOARDING_STEPS = [
    "profile_complete", "first_project", "invite_teammate",
    "connect_integration", "published_first", "set_billing",
]


class DataFactory:
    """
    Generates reproducible realistic fake data for Kronos scenarios.

    Parameters
    ----------
    seed : int | None
        Random seed for reproducibility. None = random every run.
    locale : str
        "in" for Indian-flavoured data, "global" for mixed.
    """

    def __init__(self, seed: Optional[int] = None, locale: str = "global"):
        self._rng = random.Random(seed)
        self.locale = locale
        self._used_emails: set = set()

    # ── Primitives ────────────────────────────────────────────

    def first_name(self) -> str:
        return self._rng.choice(_FIRST_NAMES)

    def last_name(self) -> str:
        return self._rng.choice(_LAST_NAMES)

    def full_name(self) -> str:
        return f"{self.first_name()} {self.last_name()}"

    def company_name(self) -> str:
        word   = self._rng.choice(_COMPANY_WORDS)
        suffix = self._rng.choice(_COMPANY_SUFFIXES)
        return f"{word}{suffix}"

    def email(self, name: Optional[str] = None, company: Optional[str] = None) -> str:
        if name is None:
            name = self.full_name()
        local = name.lower().replace(" ", ".")
        domain_word = (company or self.company_name()).lower().replace(" ", "")
        tld = self._rng.choice(_DOMAINS)
        base = f"{local}@{domain_word}.{tld}"
        # ensure uniqueness
        candidate = base
        i = 1
        while candidate in self._used_emails:
            candidate = f"{local}{i}@{domain_word}.{tld}"
            i += 1
        self._used_emails.add(candidate)
        return candidate

    def phone(self) -> str:
        prefix = self._rng.choice(["+91", "+1", "+44", "+61"])
        number = "".join(self._rng.choices(string.digits, k=10))
        return f"{prefix} {number[:5]} {number[5:]}"

    def budget(self, low: int = 500, high: int = 50000) -> int:
        """Returns a round-number budget in the range."""
        raw = self._rng.randint(low // 500, high // 500) * 500
        return raw

    def project(self) -> str:
        return self._rng.choice(_PROJECTS)

    def next_action(self) -> str:
        actions = [
            "Schedule discovery call", "Send proposal", "Follow up on proposal",
            "Confirm project kick-off", "Send invoice", "Request feedback",
            "Schedule review call", "Send contract",
        ]
        return self._rng.choice(actions)

    # ── Composite objects ─────────────────────────────────────

    def contact(self) -> dict:
        """A full CRM contact dict."""
        name    = self.full_name()
        company = self.company_name()
        return {
            "name":        name,
            "email":       self.email(name, company),
            "company":     company,
            "phone":       self.phone(),
            "project":     self.project(),
            "budget":      self.budget(),
            "next_action": self.next_action(),
            "source":      self._rng.choice([
                "LinkedIn", "Referral", "Inbound", "Cold outreach",
                "Website", "Trade show", "Podcast", "Returning client",
            ]),
        }

    def order(self) -> dict:
        """A single e-commerce order line."""
        product, low, high = self._rng.choice(_PRODUCTS)
        qty        = self._rng.randint(1, 4)
        unit_price = self._rng.randint(low, high)
        return {
            "product":    product,
            "quantity":   qty,
            "unit_price": unit_price,
            "total":      unit_price * qty,
            "status":     "pending",
        }

    def saas_user(self, plan: Optional[str] = None) -> dict:
        """A SaaS signup record."""
        name    = self.full_name()
        company = self.company_name()
        return {
            "name":    name,
            "email":   self.email(name, company),
            "company": company,
            "plan":    plan or self._rng.choice(_SAAS_PLANS[:3]),  # default to lower tiers
            "source":  self._rng.choice([
                "organic", "referral", "paid_ad", "product_hunt",
                "hacker_news", "twitter", "direct",
            ]),
        }

    def support_ticket(self) -> dict:
        return {
            "issue":    self._rng.choice(_SUPPORT_ISSUES),
            "priority": self._rng.choice(["low", "medium", "high"]),
            "channel":  self._rng.choice(["email", "chat", "form"]),
        }

    def churn_reason(self) -> str:
        return self._rng.choice(_CHURN_REASONS)

    def nudge_type(self) -> str:
        return self._rng.choice(_NUDGE_TYPES)

    def upgrade_plan(self, current: str = "free") -> str:
        idx = _SAAS_PLANS.index(current) if current in _SAAS_PLANS else 0
        next_idx = min(idx + 1, len(_SAAS_PLANS) - 1)
        return _SAAS_PLANS[next_idx]

    def onboarding_step(self) -> str:
        return self._rng.choice(_ONBOARDING_STEPS)

    def feature(self) -> str:
        return self._rng.choice(_SAAS_FEATURES)

    def crm_note(self, stage: str = "") -> str:
        notes = {
            "LEAD":           ["Intro call booked", "Referral from LinkedIn", "Inbound enquiry"],
            "DISCOVERY CALL": ["Good discovery call", "Clear budget confirmed", "Strong fit"],
            "PROPOSAL SENT":  ["Proposal sent — awaiting feedback", "Client requested changes"],
            "NEGOTIATION":    ["Client requested 10% discount", "Needs phased payment plan"],
            "PROJECT ACTIVE": ["Kick-off done", "Week 1 progress good", "On track"],
            "DELIVERED":      ["Delivered and approved", "Minor revisions requested"],
            "INVOICE SENT":   ["Invoice sent — payment due in 7 days"],
            "CLOSED":         ["Project complete", "Client very happy — referral likely"],
        }
        pool = notes.get(stage, ["Follow-up scheduled", "Awaiting response"])
        return self._rng.choice(pool)

    # ── Bulk generators ───────────────────────────────────────

    def contacts(self, n: int) -> list:
        """Generate a list of n unique contact dicts."""
        return [self.contact() for _ in range(n)]

    def orders(self, n: int) -> list:
        return [self.order() for _ in range(n)]

    def saas_users(self, n: int) -> list:
        return [self.saas_user() for _ in range(n)]
