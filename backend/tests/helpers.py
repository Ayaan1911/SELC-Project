"""Shared test helpers: seeding a temp DB and logging in through the real API."""
import auth
import database


def create_user(conn, username, email, password, role="user"):
    cur = conn.execute(
        "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
        (username, email, auth.hash_password(password), role),
    )
    return cur.lastrowid


def create_product(conn, name, description, price, stock=10):
    cur = conn.execute(
        "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
        (name, description, price, stock),
    )
    return cur.lastrowid


def create_order(conn, user_id, items, card_last4="4242"):
    """items: list of (product_id, quantity)."""
    cur = conn.execute(
        "INSERT INTO orders (user_id, total, status, card_last4, created_at) "
        "VALUES (?, 0, 'paid', ?, '2025-01-01 00:00:00')",
        (user_id, card_last4),
    )
    order_id = cur.lastrowid
    total = 0.0
    for product_id, qty in items:
        row = conn.execute(
            "SELECT name, price FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) "
            "VALUES (?, ?, ?, ?, ?)",
            (order_id, product_id, row["name"], qty, row["price"]),
        )
        total += row["price"] * qty
    conn.execute("UPDATE orders SET total = ? WHERE id = ?", (round(total, 2), order_id))
    return order_id


def seed_standard_data():
    """Create admin/alice/bob, two products, and one order each for alice and bob.

    Returns a dict of ids the tests use.
    """
    conn = database.get_db()
    ids = {
        "admin_id": create_user(conn, "admin", "admin@test.local", "admin123", "admin"),
        "alice_id": create_user(conn, "alice", "alice@test.local", "alice123", "user"),
        "bob_id": create_user(conn, "bob", "bob@test.local", "bob123", "user"),
    }
    ids["product1"] = create_product(conn, "Widget", "A plain widget", 9.99, 100)
    ids["product2"] = create_product(conn, "Gadget", "A fancy gadget", 19.99, 50)
    conn.commit()
    ids["order_alice"] = create_order(conn, ids["alice_id"], [(ids["product1"], 1)], "4242")
    ids["order_bob"] = create_order(conn, ids["bob_id"], [(ids["product2"], 1)], "1111")
    conn.commit()
    conn.close()
    return ids


def login(client, username, password):
    resp = client.post("/api/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
