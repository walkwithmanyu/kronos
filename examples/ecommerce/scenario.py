"""
Kronos Example — E-Commerce Scenario
======================================
Simulates 30 days of a Shopify/WooCommerce store:
orders, fulfilment, refunds, inventory alerts, and abandoned carts.

To run:
    kronos preview examples/ecommerce/scenario.py --days 30 --minutes 45
    kronos run    examples/ecommerce/scenario.py --days 30 --minutes 45
"""

from kronos import Kronos
import random

PRODUCTS = [
    ("Wireless Earbuds",  2999,  50),
    ("Laptop Stand",       999,  80),
    ("Mechanical Keyboard",3499, 30),
    ("USB-C Hub",         1499,  60),
    ("Webcam HD",         2299,  25),
]

CUSTOMERS = [
    "Aarav Shah", "Ishaan Verma", "Diya Patel", "Kabir Nair",
    "Ananya Gupta", "Vivaan Joshi", "Myra Singh", "Aryan Mehta",
    "Saanvi Rao", "Reyansh Kumar",
]

# ── Replace with your real store API calls ────────────────────────────────────

def place_order(customer, product, qty):
    total = product[1] * qty
    print(f"    🛒 Order: {customer} — {product[0]} x{qty} = ₹{total}")

def fulfil_order(customer, product):
    print(f"    📦 Fulfilled: {customer} — {product[0]}")

def send_tracking(customer):
    print(f"    🚚 Tracking email → {customer}")

def process_refund(customer, product):
    print(f"    ↩  Refund: {customer} — {product[0]}")

def low_stock_alert(product, remaining):
    print(f"    ⚠  Low stock: {product[0]} — {remaining} left")

def abandoned_cart_email(customer, product):
    print(f"    📧 Abandoned cart email → {customer} ({product[0]})")

def restock(product, qty):
    print(f"    ✅ Restocked: {product[0]} +{qty} units")

# ── Build scenario ────────────────────────────────────────────────────────────

def build(k: Kronos):
    random.seed(42)

    # Week 1 — steady orders
    for day in range(1, 8):
        for _ in range(random.randint(2, 4)):
            c = random.choice(CUSTOMERS)
            p = random.choice(PRODUCTS)
            qty = random.randint(1, 3)
            hour = random.uniform(8, 21)
            k.schedule(day, hour, f"Order: {c} — {p[0]}", lambda c=c, p=p, q=qty: place_order(c, p, q))
            k.schedule(day + 1, hour, f"Fulfil: {c} — {p[0]}", lambda c=c, p=p: fulfil_order(c, p))
            k.schedule(day + 1, hour + 0.5, f"Tracking → {c}", lambda c=c: send_tracking(c))

    # Day 5 — first refund
    k.schedule(5, 14, "Refund: Aarav Shah — Wireless Earbuds",
               lambda: process_refund("Aarav Shah", PRODUCTS[0]))

    # Day 7 — abandoned cart emails
    for c in CUSTOMERS[:3]:
        p = random.choice(PRODUCTS)
        k.schedule(7, 18, f"Abandoned cart → {c}", lambda c=c, p=p: abandoned_cart_email(c, p))

    # Week 2 — flash sale spike
    for day in range(8, 11):
        for _ in range(random.randint(5, 8)):
            c = random.choice(CUSTOMERS)
            p = random.choice(PRODUCTS)
            qty = random.randint(1, 5)
            hour = random.uniform(10, 20)
            k.schedule(day, hour, f"SALE Order: {c} — {p[0]}", lambda c=c, p=p, q=qty: place_order(c, p, q))

    # Day 10 — low stock alerts from sale spike
    k.schedule(10, 16, "Low stock: Mechanical Keyboard (4 left)",
               lambda: low_stock_alert(PRODUCTS[2], 4))
    k.schedule(10, 17, "Low stock: Webcam HD (3 left)",
               lambda: low_stock_alert(PRODUCTS[4], 3))

    # Day 12 — restock
    k.schedule(12, 9, "Restock: Mechanical Keyboard +50",
               lambda: restock(PRODUCTS[2], 50))
    k.schedule(12, 9, "Restock: Webcam HD +30",
               lambda: restock(PRODUCTS[4], 30))

    # Week 3 — normal pace resumes
    for day in range(15, 22):
        for _ in range(random.randint(2, 3)):
            c = random.choice(CUSTOMERS)
            p = random.choice(PRODUCTS)
            qty = random.randint(1, 2)
            hour = random.uniform(9, 20)
            k.schedule(day, hour, f"Order: {c} — {p[0]}", lambda c=c, p=p, q=qty: place_order(c, p, q))

    # Day 20 — second refund
    k.schedule(20, 11, "Refund: Diya Patel — USB-C Hub",
               lambda: process_refund("Diya Patel", PRODUCTS[3]))

    # Week 4 — month-end push
    for day in range(25, 30):
        for _ in range(random.randint(3, 5)):
            c = random.choice(CUSTOMERS)
            p = random.choice(PRODUCTS)
            qty = random.randint(1, 3)
            hour = random.uniform(8, 22)
            k.schedule(day, hour, f"Order: {c} — {p[0]}", lambda c=c, p=p, q=qty: place_order(c, p, q))

    # Day 30 — end of month abandoned cart sweep
    for c in CUSTOMERS[3:6]:
        p = random.choice(PRODUCTS)
        k.schedule(30, 19, f"EOM abandoned cart → {c}", lambda c=c, p=p: abandoned_cart_email(c, p))
