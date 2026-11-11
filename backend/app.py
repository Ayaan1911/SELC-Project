"""SecureCart v1 backend (FastAPI + raw sqlite3).

Run with:  python app.py   (binds to 127.0.0.1:8000 only)
"""
import logging
import traceback
import uuid
from datetime import datetime

import bleach
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from auth import create_token, get_current_user, hash_password, require_admin, verify_password
from database import get_db, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("securecart")

app = FastAPI(title="SecureCart API")

# ------------------------------------------------------------------- CORS
# VULN-10: CORS allows every origin (CWE-942)
# VULN-11: no security headers are set anywhere (no CSP, X-Frame-Options,
#          X-Content-Type-Options, HSTS, ...) (CWE-693)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------- error handling
# VULN-09 FIXED: the client gets a generic message and a correlation ID; the
# full exception type, message and stack trace are logged server-side only,
# never returned in the response (CWE-209).
@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())
    logger.error(
        "Unhandled error [%s] on %s %s: %s\n%s",
        error_id, request.method, request.url.path, exc, traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again later.", "error_id": error_id},
    )


# ------------------------------------------------------------------ models
class RegisterBody(BaseModel):
    username: str
    email: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


class ReviewBody(BaseModel):
    rating: int
    review_text: str

    # VULN-07 FIXED (backend half): validate/sanitize on the way in (CWE-79).
    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("rating must be between 1 and 5")
        return v

    @field_validator("review_text")
    @classmethod
    def review_text_is_plain_text(cls, v):
        # Strip all HTML tags/attributes; keep only the plain text content.
        cleaned = bleach.clean(v, tags=[], attributes={}, strip=True).strip()
        if not cleaned:
            raise ValueError("review_text must not be empty")
        if len(cleaned) > 2000:
            raise ValueError("review_text is too long (max 2000 characters)")
        return cleaned


class CartBody(BaseModel):
    product_id: int
    quantity: int = 1


class CheckoutBody(BaseModel):
    card_name: str
    card_number: str  # MOCK payment: use a dummy number, never a real one
    expiry: str


class ProductBody(BaseModel):
    name: str
    description: str = ""
    price: float
    stock: int = 0


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------------------- auth
@app.post("/api/register")
def register(body: RegisterBody):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
            (body.username, body.email, hash_password(body.password)),
        )
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Username or email already taken")
    user_id = cur.lastrowid
    conn.close()
    return {"id": user_id, "username": body.username, "role": "user"}


# VULN-04 FIXED: rate limiting + temporary lockout (CWE-307). After
# MAX_LOGIN_ATTEMPTS consecutive failures for a username, further attempts
# are rejected for LOGIN_LOCKOUT_SECONDS, even with the correct password.
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300


def _is_locked_out(conn, username: str) -> bool:
    rows = conn.execute(
        "SELECT success, created_at FROM login_attempts "
        "WHERE username = ? ORDER BY id DESC LIMIT ?",
        (username, MAX_LOGIN_ATTEMPTS),
    ).fetchall()
    if len(rows) < MAX_LOGIN_ATTEMPTS or any(r["success"] for r in rows):
        return False
    last_attempt = datetime.strptime(rows[0]["created_at"], "%Y-%m-%d %H:%M:%S")
    return (datetime.now() - last_attempt).total_seconds() < LOGIN_LOCKOUT_SECONDS


@app.post("/api/login")
def login(body: LoginBody):
    conn = get_db()
    if _is_locked_out(conn, body.username):
        conn.close()
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again in a few minutes.",
        )

    row = conn.execute(
        "SELECT id, username, password, role FROM users WHERE username = ?",
        (body.username,),
    ).fetchone()
    success = row is not None and verify_password(body.password, row["password"])
    conn.execute(
        "INSERT INTO login_attempts (username, success, created_at) VALUES (?, ?, ?)",
        (body.username, 1 if success else 0, now()),
    )
    conn.commit()
    conn.close()

    if not success:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(row["id"], row["username"], row["role"])
    return {"token": token, "username": row["username"], "role": row["role"]}


# ---------------------------------------------------------------- products
@app.get("/api/products")
def list_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/products/search")
def search_products(q: str = ""):
    # VULN-01 FIXED: parameterized query - user input is bound as data, never
    # concatenated into SQL text, so it can't change the query's structure (CWE-89).
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, description, price, stock FROM products WHERE name LIKE ?",
        (f"%{q}%",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/products/{product_id}")
def product_detail(product_id: int):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    reviews = conn.execute(
        "SELECT id, username, rating, review_text, created_at FROM reviews "
        "WHERE product_id = ? ORDER BY id DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    result = dict(product)
    result["reviews"] = [dict(r) for r in reviews]
    return result


@app.post("/api/products/{product_id}/reviews")
def add_review(product_id: int, body: ReviewBody, user: dict = Depends(get_current_user)):
    conn = get_db()
    if conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    # body.review_text was already sanitized to plain text by the validator above.
    text = body.review_text
    conn.execute(
        "INSERT INTO reviews (product_id, user_id, username, rating, review_text, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (product_id, user["id"], user["username"], body.rating, text, now()),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


# -------------------------------------------------------------------- cart
@app.get("/api/cart")
def get_cart(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT c.id, c.product_id, c.quantity, p.name, p.price "
        "FROM cart_items c JOIN products p ON p.id = c.product_id "
        "WHERE c.user_id = ? ORDER BY c.id",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/cart")
def add_to_cart(body: CartBody, user: dict = Depends(get_current_user)):
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    conn = get_db()
    if conn.execute("SELECT id FROM products WHERE id = ?", (body.product_id,)).fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    existing = conn.execute(
        "SELECT id FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user["id"], body.product_id),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE cart_items SET quantity = quantity + ? WHERE id = ?",
            (body.quantity, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
            (user["id"], body.product_id, body.quantity),
        )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/cart/{item_id}")
def remove_from_cart(item_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    conn.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user["id"]))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------------------------------------------------------- checkout
@app.post("/api/checkout")
def checkout(body: CheckoutBody, user: dict = Depends(get_current_user)):
    """MOCK payment: nothing is charged. Only the last 4 digits are stored."""
    digits = "".join(ch for ch in body.card_number if ch.isdigit())
    if len(digits) < 4:
        raise HTTPException(status_code=400, detail="Enter a (dummy) card number")

    conn = get_db()
    items = conn.execute(
        "SELECT c.product_id, c.quantity, p.name, p.price "
        "FROM cart_items c JOIN products p ON p.id = c.product_id WHERE c.user_id = ?",
        (user["id"],),
    ).fetchall()
    if not items:
        conn.close()
        raise HTTPException(status_code=400, detail="Cart is empty")

    total = round(sum(i["price"] * i["quantity"] for i in items), 2)
    cur = conn.execute(
        "INSERT INTO orders (user_id, total, status, card_last4, created_at) "
        "VALUES (?, ?, 'paid', ?, ?)",
        (user["id"], total, digits[-4:], now()),
    )
    order_id = cur.lastrowid
    for i in items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) "
            "VALUES (?, ?, ?, ?, ?)",
            (order_id, i["product_id"], i["name"], i["quantity"], i["price"]),
        )
        conn.execute(
            "UPDATE products SET stock = MAX(stock - ?, 0) WHERE id = ?",
            (i["quantity"], i["product_id"]),
        )
    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user["id"],))
    conn.commit()
    conn.close()
    return {"order_id": order_id, "total": total, "status": "paid"}


# ------------------------------------------------------------------ orders
@app.get("/api/orders")
def order_history(user: dict = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, total, status, created_at FROM orders WHERE user_id = ? ORDER BY id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/orders/{order_id}")
def order_detail(order_id: int, user: dict = Depends(get_current_user)):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    # VULN-02 FIXED: enforce ownership - only the order's own user, or an admin,
    # may read it (CWE-639). A mismatch is reported as 404 (not 403) so a user
    # cannot distinguish "not yours" from "doesn't exist".
    if order is None or (order["user_id"] != user["id"] and user["role"] != "admin"):
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    items = conn.execute(
        "SELECT product_id, product_name, quantity, price FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    conn.close()
    result = dict(order)
    result["items"] = [dict(i) for i in items]
    return result


# ------------------------------------------------------------------- admin
# VULN-08 FIXED: every admin route depends on require_admin, not just
# get_current_user, so only users with role=='admin' can call them (CWE-862).
@app.post("/api/admin/products")
def admin_add_product(body: ProductBody, admin: dict = Depends(require_admin)):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
        (body.name, body.description, body.price, body.stock),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id}


@app.put("/api/admin/products/{product_id}")
def admin_edit_product(product_id: int, body: ProductBody, admin: dict = Depends(require_admin)):
    conn = get_db()
    conn.execute(
        "UPDATE products SET name = ?, description = ?, price = ?, stock = ? WHERE id = ?",
        (body.name, body.description, body.price, body.stock, product_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: int, admin: dict = Depends(require_admin)):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


init_db()

if __name__ == "__main__":
    # Bound to loopback only: this app is intentionally vulnerable.
    uvicorn.run(app, host="127.0.0.1", port=8000)
