"""Reset the database and load demo data.  Usage: python seed.py"""
import os

from auth import hash_password
from database import DB_PATH, get_db, init_db

USERS = [
    ("admin", "admin@securecart.local", "admin123", "admin"),
    ("alice", "alice@securecart.local", "alice123", "user"),
    ("bob", "bob@securecart.local", "bob123", "user"),
]

PRODUCTS = [
    ("Wireless Mouse", "Ergonomic 2.4GHz wireless mouse with silent clicks.", 19.99, 50),
    ("Mechanical Keyboard", "Tenkeyless keyboard with blue switches.", 69.50, 25),
    ("USB-C Hub", "7-in-1 hub: HDMI, USB 3.0, SD card reader.", 34.00, 40),
    ("27-inch Monitor", "1440p IPS monitor, 75Hz.", 249.00, 10),
    ("Laptop Stand", "Adjustable aluminium laptop stand.", 29.99, 60),
    ("Noise-Cancelling Headphones", "Over-ear Bluetooth headphones, 30h battery.", 129.00, 15),
    ("Webcam 1080p", "Full HD webcam with built-in microphone.", 44.90, 35),
    ("Portable SSD 1TB", "USB 3.2 portable solid state drive.", 89.00, 20),
    ("Desk Lamp", "LED desk lamp with dimmer and USB charging port.", 24.50, 45),
    ("Backpack", "Water-resistant 20L laptop backpack.", 39.00, 30),
]

# (product_id, username, rating, text)
REVIEWS = [
    (1, "alice", 5, "Great mouse, battery lasts forever."),
    (1, "bob", 4, "Good value for the price."),
    (2, "bob", 5, "Love the typing feel. A bit loud though."),
    (4, "alice", 4, "Sharp picture, stand is wobbly."),
    (6, "alice", 5, "Best noise cancelling I have owned."),
]

# (username, card_last4, [(product_id, qty), ...])
ORDERS = [
    ("alice", "4242", [(1, 1), (5, 2)]),
    ("alice", "4242", [(6, 1)]),
    ("bob", "1111", [(2, 1), (3, 1)]),
    ("bob", "1111", [(8, 1)]),
    ("admin", "0000", [(9, 3)]),
]


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    conn = get_db()

    ids = {}
    for username, email, password, role in USERS:
        cur = conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), role),
        )
        ids[username] = cur.lastrowid

    prices = {}
    for pid, (name, desc, price, stock) in enumerate(PRODUCTS, start=1):
        conn.execute(
            "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
            (name, desc, price, stock),
        )
        prices[pid] = (name, price)

    for product_id, username, rating, text in REVIEWS:
        conn.execute(
            "INSERT INTO reviews (product_id, user_id, username, rating, review_text, created_at) "
            "VALUES (?, ?, ?, ?, ?, '2025-01-15 10:00:00')",
            (product_id, ids[username], username, rating, text),
        )

    for username, last4, items in ORDERS:
        total = round(sum(prices[p][1] * q for p, q in items), 2)
        cur = conn.execute(
            "INSERT INTO orders (user_id, total, status, card_last4, created_at) "
            "VALUES (?, ?, 'paid', ?, '2025-01-20 12:00:00')",
            (ids[username], total, last4),
        )
        for p, q in items:
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) "
                "VALUES (?, ?, ?, ?, ?)",
                (cur.lastrowid, p, prices[p][0], q, prices[p][1]),
            )

    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH}: {len(USERS)} users, {len(PRODUCTS)} products, "
          f"{len(REVIEWS)} reviews, {len(ORDERS)} orders")


if __name__ == "__main__":
    main()
